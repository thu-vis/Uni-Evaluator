import numpy as np
import copy
import os
from queue import PriorityQueue
import base64
import math

from data.grid.sampling import HierarchySampling
from data.grid.gridLayout import GridLayout

class GridInteraction(object):
    def __init__(self, mainData, contextData = None) -> None:
        self.mainData = mainData
        self.contextData = contextData
        self.mainSampler = mainData.sampler
        self.contextSampler = None
        self.grider = GridLayout()
    
        # hierarchy sampling
        if contextData is not None:
            self.contextSampler = HierarchySampling()
            if os.path.exists(mainData.context_hierarchy_sample_path):
                self.contextSampler.load(mainData.context_hierarchy_sample_path)
            else:
                # fit all features (predict & gt) to sampler
                val_labels = np.concatenate((mainData.raw_predicts[:, 0], mainData.raw_labels[:, 0])).astype(np.int32)
                val_features = mainData.all_features
                # TODO: use gt data or all training data?
                train_labels = contextData.raw_labels[:, 0].astype(np.int32)
                train_features = contextData.gt_features
                self.contextSampler.fit(val_features, val_labels, train_features, train_labels, 225)
                self.contextSampler.dump(mainData.context_hierarchy_sample_path)
    
    def gridZoomIn(self, nodes, constraints, depth, aspectRatio, zoomin, iou_thres, conf_thres):
        mainData = self.mainData
        contextData = self.contextData
        
        predict_label_pairs, _, predict_type = mainData.pairs_map_under_iou_thresholds[iou_thres][conf_thres]

        def getFeatureIdsFromNodes(nds):
            # TODO: sometimes can use gt features?
            feature_ids = predict_label_pairs[nds, 0]
            feature_ids[feature_ids==-1] = predict_label_pairs[np.array(nds, dtype=np.int32)[feature_ids==-1], 1] + len(mainData.raw_predicts)
            return feature_ids

        nodes = np.array(nodes)
        if len(nodes) > 0 and np.all(nodes < 0):
            return {}
        if constraints is not None:
            constraints = np.array(constraints)[nodes >= 0]
        nodes = nodes[nodes >= 0].tolist()

        minWidth, maxWidth = 3, 12
        if len(nodes) == 0:
            layoutWidth = maxWidth
        else:
            layoutWidth = minWidth
            for width in range(minWidth, maxWidth + 1):
                height = math.ceil(width * aspectRatio)
                if width * height > len(nodes): # or width == maxWidth:
                    # layoutWidth = width
                    break
                layoutWidth = width
        aspectRatio = math.ceil(layoutWidth * aspectRatio) / layoutWidth
        targetGrids = int(layoutWidth * layoutWidth * aspectRatio)

        zoomInConstraints = None
        zoomInConstraintX = None
        if constraints is not None and len(constraints) > 0:
            feature_ids = getFeatureIdsFromNodes(nodes)
            zoomInConstraints = constraints
            zoomInConstraintX = mainData.all_features[feature_ids]

        val_show = 50 if contextData is not None else targetGrids
        if len(nodes) > val_show:
            # sample val_show from val samples with error
            from data.grid.sampling import DensityBiasedSampling
            sampler = DensityBiasedSampling(alpha=1, beta=20)
            if len(nodes) > 10000:
                np.random.seed(42)
                nodes = np.random.choice(nodes, 10000, replace=False)
            feature_ids = getFeatureIdsFromNodes(nodes)
            sample_ids = sampler.sample(mainData.all_features[feature_ids], val_show)
            nodes = np.array(nodes, dtype=np.int32)[sample_ids].tolist()
            if constraints is not None:
                zoomInConstraints, zoomInConstraintX = zoomInConstraints[sample_ids], zoomInConstraintX[sample_ids]
        elif len(nodes) > 0 and len(nodes) < val_show:
            feature_ids = getFeatureIdsFromNodes(nodes)
            zoomin_cat = -1
            if feature_ids[0] > len(mainData.raw_predicts):
                zoomin_cat = mainData.raw_labels[feature_ids[0]-len(mainData.raw_predicts), 0]
            else:
                zoomin_cat = mainData.raw_predicts[feature_ids[0], 0]
            neighbor_ids = self.mainSampler.zoomin(feature_ids, val_show - len(nodes), mainData.all_features, np.concatenate((mainData.raw_predicts[:, 0], mainData.raw_labels[:, 0])).astype(np.int32), zoomin_cat)
            for feat_id in neighbor_ids:
                if feat_id > len(mainData.raw_predicts):
                    target_pair_ids = np.where(predict_label_pairs[:,1]==feat_id-len(mainData.raw_predicts))[0].tolist()
                else:
                    if feat_id not in predict_label_pairs[:, 0]:
                        continue
                    else:
                        target_pair_ids = np.where(predict_label_pairs[:,0]==feat_id)[0].tolist()
                if len(target_pair_ids) == 0:
                    continue
                nodes.append(target_pair_ids[np.argmin(predict_type[target_pair_ids])])
            nodes = np.unique(np.array(nodes).astype(np.int32)).tolist()
            if len(nodes) < val_show:
                candidate_pairs = np.where(((predict_label_pairs[:,0]!=-1) & (mainData.raw_predicts[predict_label_pairs[:,0],0]==zoomin_cat)) | \
                    ((predict_label_pairs[:,1]!=-1) & (mainData.raw_labels[predict_label_pairs[:,1],0]==zoomin_cat)))[0]
                candidate_pairs = np.setdiff1d(candidate_pairs, nodes)
                nodes += np.random.choice(candidate_pairs, val_show - len(nodes), replace=False).tolist() # TODO: for categories with very small quantity, will cause error
        elif len(nodes) == 0 and contextData is None:
            np.random.seed(42)
            node_pairs = np.random.choice(np.where((predict_type<=4)|(predict_type>=9))[0], targetGrids, replace=False)
            nodes = np.unique(np.array(node_pairs).astype(np.int32)).tolist()
        feature_ids = getFeatureIdsFromNodes(nodes)
        if contextData is not None:
            # TODO: assure grid quantity when using training data as context
            zoomin_cat = -1
            if len(nodes) > 0:
                if feature_ids[0] > len(mainData.raw_predicts):
                    zoomin_cat = mainData.raw_labels[feature_ids[0]-len(mainData.raw_predicts), 0]
                else:
                    zoomin_cat = mainData.raw_predicts[feature_ids[0], 0]
            # zoomin returns id of train gt
            neighbor_train_gt = self.contextSampler.zoomin(feature_ids, targetGrids - val_show, contextData.gt_features, contextData.raw_labels[:, 0], zoomin_cat)
            train_predict_label_pairs, _, train_pair_type = contextData.pairs_map_under_iou_thresholds[iou_thres][conf_thres]
            neighbor_train_pair = []
            for train_gt in neighbor_train_gt:
                target_pair_ids = np.where(train_predict_label_pairs[:,1]==train_gt)[0].tolist()
                if len(target_pair_ids) == 0:
                    continue
                neighbor_train_pair.append(target_pair_ids[np.argmin(train_pair_type[target_pair_ids])])
            # mark train gt index as negative numbers
            zoomInNodes = np.concatenate((nodes, -np.array(neighbor_train_pair))).astype(np.int32).tolist()
            zoomInFeatures = np.concatenate((mainData.all_features[feature_ids], contextData.gt_features[train_predict_label_pairs[neighbor_train_pair, 1]]))
        else:
            zoomInNodes = nodes
            zoomInFeatures = mainData.all_features[feature_ids]
        
        zoomInLabels, zoomInPreds, zoomInConfidence, zoomInType = [], [], [], []
        for node in zoomInNodes:
            # train gt
            if node < 0:
                pr, gt = train_predict_label_pairs[-node]
                zoomInPreds.append(-1 if pr == -1 else contextData.raw_predicts[pr, 0])
                zoomInConfidence.append(0 if pr == -1 else contextData.raw_predicts[pr, 1])
                zoomInLabels.append(contextData.raw_labels[gt, 0])
                zoomInType.append(13)
                continue
            # node is index of pairs
            pr, gt = predict_label_pairs[node]
            if pr == -1:
                zoomInPreds.append(-1)
                zoomInConfidence.append(0)
            else:
                zoomInPreds.append(mainData.raw_predicts[pr, 0])
                zoomInConfidence.append(mainData.raw_predicts[pr, 1])
            if gt == -1:
                zoomInLabels.append(-1)
            else:
                zoomInLabels.append(mainData.raw_labels[gt, 0])
            zoomInType.append(predict_type[node])

        zoomInLabels, zoomInPreds, zoomInConfidence, zoomInType = np.array(zoomInLabels, dtype=np.int32), np.array(zoomInPreds, dtype=np.int32), np.array(zoomInConfidence, dtype=np.float64), np.array(zoomInType, dtype=np.int32)
        zoomInLabels[zoomInLabels==-1] = len(mainData.names) - 1
        zoomInPreds[zoomInPreds==-1] = len(mainData.names) - 1

        def getBottomLabels(zoomInNodes):
            hierarchy = copy.deepcopy(mainData.hierarchy)
            labelnames = copy.deepcopy(mainData.names)
            nodes = [{
                "index": zoomInNodes[i],
                "label": zoomInLabels[i],
                "pred": zoomInPreds[i]
            } for i in range(len(zoomInNodes))]

            root = {
                'name': '',
                'children': hierarchy,
            }
            counts = {}
            for node in nodes:
                if not counts.__contains__(labelnames[node['pred']]):
                    counts[labelnames[node['pred']]] = 0
                counts[labelnames[node['pred']]] += 1

            def dfsCount(root, counts):
                if isinstance(root, str):
                    if not counts.__contains__(root): # TODO
                        counts[root] = 0
                    return {
                        'name': root,
                        'count': counts[root],
                        'children': [],
                        'realChildren': [],
                        'emptyChildren': [],
                    }
                else:
                    count = 0
                    realChildren = []
                    emptyChildren = []
                    for i in range(len(root['children'])):
                        root['children'][i] = dfsCount(root['children'][i], counts)
                        count += root['children'][i]['count']
                        if root['children'][i]['count'] != 0:
                            realChildren.append(root['children'][i])
                        else: 
                            emptyChildren.append(root['children'][i])
                    root['realChildren'] = realChildren
                    root['emptyChildren'] = emptyChildren
                    counts[root['name']] = count
                    root['count'] = count
                    return root
            
            dfsCount(root, counts)

            pq = PriorityQueue()

            class Cmp:
                def __init__(self, name, count, realChildren):
                    self.name = name
                    self.count = count
                    self.realChildren = realChildren

                def __lt__(self, other):
                    if self.count <= other.count:
                        return False
                    else:
                        return True

                def to_list(self):
                    return [self.name, self.count, self.realChildren]
            
            pq.put(Cmp(root['name'], root['count'], root['realChildren']))
            classThreshold = 10
            countThreshold = 0.5
        
            while True:
                if pq.qsize()==0:
                    break
                top = pq.get()
                if pq.qsize() + len(top.realChildren) <= classThreshold or top.count / root['count'] >= countThreshold:
                    for child in top.realChildren:
                        pq.put(Cmp(child['name'], child['count'], child['realChildren']))
                    if pq.qsize()==0:
                        pq.put(top)
                        break
                else:
                    pq.put(top)
                    break
    
            pq_list = []
            while not pq.empty():
                pq_list.append(pq.get().name)
            return pq_list

        bottomLabels = getBottomLabels(copy.deepcopy(zoomInNodes))
        labelTransform = mainData.transformBottomLabelToTop(bottomLabels)
        constraintLabels = []
        for node in nodes:
            if predict_label_pairs[node, 1] == -1:
                constraintLabels.append(labelTransform[len(mainData.names) - 1])
            else:
                constraintLabels.append(labelTransform[int(mainData.raw_labels[predict_label_pairs[node, 1], 0])])
        labels = labelTransform[zoomInLabels]

        # original
        # labelTransform = self.transformBottomLabelToTop([node['name'] for node in self.statistic['confusion']['hierarchy']])

        # constraints should be related to the previous n nodes, or it will cause error in tSNE
        tsne, grid, grid_width, grid_height = self.grider.fit(zoomInFeatures, labels = labels, constraintX = zoomInConstraintX, 
                                               constraintY = zoomInConstraints, constraintLabels = constraintLabels, aspectRatio = aspectRatio)
        tsne = tsne.tolist()
        grid = grid.tolist()
        zoomInLabels = zoomInLabels.tolist()
        zoomInPreds = zoomInPreds.tolist()
        zoomInConfidence = zoomInConfidence.tolist()
        zoomInType = zoomInType.tolist()

        n = len(zoomInNodes)
        print(n)
        nodes = [{
            "index": zoomInNodes[i],
            "tsne": tsne[i],
            "grid": grid[i],
            "label": zoomInLabels[i],
            "pred": zoomInPreds[i],
            "confidence": zoomInConfidence[i],
            "type": zoomInType[i]
        } for i in range(n)]
        res = {
            "nodes": nodes,
            "grid": {
                "width": grid_width,
                "height": grid_height,
            },
            "depth": 0
        }
        return res
        
    def getImagesInGridLayout(self, boxIDs: list, show_mode: str, iou_thres: float, conf_thres: float, gt_color: str, pr_color: str):
        base64Imgs = []
        for boxID in boxIDs:
            if boxID < 0:
                output = self.contextData.getImage(-boxID, show_mode, 'single', iou_thres, conf_thres, False, gt_color, pr_color)
            else:
                output = self.mainData.getImage(boxID, show_mode, 'single', iou_thres, conf_thres, False, gt_color, pr_color)
            base64Imgs.append(base64.b64encode(output.getvalue()).decode())
        return base64Imgs

    def getImageThumbnail(self, boxID: int, showall: str, iou_thres: float, conf_thres: float, gt_color: str, pr_color: str, hideBox = False):
        if boxID < 0:
            return self.contextData.getImage(-boxID, 'all', showall, iou_thres, conf_thres, hideBox, gt_color, pr_color)
        else:
            return self.mainData.getImage(boxID, 'all', showall, iou_thres, conf_thres, hideBox, gt_color, pr_color)

    def getImageBoxDetail(self, boxID: int, showall: str, iou_thres: float, conf_thres: float):
        if boxID < 0:
            return self.contextData.getImagebox(-boxID, showall, iou_thres, conf_thres)
        else:
            return self.mainData.getImagebox(boxID, showall, iou_thres, conf_thres)
