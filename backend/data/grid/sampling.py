import numpy as np
import pickle
import random
import math
import faiss
import logging
from sklearn.neighbors import NearestNeighbors
from sklearn.decomposition import PCA
import mkl

mkl.get_max_threads()

logging.basicConfig(level=logging.INFO)

# for efficient add, remove, and random select
# modified from https://stackoverflow.com/questions/15993447/python-data-structure-for-efficient-add-remove-and-random-choice
class ListDict(object):
    def __init__(self, items = []):
        self.items = items
        self.item_to_position = {}
        for i in range(len(items)):
            self.item_to_position[items[i]] = i
            
    def __len__(self):
        return len(self.items)

    def add_item(self, item):
        if item in self.item_to_position:
            return
        self.items.append(item)
        self.item_to_position[item] = len(self.items)-1

    def remove_item(self, item):
        position = self.item_to_position.pop(item)
        last_item = self.items.pop()
        if position != len(self.items):
            self.items[position] = last_item
            self.item_to_position[last_item] = position

    def choose_random_item(self):
        return random.choice(self.items)

class DensityBiasedSampling():
    def __init__(self, alpha=1.0, beta=1.0) -> None:
        self.alpha = alpha
        self.beta = beta
    
    def sample(self, data, sample_num, prob_ext = None):
        k = 50
        X = np.array(data.tolist(), dtype=np.float64)
        n, d = X.shape
        m = sample_num
        if k + 1 > n:
            k = int((n - 1) / 2)
        neighbor, dist = Knn(X, n, d, k + 1, 1, 1, n)
        radius_of_k_neighbor = dist[:, -1]
        for i in range(len(radius_of_k_neighbor)):
            radius_of_k_neighbor[i] = math.sqrt(radius_of_k_neighbor[i])
        maxD = np.max(radius_of_k_neighbor)
        minD = np.min(radius_of_k_neighbor)
        for i in range(len(radius_of_k_neighbor)):
            radius_of_k_neighbor[i] = ((radius_of_k_neighbor[i] - minD) * 1.0 / (maxD - minD)) * 0.5 + 0.5
        if prob_ext is None:
            prob_ext = np.zeros(len(data))
        prob = self.alpha * radius_of_k_neighbor + self.beta * prob_ext
        prob = prob / prob.sum()
        selected_indexes = np.random.choice(n, m, replace=False, p=prob)
        return selected_indexes
class OutlierBiasedBlueNoiseSamplingFAISS():
    def __init__(self, sampling_rate, outlier_score=None, fail_rate=0.1):
        self.sampling_rate = sampling_rate
        self.outlier_score = outlier_score
        self.fail_rate = fail_rate

    def fit(self, data, category):
        data = np.array(data.tolist(), dtype=np.float32)
        n, d = data.shape
        
        allIndexer = faiss.IndexFlatL2(d)
        allIndexer.add(data)
        if self.outlier_score is None:
            self.outlier_score = get_default_outlier_scores(data, category, dataIndexer=allIndexer)
        prob = self.outlier_score / (2 * np.max(self.outlier_score)) + 0.5
        if type(self.sampling_rate)==float:
            m = round(n * self.sampling_rate)
        else:
            m = self.sampling_rate
            self.sampling_rate = m/n
        k = int(1 / self.sampling_rate)
        dist, _ = allIndexer.search(data, k+1)
        radius = np.average(np.sqrt(dist[:, -1]))

        selected_indexes = []

        count = 0
        candidates = ListDict(items=list(range(n)))
        indexer = faiss.IndexFlatL2(d)
        while count < m:
            failure_tolerance = min(1000, (n - m) * self.fail_rate)
            fail = 0
            for i in range(len(candidates)):
                idx = candidates.choose_random_item()
                if fail > failure_tolerance or count >= m:
                    break
                if random.random() < prob[idx]:
                    fail += 1
                    continue
                success = True
                topK = 1
                nearestDis, nearestIdx = indexer.search(data[idx:idx+1, :], 1)
                if nearestIdx[0][0]!=-1 and nearestDis[0][0]<radius:
                    success = False
                if success:
                    count += 1
                    selected_indexes.append(idx)
                    indexer.add(data[idx:idx+1,:])
                    candidates.remove_item(idx)
                else:
                    fail += 1
            radius /= 2

        selected_indexes = np.array(selected_indexes)
        _, nearestIdx = indexer.search(data, 1)
        nearestIdx = np.array(selected_indexes)[nearestIdx.reshape((n))]
        
        return selected_indexes, nearestIdx

def Knn(X, N, D, n_neighbors, forest_size, subdivide_variance_size, leaf_number):
    neighbors = NearestNeighbors(n_neighbors=n_neighbors, leaf_size=leaf_number)
    neighbors.fit(X)
    distances, indices = neighbors.kneighbors(X)
    return indices, distances

def get_default_outlier_scores(data, category, k=50, dataIndexer = None):
    X = np.array(data.tolist(), dtype=np.float64)
    n, d = X.shape
    if k + 1 > n:
        k = int((n - 1) / 2)
    if dataIndexer is not None:
        distances, neighbor = dataIndexer.search(data, k+1)
    else:
        neighbor, _ = Knn(X, n, d, k + 1, 1, 1, n)
    neighbor_labels = category[neighbor]
    outlier_score = [sum(neighbor_labels[i] != category[i]) for i in range(data.shape[0])]
    outlier_score = np.array(outlier_score) / k
    return outlier_score

class HierarchySampling(object):
    
    def __init__(self):
        super().__init__()
        self.top_nodes = []
        self.neighbors = None
        
    def fit(self, val_data, val_category, train_data, train_category, top_nodes_count):
        train_data = np.array(train_data.tolist(), dtype=np.float32)
        val_data = np.array(val_data.tolist(), dtype=np.float32)
        # get faiss index
        n, d = train_data.shape
        nlist = 50  # how many cells
        quantizer = faiss.IndexFlatL2(d)
        indexer = faiss.IndexIVFFlat(quantizer, d, nlist)
        print("fitting train_data", len(train_data))
        indexer.train(train_data)
        indexer.add(train_data)
        dis, self.neighbors = indexer.search(val_data, 50)
        print("fit done")
        
        # get tops
        self.top_nodes = np.random.choice(n, size=top_nodes_count, replace=False)
        
    def zoomin(self, indexes, maxValue, data, neighbor_cat, zoomin_cat):
        if len(indexes)==0:
            return self.top_nodes.tolist()
        else:
            neighbors = np.unique(np.concatenate(self.neighbors[indexes, :50]))
            # select neighbors with same category
            neighbors = neighbors[neighbor_cat[neighbors]==zoomin_cat]
            if len(neighbors)<=maxValue:
                return neighbors.tolist()
            neighbors_data = data[neighbors]
            sampler = DensityBiasedSampling(alpha=1, beta=20)
            top_prob = np.zeros(len(neighbors_data))
            isTop = {}
            for index in indexes:
                isTop[index]=True
            for i in range(len(neighbors)):
                if neighbors[i] in isTop:
                    top_prob[i] = 1
            return neighbors[sampler.sample(neighbors_data, maxValue, top_prob)].tolist()
        
    def dump(self, hierarchy_path):
        with open(hierarchy_path, "wb") as f:
            pickle.dump({
                "neighbors": self.neighbors,
                "top_nodes": self.top_nodes
                }, f)
            
    def load(self, hierarchy_path):
        with open(hierarchy_path, "rb") as file:
            hierarchyInfo = pickle.load(file)
            self.neighbors = hierarchyInfo["neighbors"]
            self.top_nodes = hierarchyInfo["top_nodes"]
        