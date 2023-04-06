import numpy as np
# from tsnecuda import TSNE
# from sklearn.manifold import TSNE
from data.grid.IncrementalTSNE import IncrementalTSNE
import fastlapjv
from matplotlib import pyplot as plt
from scipy.spatial.distance import cdist
from fastlapjv import fastlapjv
import math
from time import time

class GridLayout(object):
    def __init__(self):
        super().__init__()
        self.tsner = IncrementalTSNE(n_components=2, init='pca', method='barnes_hut', perplexity=30, angle=0.3, n_jobs=8, n_iter=1000, random_state = 100)

    def fit(self, X: np.ndarray, labels: np.ndarray = None, constraintX: np.ndarray = None, constraintY: np.ndarray = None, constraintLabels: np.ndarray = None, init = None, aspectRatio = 1):
        """main fit function

        Args:
            X (np.ndarray): n * d, n is the number of samples, d is the dimension of a sample
            labels (np.ndarray): label of each sample in X
        """        
        X_embedded = self.tsne(X, constraintX = constraintX, constraintY = constraintY, labels = labels, constraintLabels = constraintLabels, init = init)
        grid_ass, grid_width, grid_height = self.grid(X_embedded, aspectRatio)
        return X_embedded, grid_ass, grid_width, grid_height
        
    def tsne(self, X: np.ndarray, labels: np.ndarray = None, perplexity: int = 15, learning_rate: int = 3, constraintX: np.ndarray = None, constraintY: np.ndarray = None, constraintLabels: np.ndarray = None, init = None) -> np.ndarray:
        # remove empty labels
        labelcnt = 0
        removeEmptyTransform = np.zeros((np.max(labels)+1), dtype=int)-1
        for label in labels:
            if removeEmptyTransform[label]==-1:
                removeEmptyTransform[label]=labelcnt
                labelcnt += 1
        labels = removeEmptyTransform[labels]
        constraintLabels = removeEmptyTransform[constraintLabels]
        self.tsner = IncrementalTSNE(n_components=2, init='pca' if init is None else init, method='barnes_hut', perplexity=30, angle=0.3, n_jobs=8, n_iter=1000, random_state = 100)
        if constraintX is None:
            X_embedded = self.tsner.fit_transform(X, constraint_X = constraintX, constraint_Y = constraintY, prev_n = 0 if constraintX is None else len(constraintX), 
            alpha = 0.5, labels=labels, label_alpha=0.9)
        else:
            self.tsner = IncrementalTSNE(n_components=2, init='pca' if init is None else init, method='barnes_hut', perplexity=50, angle=0.3, n_jobs=8, n_iter=1000, random_state = 100)
            X_embedded = self.tsner.fit_transform(X, constraint_X = constraintX, constraint_Y = constraintY, constraint_labels = constraintLabels, prev_n = 0 if constraintX is None else len(constraintX), 
            alpha = 0.1, labels = labels, label_alpha=0.1)
        return X_embedded
    
    def grid(self, X_embedded: np.ndarray, aspectRatio: int = 1):
        if len(X_embedded)>1:
            X_embedded -= X_embedded.min()
        if not np.any(np.isnan(X_embedded / X_embedded.max())):
            X_embedded /= X_embedded.max()
        num = X_embedded.shape[0]
        k = np.sqrt(num/aspectRatio)
        width = math.ceil(k)
        height = math.ceil(k*aspectRatio)
        N = width * height
        grids = np.dstack(np.meshgrid(np.linspace(0, 1 - 1.0 / width, width),
                np.linspace(0, 1 - 1.0 / height, height))) \
                .reshape(-1, 2)

        original_cost_matrix = cdist(grids, X_embedded, "euclidean")
        # knn process
        dummy_points = np.ones((N - original_cost_matrix.shape[1], 2)) * 0.5
        # dummy at [0.5, 0.5]
        dummy_vertices = (1 - cdist(grids, dummy_points, "euclidean")) * 1000
        cost_matrix = np.concatenate((original_cost_matrix, dummy_vertices), axis=1)
        row_asses, col_asses, info = fastlapjv(cost_matrix, k_value=50 if len(cost_matrix)>50 else len(cost_matrix))
        col_asses = col_asses[:num]
        return col_asses, width, height
        
if __name__ == "__main__":
    X = np.random.rand(500, 128)
    labels = np.random.randint(10, size=500)
    grid = GridLayout()
    grid.fit(X, labels)