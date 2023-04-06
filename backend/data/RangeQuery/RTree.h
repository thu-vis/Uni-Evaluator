
#include <stdio.h>
#include <math.h>
#include <assert.h>
#include <stdlib.h>

#include <algorithm>
#include <functional>

#ifndef Min
#define Min std::min
#endif //Min
#ifndef Max
#define Max std::max
#endif //Max

template <class DATATYPE, class ELEMTYPE, int NUMDIMS,
          class ELEMTYPEREAL = ELEMTYPE, int TMAXNODES = 8, int TMINNODES = TMAXNODES / 2>
class RTree
{
protected:
  struct Node; // Fwd decl.  Used by other internal structs and iterator

public:
  // These constant must be declared after Branch and before Node struct
  // Stuck up here for MSVC 6 compiler.  NSVC .NET 2003 is much happier.
  enum
  {
    MAXNODES = TMAXNODES, ///< Max elements in node
    MINNODES = TMINNODES, ///< Min elements in node
  };

public:
  RTree();
  RTree(const RTree &other);
  virtual ~RTree();

  int Search(const ELEMTYPE a_min[NUMDIMS], const ELEMTYPE a_max[NUMDIMS], std::function<bool(const DATATYPE &)> callback) const;

  /// Remove all entries from tree
  void RemoveAll();

  /// Count the data elements in this container.  This is slow as no internal counter is maintained.
  int Count();

  /// Load tree contents from file
  bool Load(const char *a_fileName);
  /// Load tree contents from stream
  bool Load(RTFileStream &a_stream);

  int Searchnode(int xmin, int xmax, int ymin, int ymax)
  {
    return 0;
  };

  int InsertNode(int xmin, int xmax, int ymin, int ymax)
  {
    return 0;
  }
  /// Save tree contents to file
  bool Save(const char *a_fileName);
  /// Save tree contents to stream
  bool Save(RTFileStream &a_stream);

  /// Iterator is not remove safe.
  class Iterator
  {
  private:
    enum
    {
      MAX_STACK = 32
    }; //  Max stack size. Allows almost n^32 where n is number of branches in node

    struct StackElement
    {
      Node *m_node;
      int m_branchIndex;
    };

  public:
    Iterator() { Init(); }

    ~Iterator() {}

    /// Is iterator invalid
    bool IsNull() { return (m_tos <= 0); }

    /// Is iterator pointing to valid data
    bool IsNotNull() { return (m_tos > 0); }

    /// Access the current data element. Caller must be sure iterator is not NULL first.
    DATATYPE &operator*()
    {
      assert(IsNotNull());
      StackElement &curTos = m_stack[m_tos - 1];
      return curTos.m_node->m_branch[curTos.m_branchIndex].m_data;
    }

    /// Access the current data element. Caller must be sure iterator is not NULL first.
    const DATATYPE &operator*() const
    {
      assert(IsNotNull());
      StackElement &curTos = m_stack[m_tos - 1];
      return curTos.m_node->m_branch[curTos.m_branchIndex].m_data;
    }

    /// Find the next data element
    bool operator++() { return FindNextData(); }

    /// Get the bounds for this node
    void GetBounds(ELEMTYPE a_min[NUMDIMS], ELEMTYPE a_max[NUMDIMS])
    {
      assert(IsNotNull());
      StackElement &curTos = m_stack[m_tos - 1];
      Branch &curBranch = curTos.m_node->m_branch[curTos.m_branchIndex];

      for (int index = 0; index < NUMDIMS; ++index)
      {
        a_min[index] = curBranch.m_rect.m_min[index];
        a_max[index] = curBranch.m_rect.m_max[index];
      }
    }

  private:
    /// Reset iterator
    void Init() { m_tos = 0; }

    /// Find the next data element in the tree (For internal use only)
    bool FindNextData()
    {
      for (;;)
      {
        if (m_tos <= 0)
        {
          return false;
        }
        StackElement curTos = Pop(); // Copy stack top cause it may change as we use it

        if (curTos.m_node->IsLeaf())
        {
          // Keep walking through data while we can
          if (curTos.m_branchIndex + 1 < curTos.m_node->m_count)
          {
            // There is more data, just point to the next one
            Push(curTos.m_node, curTos.m_branchIndex + 1);
            return true;
          }
          // No more data, so it will fall back to previous level
        }
        else
        {
          if (curTos.m_branchIndex + 1 < curTos.m_node->m_count)
          {
            // Push sibling on for future tree walk
            // This is the 'fall back' node when we finish with the current level
            Push(curTos.m_node, curTos.m_branchIndex + 1);
          }
          // Since cur node is not a leaf, push first of next level to get deeper into the tree
          Node *nextLevelnode = curTos.m_node->m_branch[curTos.m_branchIndex].m_child;
          Push(nextLevelnode, 0);

          // If we pushed on a new leaf, exit as the data is ready at TOS
          if (nextLevelnode->IsLeaf())
          {
            return true;
          }
        }
      }
    }

    /// Push node and branch onto iteration stack (For internal use only)
    void Push(Node *a_node, int a_branchIndex)
    {
      m_stack[m_tos].m_node = a_node;
      m_stack[m_tos].m_branchIndex = a_branchIndex;
      ++m_tos;
      assert(m_tos <= MAX_STACK);
    }

    /// Pop element off iteration stack (For internal use only)
    StackElement &Pop()
    {
      assert(m_tos > 0);
      --m_tos;
      return m_stack[m_tos];
    }

    StackElement m_stack[MAX_STACK]; ///< Stack as we are doing iteration instead of recursion
    int m_tos;                       ///< Top Of Stack index

    friend class RTree; // Allow hiding of non-public functions while allowing manipulation by logical owner
  };

  /// Get 'first' for iteration

  /// Get Next for iteration
  void GetNext(Iterator &a_it) { ++a_it; }

  /// Is iterator NULL, or at end?
  bool IsNull(Iterator &a_it) { return a_it.IsNull(); }

  /// Get object at iterator position
  DATATYPE &GetAt(Iterator &a_it) { return *a_it; }

protected:
  /// Minimal bounding rectangle (n-dimensional)
  struct Rect
  {
    ELEMTYPE m_min[NUMDIMS]; ///< Min dimensions of bounding box
    ELEMTYPE m_max[NUMDIMS]; ///< Max dimensions of bounding box
  };

  /// May be data or may be another subtree
  /// The parents level determines this.
  /// If the parents level is 0, then this is data
  struct Branch
  {
    Rect m_rect;     ///< Bounds
    Node *m_child;   ///< Child node
    DATATYPE m_data; ///< Data Id
  };

  /// Node for each branch level
  struct Node
  {
    bool IsInternalNode() { return (m_level > 0); } // Not a leaf, but a internal node
    bool IsLeaf() { return (m_level == 0); }        // A leaf, contains data

    int m_count;               ///< Count
    int m_level;               ///< Leaf is zero, others positive
    Branch m_branch[MAXNODES]; ///< Branch
  };

  /// A link list of nodes for reinsertion after a delete operation
  struct ListNode
  {
    ListNode *m_next; ///< Next in list
    Node *m_node;     ///< Node
  };

  /// Variables for finding a split partition
  struct PartitionVars
  {
    enum
    {
      NOT_TAKEN = -1
    }; // indicates that position

    int m_partition[MAXNODES + 1];
    int m_total;
    int m_minFill;
    int m_count[2];
    Rect m_cover[2];
    ELEMTYPEREAL m_area[2];

    Branch m_branchBuf[MAXNODES + 1];
    int m_branchCount;
    Rect m_coverSplit;
    ELEMTYPEREAL m_coverSplitArea;
  };

  Node *AllocNode();
  void FreeNode(Node *a_node);
  void InitNode(Node *a_node);
  void InitRect(Rect *a_rect);
  bool InsertRectRec(const Branch &a_branch, Node *a_node, Node **a_newNode, int a_level);
  bool InsertRect(const Branch &a_branch, Node **a_root, int a_level);
  Rect NodeCover(Node *a_node);
  bool AddBranch(const Branch *a_branch, Node *a_node, Node **a_newNode);
  void DisconnectBranch(Node *a_node, int a_index);
  int PickBranch(const Rect *a_rect, Node *a_node);
  Rect CombineRect(const Rect *a_rectA, const Rect *a_rectB);
  void SplitNode(Node *a_node, const Branch *a_branch, Node **a_newNode);
  ELEMTYPEREAL RectSphericalVolume(Rect *a_rect);
  ELEMTYPEREAL RectVolume(Rect *a_rect);
  ELEMTYPEREAL CalcRectVolume(Rect *a_rect);
  void GetBranches(Node *a_node, const Branch *a_branch, PartitionVars *a_parVars);
  void ChoosePartition(PartitionVars *a_parVars, int a_minFill);
  void LoadNodes(Node *a_nodeA, Node *a_nodeB, PartitionVars *a_parVars);
  void InitParVars(PartitionVars *a_parVars, int a_maxRects, int a_minFill);
  void PickSeeds(PartitionVars *a_parVars);
  void Classify(int a_index, int a_group, PartitionVars *a_parVars);
  bool RemoveRect(Rect *a_rect, const DATATYPE &a_id, Node **a_root);
  bool RemoveRectRec(Rect *a_rect, const DATATYPE &a_id, Node *a_node, ListNode **a_listNode);
  ListNode *AllocListNode();
  void FreeListNode(ListNode *a_listNode);
  bool Overlap(Rect *a_rectA, Rect *a_rectB) const;
  void ReInsert(Node *a_node, ListNode **a_listNode);
  bool Search(Node *a_node, Rect *a_rect, int &a_foundCount, std::function<bool(const DATATYPE &)> callback) const;
  void RemoveAllRec(Node *a_node);
  void Reset();
  void CountRec(Node *a_node, int &a_count);

  bool SaveRec(Node *a_node, RTFileStream &a_stream);
  bool LoadRec(Node *a_node, RTFileStream &a_stream);
  void CopyRec(Node *current, Node *other);

  Node *m_root;                    ///< Root of tree
  ELEMTYPEREAL m_unitSphereVolume; ///< Unit sphere constant for required number of dimensions
};

// Because there is not stream support, this is a quick and dirty file I/O helper.
// Users will likely replace its usage with a Stream implementation from their favorite API.
class RTFileStream
{
  FILE *m_file;

public:
  RTFileStream()
  {
    m_file = NULL;
  }

  ~RTFileStream()
  {
    Close();
  }

  bool OpenRead(const char *a_fileName)
  {
    m_file = fopen(a_fileName, "rb");
    if (!m_file)
    {
      return false;
    }
    return true;
  }

  bool OpenWrite(const char *a_fileName)
  {
    m_file = fopen(a_fileName, "wb");
    if (!m_file)
    {
      return false;
    }
    return true;
  }

  void Close()
  {
    if (m_file)
    {
      fclose(m_file);
      m_file = NULL;
    }
  }

  template <typename TYPE>
  size_t Write(const TYPE &a_value)
  {
    assert(m_file);
    return fwrite((void *)&a_value, sizeof(a_value), 1, m_file);
  }

  template <typename TYPE>
  size_t WriteArray(const TYPE *a_array, int a_count)
  {
    assert(m_file);
    return fwrite((void *)a_array, sizeof(TYPE) * a_count, 1, m_file);
  }

  template <typename TYPE>
  size_t Read(TYPE &a_value)
  {
    assert(m_file);
    return fread((void *)&a_value, sizeof(a_value), 1, m_file);
  }

  template <typename TYPE>
  size_t ReadArray(TYPE *a_array, int a_count)
  {
    assert(m_file);
    return fread((void *)a_array, sizeof(TYPE) * a_count, 1, m_file);
  }
};

RTREE_QUAL::RTree()
{
  assert(MAXNODES > MINNODES);
  assert(MINNODES > 0);

  // Precomputed volumes of the unit spheres for the first few dimensions
  const float UNIT_SPHERE_VOLUMES[] = {
      0.000000f, 2.000000f, 3.141593f, // Dimension  0,1,2
      4.188790f, 4.934802f, 5.263789f, // Dimension  3,4,5
      5.167713f, 4.724766f, 4.058712f, // Dimension  6,7,8
      3.298509f, 2.550164f, 1.884104f, // Dimension  9,10,11
      1.335263f, 0.910629f, 0.599265f, // Dimension  12,13,14
      0.381443f, 0.235331f, 0.140981f, // Dimension  15,16,17
      0.082146f, 0.046622f, 0.025807f, // Dimension  18,19,20
  };

  m_root = AllocNode();
  m_root->m_level = 0;
  m_unitSphereVolume = (ELEMTYPEREAL)UNIT_SPHERE_VOLUMES[NUMDIMS];
}

RTREE_TEMPLATE
RTREE_QUAL::RTree(const RTree &other) : RTree()
{
  CopyRec(m_root, other.m_root);
}

RTREE_TEMPLATE
RTREE_QUAL::~RTree()
{
  Reset(); // Free, or reset node memory
}

RTREE_TEMPLATE
void RTREE_QUAL::Insert(const ELEMTYPE a_min[NUMDIMS], const ELEMTYPE a_max[NUMDIMS], const DATATYPE &a_dataId)
{
#ifdef _DEBUG
  for (int index = 0; index < NUMDIMS; ++index)
  {
    assert(a_min[index] <= a_max[index]);
  }
#endif //_DEBUG

  Branch branch;
  branch.m_data = a_dataId;
  branch.m_child = NULL;

  for (int axis = 0; axis < NUMDIMS; ++axis)
  {
    branch.m_rect.m_min[axis] = a_min[axis];
    branch.m_rect.m_max[axis] = a_max[axis];
  }

  InsertRect(branch, &m_root, 0);
}

RTREE_TEMPLATE
void RTREE_QUAL::Remove(const ELEMTYPE a_min[NUMDIMS], const ELEMTYPE a_max[NUMDIMS], const DATATYPE &a_dataId)
{
#ifdef _DEBUG
  for (int index = 0; index < NUMDIMS; ++index)
  {
    assert(a_min[index] <= a_max[index]);
  }
#endif //_DEBUG

  Rect rect;

  for (int axis = 0; axis < NUMDIMS; ++axis)
  {
    rect.m_min[axis] = a_min[axis];
    rect.m_max[axis] = a_max[axis];
  }

  RemoveRect(&rect, a_dataId, &m_root);
}

RTREE_TEMPLATE
int RTREE_QUAL::Search(const ELEMTYPE a_min[NUMDIMS], const ELEMTYPE a_max[NUMDIMS], std::function<bool(const DATATYPE &)> callback) const
{
#ifdef _DEBUG
  for (int index = 0; index < NUMDIMS; ++index)
  {
    assert(a_min[index] <= a_max[index]);
  }
#endif //_DEBUG

  Rect rect;

  for (int axis = 0; axis < NUMDIMS; ++axis)
  {
    rect.m_min[axis] = a_min[axis];
    rect.m_max[axis] = a_max[axis];
  }

  // NOTE: May want to return search result another way, perhaps returning the number of found elements here.

  int foundCount = 0;
  Search(m_root, &rect, foundCount, callback);

  return foundCount;
}

RTREE_TEMPLATE
int RTREE_QUAL::Count()
{
  int count = 0;
  CountRec(m_root, count);

  return count;
}

RTREE_TEMPLATE
void RTREE_QUAL::CountRec(Node *a_node, int &a_count)
{
  if (a_node->IsInternalNode()) // not a leaf node
  {
    for (int index = 0; index < a_node->m_count; ++index)
    {
      CountRec(a_node->m_branch[index].m_child, a_count);
    }
  }
  else // A leaf node
  {
    a_count += a_node->m_count;
  }
}

RTREE_TEMPLATE
bool RTREE_QUAL::Load(const char *a_fileName)
{
  RemoveAll(); // Clear existing tree

  RTFileStream stream;
  if (!stream.OpenRead(a_fileName))
  {
    return false;
  }

  bool result = Load(stream);

  stream.Close();

  return result;
}

RTREE_TEMPLATE
bool RTREE_QUAL::Load(RTFileStream &a_stream)
{
  // Write some kind of header
  int _dataFileId = ('R' << 0) | ('T' << 8) | ('R' << 16) | ('E' << 24);
  int _dataSize = sizeof(DATATYPE);
  int _dataNumDims = NUMDIMS;
  int _dataElemSize = sizeof(ELEMTYPE);
  int _dataElemRealSize = sizeof(ELEMTYPEREAL);
  int _dataMaxNodes = TMAXNODES;
  int _dataMinNodes = TMINNODES;

  int dataFileId = 0;
  int dataSize = 0;
  int dataNumDims = 0;
  int dataElemSize = 0;
  int dataElemRealSize = 0;
  int dataMaxNodes = 0;
  int dataMinNodes = 0;

  a_stream.Read(dataFileId);
  a_stream.Read(dataSize);
  a_stream.Read(dataNumDims);
  a_stream.Read(dataElemSize);
  a_stream.Read(dataElemRealSize);
  a_stream.Read(dataMaxNodes);
  a_stream.Read(dataMinNodes);

  bool result = false;

  // Test if header was valid and compatible
  if ((dataFileId == _dataFileId) && (dataSize == _dataSize) && (dataNumDims == _dataNumDims) && (dataElemSize == _dataElemSize) && (dataElemRealSize == _dataElemRealSize) && (dataMaxNodes == _dataMaxNodes) && (dataMinNodes == _dataMinNodes))
  {
    // Recursively load tree
    result = LoadRec(m_root, a_stream);
  }

  return result;
}

RTREE_TEMPLATE
bool RTREE_QUAL::LoadRec(Node *a_node, RTFileStream &a_stream)
{
  a_stream.Read(a_node->m_level);
  a_stream.Read(a_node->m_count);

  if (a_node->IsInternalNode()) // not a leaf node
  {
    for (int index = 0; index < a_node->m_count; ++index)
    {
      Branch *curBranch = &a_node->m_branch[index];

      a_stream.ReadArray(curBranch->m_rect.m_min, NUMDIMS);
      a_stream.ReadArray(curBranch->m_rect.m_max, NUMDIMS);

      curBranch->m_child = AllocNode();
      LoadRec(curBranch->m_child, a_stream);
    }
  }
  else // A leaf node
  {
    for (int index = 0; index < a_node->m_count; ++index)
    {
      Branch *curBranch = &a_node->m_branch[index];

      a_stream.ReadArray(curBranch->m_rect.m_min, NUMDIMS);
      a_stream.ReadArray(curBranch->m_rect.m_max, NUMDIMS);

      a_stream.Read(curBranch->m_data);
    }
  }

  return true; // Should do more error checking on I/O operations
}

RTREE_TEMPLATE
void RTREE_QUAL::CopyRec(Node *current, Node *other)
{
  current->m_level = other->m_level;
  current->m_count = other->m_count;

  if (current->IsInternalNode()) // not a leaf node
  {
    for (int index = 0; index < current->m_count; ++index)
    {
      Branch *currentBranch = &current->m_branch[index];
      Branch *otherBranch = &other->m_branch[index];

      std::copy(otherBranch->m_rect.m_min,
                otherBranch->m_rect.m_min + NUMDIMS,
                currentBranch->m_rect.m_min);

      std::copy(otherBranch->m_rect.m_max,
                otherBranch->m_rect.m_max + NUMDIMS,
                currentBranch->m_rect.m_max);

      currentBranch->m_child = AllocNode();
      CopyRec(currentBranch->m_child, otherBranch->m_child);
    }
  }
  else // A leaf node
  {
    for (int index = 0; index < current->m_count; ++index)
    {
      Branch *currentBranch = &current->m_branch[index];
      Branch *otherBranch = &other->m_branch[index];

      std::copy(otherBranch->m_rect.m_min,
                otherBranch->m_rect.m_min + NUMDIMS,
                currentBranch->m_rect.m_min);

      std::copy(otherBranch->m_rect.m_max,
                otherBranch->m_rect.m_max + NUMDIMS,
                currentBranch->m_rect.m_max);

      currentBranch->m_data = otherBranch->m_data;
    }
  }
}

RTREE_TEMPLATE
bool RTREE_QUAL::Save(const char *a_fileName)
{
  RTFileStream stream;
  if (!stream.OpenWrite(a_fileName))
  {
    return false;
  }

  bool result = Save(stream);

  stream.Close();

  return result;
}

RTREE_TEMPLATE
bool RTREE_QUAL::Save(RTFileStream &a_stream)
{
  // Write some kind of header
  int dataFileId = ('R' << 0) | ('T' << 8) | ('R' << 16) | ('E' << 24);
  int dataSize = sizeof(DATATYPE);
  int dataNumDims = NUMDIMS;
  int dataElemSize = sizeof(ELEMTYPE);
  int dataElemRealSize = sizeof(ELEMTYPEREAL);
  int dataMaxNodes = TMAXNODES;
  int dataMinNodes = TMINNODES;

  a_stream.Write(dataFileId);
  a_stream.Write(dataSize);
  a_stream.Write(dataNumDims);
  a_stream.Write(dataElemSize);
  a_stream.Write(dataElemRealSize);
  a_stream.Write(dataMaxNodes);
  a_stream.Write(dataMinNodes);

  // Recursively save tree
  bool result = SaveRec(m_root, a_stream);

  return result;
}

RTREE_TEMPLATE
bool RTREE_QUAL::SaveRec(Node *a_node, RTFileStream &a_stream)
{
  a_stream.Write(a_node->m_level);
  a_stream.Write(a_node->m_count);

  if (a_node->IsInternalNode()) // not a leaf node
  {
    for (int index = 0; index < a_node->m_count; ++index)
    {
      Branch *curBranch = &a_node->m_branch[index];

      a_stream.WriteArray(curBranch->m_rect.m_min, NUMDIMS);
      a_stream.WriteArray(curBranch->m_rect.m_max, NUMDIMS);

      SaveRec(curBranch->m_child, a_stream);
    }
  }
  else // A leaf node
  {
    for (int index = 0; index < a_node->m_count; ++index)
    {
      Branch *curBranch = &a_node->m_branch[index];

      a_stream.WriteArray(curBranch->m_rect.m_min, NUMDIMS);
      a_stream.WriteArray(curBranch->m_rect.m_max, NUMDIMS);

      a_stream.Write(curBranch->m_data);
    }
  }

  return true; // Should do more error checking on I/O operations
}

RTREE_TEMPLATE
void RTREE_QUAL::RemoveAll()
{
  // Delete all existing nodes
  Reset();

  m_root = AllocNode();
  m_root->m_level = 0;
}

RTREE_TEMPLATE
void RTREE_QUAL::Reset()
{
#ifdef RTREE_DONT_USE_MEMPOOLS
  // Delete all existing nodes
  RemoveAllRec(m_root);
#else  // RTREE_DONT_USE_MEMPOOLS
  // Just reset memory pools.  We are not using complex types
  // EXAMPLE
#endif // RTREE_DONT_USE_MEMPOOLS
}

RTREE_TEMPLATE
void RTREE_QUAL::RemoveAllRec(Node *a_node)
{
  assert(a_node);
  assert(a_node->m_level >= 0);

  if (a_node->IsInternalNode())
  {
    for (int index = 0; index < a_node->m_count; ++index)
    {
      RemoveAllRec(a_node->m_branch[index].m_child);
    }
  }
  FreeNode(a_node);
}