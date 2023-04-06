#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
namespace py = pybind11;
using namespace pybind11::literals; // to bring in the `_a` literal

#include <map>
#include <string>
#include <ctime>
#include <tuple>
#include <stdio.h>
#include <time.h>
#include <functional>
#include "RStarTree.h"

const int nIndexedDims = 5;
const int nLeafDims = 2;
const int nBin = 50;

struct LeafData {
	int index;
	std::vector<double> data;
	LeafData(){}
	LeafData(int index, const std::vector<double>& data): index(index), data(data) {}
};

typedef RStarTree<LeafData, nIndexedDims, 32, 64> RTree;
typedef RTree::BoundingBox BoundingBox;

struct MatrixVisitor {
	MatrixVisitor(size_t nCol = 1, size_t nRow = 1) :
		ContinueVisiting(true),
		nCol(nCol), nRow(nRow),
		getter([](const LeafData& vec) -> std::pair<int, int> { return std::make_pair((int)vec.data[0], (int)vec.data[1]); }),
		checker([](const LeafData&) -> bool { return true; }) {};

	std::vector<std::pair<int, int>> values;
	std::function<std::pair<int, int>(const LeafData&)> getter;
	std::function<bool(const LeafData&)> checker;
	size_t nCol, nRow;
	bool ContinueVisiting;
	
	void operator()(const RTree::Leaf * const leaf) {
		if (checker(leaf->leaf)) {
			values.push_back(getter(leaf->leaf));
		}
	}

	std::vector<std::vector<int>> matrix() {
		std::vector<std::vector<int>> ret;
		for (size_t i = 0; i < nRow; ++i) {
			std::vector<int> row;
			for (size_t j = 0; j < nCol; ++j) {
				row.push_back(0);
			}
			ret.push_back(row);
		}

		for (auto v: values) {
			ret[v.first][v.second]++;
		}

		return ret;
	}
};

struct DistributionVisitor {
	std::vector<double> values;
	bool ContinueVisiting;
	double minValue, maxValue;
	std::function<double(const LeafData&)> getter;
	std::function<bool(const LeafData&)> checker;
	
	DistributionVisitor(double minValue = 0.0, double maxValue = 1.0) :
		ContinueVisiting(true),
		minValue(minValue), maxValue(maxValue),
		getter([](const LeafData& vec) -> double { return vec.data[0]; }),
		checker([](const LeafData&) -> bool { return true; }) {};
	
	void operator()(const RTree::Leaf * const leaf) {
		if (checker(leaf->leaf)) {
			values.push_back(getter(leaf->leaf));
		}
	}

	std::pair<std::vector<std::pair<double, double>>, std::vector<int>> distribution() {
		std::vector<int> ret;
		for (int i = 0; i < nBin; ++i)
			ret.push_back(0);

		for (size_t i = 0; i < values.size(); ++i) {
			int index = (int)((values[i] - minValue) * nBin / (maxValue - minValue));
			if (index >= nBin) index = nBin - 1;
			ret[index]++;
		}

		std::vector<std::pair<double, double>> bins;
		for (int i = 0; i < nBin; ++i) {
			double start = minValue + (maxValue - minValue) / nBin * i;
			double end = minValue + (maxValue - minValue) / nBin * (i + 1);
			bins.push_back(std::make_pair(start, end));
		}

		return std::make_pair(bins, ret);
	}
};

struct IndexVisitor {
	std::vector<int> index;
	bool ContinueVisiting;
	std::function<bool(const LeafData&)> checker;
	
	IndexVisitor() :
		ContinueVisiting(true),
		checker([](const LeafData&) -> bool { return true; }) {};
	
	void operator()(const RTree::Leaf * const leaf) {
		if (checker(leaf->leaf)) {
			index.push_back(leaf->leaf.index);
		}
	}
};

std::vector<double> getIndex(const std::vector<double> &vec, const std::vector<int>& indexes) {
	std::vector<double> ret;
	for (int i: indexes) {
		ret.push_back(vec[i]);
	}
	return ret;
}

BoundingBox getBound(const std::vector<double>& vec) {
	BoundingBox bb;
	for (size_t i = 0; i < vec.size(); ++i) {
		bb.edges[i].first = bb.edges[i].second = vec[i];
	}
	return bb;
}

class RangeTree {
public:
	RangeTree(){}
	void Init(const std::vector<std::vector<double>> &data) {
		std::vector<int> indexed_pos;

		for (auto name: features) {
			if (featureType[name] == "index") {
				indexed_pos.push_back(featureIndex[name]);
			}
		}

		tree = new RTree();
		for (size_t i = 0; i < data.size(); ++i) {
			tree->Insert(
				LeafData(i, data[i]),
				getBound(getIndex(data[i], indexed_pos))
			);
		}
	}

	std::vector<std::vector<int>> QueryMatrix(const std::string& row, const std::string& col, const std::map<std::string, std::vector<double>>& query_dict) {
		BoundingBox bb;
		int boundingIndex = 0;
		std::vector<int> leafPos;
		std::vector<std::vector<double>> leafValues;
		int rowIndex = featureIndex[row], colIndex = featureIndex[col];
		int rowLeafIndex, colLeafIndex;

		for (std::string name: features) {
			if (featureType[name] == "index") {
				if (query_dict.find(name) != query_dict.end()) {
					auto vec = query_dict.find(name)->second;
					bb.edges[boundingIndex].first = vec[0];
					bb.edges[boundingIndex].second = vec[1];
					boundingIndex++;
				} else {
					bb.edges[boundingIndex].first = -1e6;
					bb.edges[boundingIndex].second = 1e6;
					boundingIndex++;
				}
			} else {
				if (query_dict.find(name) != query_dict.end()) {
					auto vec = query_dict.find(name)->second;
					leafPos.push_back(featureIndex[name]);
					if (name == row) {
						rowLeafIndex = leafValues.size();
					} else if (name == col) {
						colLeafIndex = leafValues.size();
					}
					leafValues.push_back(vec);
				}
			}
		}

		// std::cout << "rowLeafIndex" << rowLeafIndex << "colLeafIndex" << colLeafIndex << std::endl;
		auto visitor = MatrixVisitor(leafValues[rowLeafIndex].size(), leafValues[colLeafIndex].size());

		visitor.checker = [&](const LeafData& vec) -> bool {
			for (size_t i = 0; i < leafPos.size(); ++i) {
				bool flag = false;
				for (double value: leafValues[i]) {
					if (vec.data[leafPos[i]] == value) {
						flag = true;
						break;
					}
				}
				if (!flag) return false;
			}
			return true;
		};
		visitor.getter = [&](const LeafData& vec) -> std::pair<int, int> {
			int first = 0, second = 0;
			for (size_t i = 0; i < leafValues[rowLeafIndex].size(); ++i) {
				if (leafValues[rowLeafIndex][i] == vec.data[rowIndex]) {
					first = i;
					break;
				}
			}
			for (size_t i = 0; i < leafValues[colLeafIndex].size(); ++i) {
				if (leafValues[colLeafIndex][i] == vec.data[colIndex]) {
					second = i;
					break;
				}
			}
			return std::make_pair(first, second);
		};

		visitor = tree->Query(RTree::AcceptEnclosing(bb), visitor);

		return visitor.matrix();
	}

	std::vector<int> QueryIndex(const std::map<std::string, std::vector<double>>& query_dict) {

		BoundingBox bb;
		int boundingIndex = 0;
		std::vector<int> leafPos;
		std::vector<std::vector<double>> leafValues;

		for (std::string name: features) {
			if (featureType[name] == "index") {
				if (query_dict.find(name) != query_dict.end()) {
					auto vec = query_dict.find(name)->second;
					bb.edges[boundingIndex].first = vec[0];
					bb.edges[boundingIndex].second = vec[1];
					boundingIndex++;
				} else {
					bb.edges[boundingIndex].first = -1e6;
					bb.edges[boundingIndex].second = 1e6;
					boundingIndex++;
				}
			} else {
				if (query_dict.find(name) != query_dict.end()) {
					auto vec = query_dict.find(name)->second;
					leafPos.push_back(featureIndex[name]);
					leafValues.push_back(vec);
				}
			}
		}
		auto visitor = IndexVisitor();
		visitor.checker = [&](const LeafData& vec) -> bool {
			for (size_t i = 0; i < leafPos.size(); ++i) {
				bool flag = false;
				for (double value: leafValues[i]) {
					if (vec.data[leafPos[i]] == value) {
						flag = true;
						break;
					}
				}
				if (!flag) return false;
			}
			return true;
		};

		visitor = tree->Query(RTree::AcceptEnclosing(bb), visitor);
		return visitor.index;
	}

	std::pair<std::vector<std::pair<double, double>>, std::vector<int>> QueryDistribution(
		const std::string& key,
		const std::map<std::string, std::vector<double>>& query_dict,
		const std::map<std::string, double>& attr_dict) {

		BoundingBox bb;
		int boundingIndex = 0;
		std::vector<int> leafPos;
		std::vector<std::vector<double>> leafValues;
		int keyIndex = featureIndex[key];

		for (std::string name: features) {
			if (featureType[name] == "index") {
				if (query_dict.find(name) != query_dict.end()) {
					auto vec = query_dict.find(name)->second;
					bb.edges[boundingIndex].first = vec[0];
					bb.edges[boundingIndex].second = vec[1];
					boundingIndex++;
				} else {
					bb.edges[boundingIndex].first = -1e6;
					bb.edges[boundingIndex].second = 1e6;
					boundingIndex++;
				}
			} else {
				if (query_dict.find(name) != query_dict.end()) {
					auto vec = query_dict.find(name)->second;
					leafPos.push_back(featureIndex[name]);
					leafValues.push_back(vec);
				}
			}
		}
		auto visitor = DistributionVisitor();
		if (attr_dict.find("min") != attr_dict.end()) {
			visitor.minValue = attr_dict.find("min")->second;
		}
		if (attr_dict.find("max") != attr_dict.end()) {
			visitor.maxValue = attr_dict.find("max")->second;
		}

		visitor.checker = [&](const LeafData& vec) -> bool {
			for (size_t i = 0; i < leafPos.size(); ++i) {
				bool flag = false;
				for (double value: leafValues[i]) {
					if (vec.data[leafPos[i]] == value) {
						flag = true;
						break;
					}
				}
				if (!flag) return false;
			}
			return true;
		};
		visitor.getter = [&](const LeafData& vec) -> double {
			return vec.data[keyIndex];
		};

		visitor = tree->Query(RTree::AcceptEnclosing(bb), visitor);
		return visitor.distribution();
	}

	void AddFeature(const std::string& name, const std::string& type, int index) {
		features.push_back(name);
		featureIndex[name] = index;
		featureType[name] = type;
	}

	void AddFeatures(const std::vector<std::tuple<std::string, std::string, int>> &_features) {
		for (auto feature: _features) {
			std::string name = std::get<0>(feature);
			features.push_back(name);
			featureIndex[name] = std::get<2>(feature);
			featureType[name] = std::get<1>(feature);
		}
	}
private:
	std::vector<std::string> features;
	std::map<std::string, int> featureIndex;
	std::map<std::string, std::string> featureType;
	RTree *tree;
};

PYBIND11_MODULE(RangeTree, m) {
    m.doc() = "Rstar-tree"; // optional module docstring
    pybind11::class_<RangeTree>(m, "RangeTree")
        .def( pybind11::init<>())
        .def( "Init", &RangeTree::Init )
        .def( "QueryDistribution", &RangeTree::QueryDistribution )
        .def( "QueryMatrix", &RangeTree::QueryMatrix )
        .def( "QueryIndex", &RangeTree::QueryIndex )
        .def( "AddFeature", &RangeTree::AddFeature )
        .def( "AddFeatures", &RangeTree::AddFeatures );

    // m.def("RangeTree", &RangeTree);
}
