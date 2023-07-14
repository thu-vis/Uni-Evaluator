import os
import json
import bisect
import numpy as np
import pickle
import math
import io
from PIL import Image
import logging

from data.grid.sampling import HierarchySampling
from data.drawBox import Annotator

from data.RangeQuery.RangeTree import RangeTree

import pycocotools.mask as mask_util
from tqdm import tqdm

from mlxtend.frequent_patterns import apriori
import pandas as pd

class DataCtrler(object):

    def __init__(self, data_name):
        super().__init__()
        self.iou_thresholds = [(50 + 5 * i) / 100 for i in [0, 5]]
        self.conf_thresholds = [0.1]
        self.classID2Idx = {}
        self.hierarchy = {}
        self.names = []
        self.data_name = data_name

    def process(self, rawDataPath, bufferPath, segmentation=False):
        """process raw data
        - rawDataPath/
          - images/
          - labels/
          - predicts/
          - meta.json
        """        
        # init paths
        self.segmentation = segmentation
        self.root_path = rawDataPath
        self.images_path = os.path.join(self.root_path, "images")
        self.labels_path = os.path.join(self.root_path, "labels")
        self.predicts_path = os.path.join(self.root_path, "predicts")
        self.meta_path = os.path.join(self.root_path, "meta.json")
        self.features_path = os.path.join(self.root_path, "pr_features")
        self.gt_features_path = os.path.join(self.root_path, "gt_features")
        if not os.path.exists(self.features_path):
            os.makedirs(self.features_path)
        if not os.path.exists(self.gt_features_path):
            os.makedirs(self.gt_features_path)
        if not os.path.exists(bufferPath):
            os.makedirs(bufferPath)
        setting_name = os.path.basename(os.path.normpath(rawDataPath))
        self.raw_data_path = os.path.join(bufferPath, "{}_raw_data.pkl".format(setting_name))
        self.label_predict_iou_path = os.path.join(bufferPath, "{}_predict_label_iou.pkl".format(setting_name))
        self.context_hierarchy_sample_path = os.path.join(bufferPath, "{}_hierarchy_samples.pkl".format(setting_name))
        self.main_hierarchy_sample_path = os.path.join(bufferPath, "{}_val_hierarchy_samples.pkl".format(setting_name))
        self.all_features_path = os.path.join(bufferPath, "{}_features.npy".format(setting_name))
        self.aspect_ratio_path = os.path.join(bufferPath, "{}_aspect_ratio.pkl".format(setting_name))
        self.directions_path = os.path.join(bufferPath, "{}_directions.pkl".format(setting_name))
        
        
        self.logger = logging.getLogger('dataCtrler')

        # read raw data
        if not self.segmentation:
            # for detection task
            if os.path.exists(self.raw_data_path):
                with open(self.raw_data_path, 'rb') as f:
                    self.image2index, self.raw_labels, self.raw_label2imageid, self.imageid2raw_label, self.raw_predicts, self.raw_predict2imageid, self.imageid2raw_predict = pickle.load(f)
            else:
                self.image2index = {}
                id=0
                for name in os.listdir(self.images_path):
                    self.image2index[name.split('.')[0]]=id
                    id += 1
                # read raw labels
                # format: label, box(cx, cy, w, h), isCrowd(0/1), area
                self.raw_labels = np.zeros((0,7), dtype=np.float32)
                self.raw_label2imageid = np.zeros(0, dtype=np.int32)
                self.imageid2raw_label = np.zeros((id, 2), dtype=np.int32)
                for imageName in tqdm(os.listdir(self.labels_path)):
                    label_path = os.path.join(self.labels_path, imageName)
                    imageid = self.image2index[imageName.split('.')[0]]
                    with open(label_path) as f:
                        lb = [x.split() for x in f.read().strip().splitlines() if len(x)]
                        lb = np.array(lb, dtype=np.float32)
                        self.imageid2raw_label[imageid][0] = len(self.raw_labels)
                        self.imageid2raw_label[imageid][1] = len(self.raw_labels)+len(lb)
                        if len(lb)>0:
                            self.raw_labels = np.concatenate((self.raw_labels, lb), axis=0)
                            self.raw_label2imageid = np.concatenate((self.raw_label2imageid, np.ones(len(lb), dtype=np.int32)*imageid))

                # read raw predicts
                # format: predict, confidence, box(cx, cy, w, h)
                self.raw_predicts = np.zeros((0,6), dtype=np.float32)
                self.raw_predict2imageid = np.zeros(0, dtype=np.int32)
                self.imageid2raw_predict = np.zeros((id, 2), dtype=np.int32)
                for imageName in tqdm(os.listdir(self.predicts_path)):
                    predict_path = os.path.join(self.predicts_path, imageName)
                    imageid = self.image2index[imageName.split('.')[0]]
                    with open(predict_path) as f:
                        lb = [x.split() for x in f.read().strip().splitlines() if len(x)]
                        lb = np.array(lb, dtype=np.float32)
                        self.imageid2raw_predict[imageid][0] = len(self.raw_predicts)
                        self.imageid2raw_predict[imageid][1] = len(self.raw_predicts)+len(lb)
                        if len(lb)>0:
                            self.raw_predicts = np.concatenate((self.raw_predicts, lb), axis=0)
                            self.raw_predict2imageid = np.concatenate((self.raw_predict2imageid, np.ones(len(lb), dtype=np.int32)*imageid))
                with open(self.raw_data_path, 'wb') as f:
                    pickle.dump((self.image2index, self.raw_labels, self.raw_label2imageid, self.imageid2raw_label, self.raw_predicts, self.raw_predict2imageid, self.imageid2raw_predict), f)
        else:
            # for instance segmentation task
            if os.path.exists(self.raw_data_path):
                with open(self.raw_data_path, 'rb') as f:
                    self.image2index, self.raw_labels, self.raw_label2imageid, self.imageid2raw_label, \
                        self.raw_predicts, self.raw_predict2imageid, self.imageid2raw_predict, self.label_masks, self.predict_masks = pickle.load(f)
            else:
                self.image2index = {}
                id=0
                for name in os.listdir(self.images_path):
                    self.image2index[name.split('.')[0]]=id
                    id += 1
                # read raw labels
                # format: label, isCrowd(0/1), im_w, im_h, mask_rle
                self.raw_labels = np.zeros((0,4), dtype=np.float32)
                self.raw_label2imageid = np.zeros(0, dtype=np.int32)
                self.imageid2raw_label = np.zeros((id, 2), dtype=np.int32)
                self.label_masks = []
                for imageName in tqdm(os.listdir(self.labels_path)):
                    label_path = os.path.join(self.labels_path, imageName)
                    imageid = self.image2index[imageName.split('.')[0]]
                    with open(label_path) as f:
                        lb = [x.split() for x in f.read().strip().splitlines() if len(x)]
                        assert np.all([len(i) == 5 for i in lb]), lb
                        mask_rle = [i[4] for i in lb]
                        label_info = np.array([i[:4] for i in lb], dtype=np.float32)
                        self.imageid2raw_label[imageid][0] = len(self.raw_labels)
                        self.imageid2raw_label[imageid][1] = len(self.raw_labels)+len(label_info)
                        if len(lb)>0:
                            self.raw_labels = np.concatenate((self.raw_labels, label_info), axis=0)
                            self.raw_label2imageid = np.concatenate((self.raw_label2imageid, np.ones(len(label_info), dtype=np.int32)*imageid))
                            self.label_masks += mask_rle

                # read raw predicts
                # format: predict, confidence, im_w, im_h, mask_rle
                self.raw_predicts = np.zeros((0,4), dtype=np.float32)
                self.raw_predict2imageid = np.zeros(0, dtype=np.int32)
                self.imageid2raw_predict = np.zeros((id, 2), dtype=np.int32)
                self.predict_masks = []
                for imageName in tqdm(os.listdir(self.predicts_path)):
                    predict_path = os.path.join(self.predicts_path, imageName)
                    imageid = self.image2index[imageName.split('.')[0]]
                    with open(predict_path) as f:
                        lb = [x.split() for x in f.read().strip().splitlines() if len(x)]
                        assert np.all([len(i) == 5 for i in lb]), lb
                        mask_rle = [i[4] for i in lb]
                        predict_info = np.array([i[:4] for i in lb], dtype=np.float32)
                        self.imageid2raw_predict[imageid][0] = len(self.raw_predicts)
                        self.imageid2raw_predict[imageid][1] = len(self.raw_predicts)+len(predict_info)
                        if len(lb)>0:
                            self.raw_predicts = np.concatenate((self.raw_predicts, predict_info), axis=0)
                            self.raw_predict2imageid = np.concatenate((self.raw_predict2imageid, np.ones(len(predict_info), dtype=np.int32)*imageid))
                            self.predict_masks += mask_rle
                with open(self.raw_data_path, 'wb') as f:
                    pickle.dump((self.image2index, self.raw_labels, self.raw_label2imageid, self.imageid2raw_label, 
                        self.raw_predicts, self.raw_predict2imageid, self.imageid2raw_predict, self.label_masks, self.predict_masks), f)
        self.index2image = ['']*len(self.image2index)
        for image, index in self.image2index.items():
            self.index2image[index] = image
        
        # init meta data
        # suitable for two-level hierarchy
        with open(self.meta_path) as f:
            metas = json.load(f)
            categorys = metas["categories"]
            for classIdx in range(len(categorys)):
                self.classID2Idx[categorys[classIdx]["id"]] = classIdx
                self.names.append(categorys[classIdx]["name"])
                superCategory = categorys[classIdx]["supercategory"]
                if superCategory not in self.hierarchy:
                    self.hierarchy[superCategory] = {
                        "name": superCategory,
                        "children": []
                    }
                self.hierarchy[superCategory]["children"].append(categorys[classIdx]["name"])
            self.hierarchy = list(self.hierarchy.values())
            self.hierarchy.append({
                    "name": "background",
                    "children": ["background"]
                })
            self.names.append("background")
            self.classID2Idx[-1]=len(categorys)
        
        self.name2idx = {}
        for i in range(len(self.names)):
            self.name2idx[self.names[i]]=i

        # compute (prediction, label) pair
        # creates a map, with different IoU threshold (0.5~0.95 0.05) as key and (predict_label_pairs, iou) as value
        # do not store the unmatched gt here, because different confidence thershold may result in different "Missed Error"
        if os.path.exists(self.label_predict_iou_path):
            with open(self.label_predict_iou_path, 'rb') as f:
                self.pairs_map_under_iou_thresholds = pickle.load(f)
        else:
            self.pairs_map_under_iou_thresholds = self.compute_label_predict_pair()
            with open(self.label_predict_iou_path, 'wb') as f:
                pickle.dump(self.pairs_map_under_iou_thresholds, f)

        # init size and area
        if not self.segmentation:
            self.label_size = self.raw_labels[:,3]*self.raw_labels[:,4]
            self.predict_size = self.raw_predicts[:,4]*self.raw_predicts[:,5]
            self.label_area = self.raw_labels[:, 6]
        else:
            self.label_size = mask_util.area([{'size': list(im_size), 'counts': rle} for rle, im_size in zip(self.label_masks, self.raw_labels[:, 2:])]) / (self.raw_labels[:, 2] * self.raw_labels[:, 3])
            self.predict_size = mask_util.area([{'size': list(im_size), 'counts': rle} for rle, im_size in zip(self.predict_masks, self.raw_predicts[:, 2:])]) / (self.raw_predicts[:, 2] * self.raw_predicts[:, 3])
            self.label_area = mask_util.area([{'size': list(im_size), 'counts': rle} for rle, im_size in zip(self.label_masks, self.raw_labels[:, 2:])])

        # init aspect ratio
        if os.path.exists(self.aspect_ratio_path):
            with open(self.aspect_ratio_path, 'rb') as f:
                self.label_aspect_ratio, self.predict_aspect_ratio, self.label_bbox, self.predict_bbox, self.predict_true_ar, self.label_true_ar = pickle.load(f)
        else:
            if not self.segmentation:
                self.label_aspect_ratio = self.raw_labels[:,3]/self.raw_labels[:,4]
                self.predict_aspect_ratio = self.raw_predicts[:,4]/self.raw_predicts[:,5]
                self.label_bbox = None
                self.predict_bbox = None
            else:
                # x, y, w, h
                self.label_bbox = mask_util.toBbox([{'size': list(im_size), 'counts': rle} for rle, im_size in zip(self.label_masks, self.raw_labels[:, 2:])])
                self.predict_bbox = mask_util.toBbox([{'size': list(im_size), 'counts': rle} for rle, im_size in zip(self.predict_masks, self.raw_predicts[:, 2:])])
                # cx, cy, w, h
                self.label_bbox[:, :2] += self.label_bbox[:, 2:] / 2
                self.predict_bbox[:, :2] += self.predict_bbox[:, 2:] / 2
                # normalize
                self.label_bbox[:, [0, 2]] /= self.raw_labels[:, 3].reshape(-1, 1)
                self.label_bbox[:, [1, 3]] /= self.raw_labels[:, 2].reshape(-1, 1)
                self.predict_bbox[:, [0, 2]] /= self.raw_predicts[:, 3].reshape(-1, 1)
                self.predict_bbox[:, [1, 3]] /= self.raw_predicts[:, 2].reshape(-1, 1)
                assert np.all(self.label_bbox <= 1), 'check why bbox > 1?'
                self.label_aspect_ratio = self.label_bbox[:, 2] / self.label_bbox[:, 3]
                self.predict_aspect_ratio = self.predict_bbox[:, 2] / (self.predict_bbox[:, 3] + 1e-5)
            # get image aspect ratio
            image_aspect_ratio = np.ones(len(self.index2image))
            print('Loading images aspect ratio...')
            img_format = os.listdir(self.images_path)[0].split('.')[-1]
            for idx in tqdm(range(len(self.index2image))):
                img = Image.open(os.path.join(self.images_path, self.index2image[idx]+f'.{img_format}'))
                image_aspect_ratio[idx] = img.width / img.height
            self.predict_true_ar = self.predict_aspect_ratio * image_aspect_ratio[self.raw_predict2imageid]
            self.label_true_ar = self.label_aspect_ratio * image_aspect_ratio[self.raw_label2imageid]
            # convert ratio above 1 to below 1
            self.predict_true_ar[self.predict_true_ar > 1] = 1 / self.predict_true_ar[self.predict_true_ar > 1]
            self.label_true_ar[self.label_true_ar > 1] = 1 / self.label_true_ar[self.label_true_ar > 1]
            with open(self.aspect_ratio_path, 'wb') as f:
                pickle.dump((self.label_aspect_ratio, self.predict_aspect_ratio, self.label_bbox, self.predict_bbox, self.predict_true_ar, self.label_true_ar), f)

        # direction map, also use IoU threshold as key because different match results in different directions
        if os.path.exists(self.directions_path):
            with open(self.directions_path, 'rb') as f:
                self.directions_map = pickle.load(f)
        else:
            self.directions_map = {}
            for iou_thres in self.iou_thresholds:
                self.directions_map[iou_thres] = {}
                for conf_thres in self.conf_thresholds:
                    predict_label_pairs, _, predict_types = self.pairs_map_under_iou_thresholds[iou_thres][conf_thres]
                    directionIdxes = np.where(np.logical_and(predict_label_pairs[:,0]>-1, predict_label_pairs[:,1]>-1))[0]
                    if not self.segmentation:
                        directionVectors = self.raw_predicts[predict_label_pairs[directionIdxes,0]][:,[2,3]] - self.raw_labels[predict_label_pairs[directionIdxes,1]][:,[1,2]]
                    else:
                        directionVectors = self.predict_bbox[predict_label_pairs[directionIdxes,0]][:, [0, 1]] - self.label_bbox[predict_label_pairs[directionIdxes,1]][:, [0, 1]]
                    directionNorm = np.sqrt(np.power(directionVectors[:,0], 2)+ np.power(directionVectors[:,1], 2))
                    directionCos = directionVectors[:,0]/(directionNorm + 1e-5)
                    directions = np.zeros(directionCos.shape[0], dtype=np.int32)
                    directionSplits = np.array([math.cos(angle/180*math.pi) for angle in [180, 157.5, 112.5, 67.5, 22.5, 0]])
                    for i in range(2,len(directionSplits)):
                        directions[np.logical_and(directionCos>directionSplits[i-1], directionCos<=directionSplits[i])] = i-1
                    # starts from <-: 0, and clock-wise to 7, middle point as 8
                    # if directionVectors[:,1]>0, means direction downward, as the y coordinate is downward!!!
                    negaYs = np.logical_and(directionVectors[:,1]>0, directions!=0)
                    directions[negaYs] = 8-directions[negaYs]
                    self.directions_map[iou_thres][conf_thres] = -1*np.ones(predict_label_pairs.shape[0], dtype=np.int32)
                    self.directions_map[iou_thres][conf_thres][directionIdxes] = directions
                    # assign predicts with no Loc error under this iou_thres to 8
                    self.directions_map[iou_thres][conf_thres][np.isin(predict_types, [1, 2, 5])] = 8
            with open(self.directions_path, 'wb') as f:
                pickle.dump(self.directions_map, f)
        
        # read feature data
        if os.path.exists(self.all_features_path):
            self.all_features = np.load(self.all_features_path)
            self.pr_features = self.all_features[:len(self.raw_predicts)]
            self.gt_features = self.all_features[len(self.raw_predicts):]
        else:
            if len(os.listdir(self.features_path)) > 0: pr_feature_dim = np.load(os.path.join(self.features_path, os.listdir(self.features_path)[0])).shape[1]
            else: pr_feature_dim = 256
            self.pr_features = np.zeros((self.raw_predicts.shape[0], pr_feature_dim))
            for name in os.listdir(self.labels_path):
                feature_path = os.path.join(self.features_path, name.split('.')[0]+'.npy')
                imageid = self.image2index[name.split('.')[0]]
                boxCount = self.imageid2raw_predict[imageid][1]-self.imageid2raw_predict[imageid][0]
                if not os.path.exists(feature_path):
                    # WARNING
                    self.logger.warning("can't find feature: %s" % feature_path)
                    self.pr_features[self.imageid2raw_predict[imageid][0]:self.imageid2raw_predict[imageid][1]] = np.random.rand(boxCount, pr_feature_dim)
                else:
                    if np.load(feature_path).shape[0]==0: 
                        continue # image without prediction
                    self.pr_features[self.imageid2raw_predict[imageid][0]:self.imageid2raw_predict[imageid][1]] = np.load(feature_path)
            
            if len(os.listdir(self.gt_features_path)) > 0: gt_feature_dim = np.load(os.path.join(self.gt_features_path, os.listdir(self.gt_features_path)[0])).shape[1]
            else: gt_feature_dim = 256
            self.gt_features = np.zeros((self.raw_labels.shape[0], gt_feature_dim))
            for name in os.listdir(self.predicts_path):
                feature_path = os.path.join(self.gt_features_path, name.split('.')[0]+'.npy')
                imageid = self.image2index[name.split('.')[0]]
                boxCount = self.imageid2raw_label[imageid][1]-self.imageid2raw_label[imageid][0]
                if not os.path.exists(feature_path):
                    # WARNING
                    self.logger.warning("can't find feature: %s" % feature_path)
                    self.gt_features[self.imageid2raw_label[imageid][0]:self.imageid2raw_label[imageid][1]] = np.random.rand(boxCount, gt_feature_dim)
                else:
                    self.gt_features[self.imageid2raw_label[imageid][0]:self.imageid2raw_label[imageid][1]] = np.load(feature_path)
            self.all_features = np.concatenate((self.pr_features, self.gt_features))
            np.save(self.all_features_path, self.all_features)
        
        self.sampler = HierarchySampling()
        if os.path.exists(self.main_hierarchy_sample_path):
            self.sampler.load(self.main_hierarchy_sample_path)
        else:
            # fit all features (predict & gt) to sampler
            val_labels = np.concatenate((self.raw_predicts[:, 0], self.raw_labels[:, 0])).astype(np.int32)
            val_features = self.all_features
            self.sampler.fit(val_features, val_labels, val_features, val_labels, 225)
            self.sampler.dump(self.main_hierarchy_sample_path)
        
        self.constructRangeTree()

    def getMetaData(self):
        return {
            "hierarchy": self.hierarchy,
            "names": self.names,
            "dataName": self.data_name,
        }
    
    def getThresholds(self, query):
        iou_thres = 0.75 if not self.segmentation else 0.5
        if query is not None and "iou_thres" in query:
            iou_thres = query["iou_thres"]
        conf_thres = 0.1
        if query is not None and "conf_thres" in query:
            conf_thres = query["conf_thres"]
        return iou_thres, conf_thres

    def compute_label_predict_pair(self):

        def compute_per_image(detections, labels, pos_thres, conf_thres, bg_thres=0.1):
            if not self.segmentation:
                pr_bbox = detections[:, 2:6]
                pr_cat = detections[:, 0].astype(np.int32)
                pr_conf = detections[:, 1]
                gt_bbox = labels[:, 1:5]
                gt_iscrowd = labels[:,5].astype(np.int32)
                gt_cat = labels[:,0].astype(np.int32)
                iou_pair = cal_iou(pr_bbox, gt_bbox, gt_iscrowd)
            else:
                pr_cat = detections[0][:, 0].astype(np.int32)
                pr_conf = detections[0][:, 1]
                gt_iscrowd = labels[0][:,1].astype(np.int32)
                gt_cat = labels[0][:,0].astype(np.int32)
                iou_pair = mask_util.iou([{'size': list(im_size), 'counts': rle} for rle, im_size in zip(detections[1], detections[0][:, 2:].astype(np.int32))],
                                         [{'size': list(im_size), 'counts': rle} for rle, im_size in zip(labels[1], labels[0][:, 2:].astype(np.int32))], gt_iscrowd)

            ret_ious = np.zeros(0)
            ret_match = -1*np.ones((0, 2), dtype=np.int32)
            # define type here
            # -1 for ignored, 0 for abandoned;
            # 1~4 for TP, Cls(confusion), Loc, and Cls+Loc
            # 5~8 for Dup, Cls+Dup, Loc+Dup, and Cls+Loc+Dup
            # 9 for Bkgd, 10 for Miss
            # 11 for Cls+Dup (only one for each gt), 12 Cls+Loc+Dup (only one for each gt)
            # 13 for train gt
            ret_type = np.zeros(0, dtype=np.int32)
            pr_idx = np.where(pr_conf > conf_thres)[0]
            pr_idx = pr_idx[np.argsort(-pr_conf[pr_idx])]
            gt_match_cnt = np.zeros_like(gt_cat)
            gt_find_tp = np.zeros_like(gt_cat)
            for _pr_idx in pr_idx:
                possible_match_gt = np.where(iou_pair[_pr_idx, :]>bg_thres)[0]
                if len(possible_match_gt) == 0:
                    ret_ious = np.concatenate((ret_ious, [0]))
                    ret_match = np.concatenate((ret_match, np.array([[_pr_idx, -1]])))
                    ret_type = np.concatenate((ret_type, [9])) # Bkgd
                    continue
                same_cat_gt = possible_match_gt[gt_cat[possible_match_gt]==pr_cat[_pr_idx]]
                find_TP_match = False
                if len(same_cat_gt) > 0:
                    same_cat_gt = same_cat_gt[np.argsort(-iou_pair[_pr_idx, same_cat_gt])]
                    not_is_crowd_match = same_cat_gt[gt_iscrowd[same_cat_gt]==0]
                    is_crowd_match = same_cat_gt[gt_iscrowd[same_cat_gt]==1]
                    # first try match with not iscrowd gt
                    if len(not_is_crowd_match) > 0:
                        # select gt with largest IoU
                        for _gt in not_is_crowd_match:
                            if iou_pair[_pr_idx, _gt] >= pos_thres:
                                if gt_find_tp[_gt] == 0:
                                    find_TP_match = True
                                    best_match = _gt
                                    gt_find_tp[_gt] = 1
                                    break
                            else:
                                break
                        if not find_TP_match:
                            best_match = not_is_crowd_match[np.argmax(
                                iou_pair[_pr_idx, not_is_crowd_match] + np.exp(-gt_match_cnt[not_is_crowd_match])
                            )]
                    # if cannot match with not iscrowd gt, try if can match with iscrowd gt
                    if not find_TP_match and len(is_crowd_match) > 0:
                        # if cannot find TP match and can match with iscrowd object, ignore
                        if iou_pair[_pr_idx, is_crowd_match[0]] > pos_thres:
                            continue
                    if len(not_is_crowd_match) > 0:
                        gt_match_cnt[best_match] += 1
                        ret_ious = np.concatenate((ret_ious, [iou_pair[_pr_idx, best_match]]))
                        ret_match = np.concatenate((ret_match, np.array([[_pr_idx, best_match]])))
                        if iou_pair[_pr_idx, best_match] >= pos_thres:
                            # mark as Dup here, will edit the one with largest confidence to TP
                            ret_type = np.concatenate((ret_type, [5]))
                        else:
                            ret_type = np.concatenate((ret_type, [7])) # Loc
                        continue # if found TP match, do not match Cls error
                diff_cat_gt = possible_match_gt[gt_cat[possible_match_gt]!=pr_cat[_pr_idx]]
                diff_cat_gt = diff_cat_gt[gt_iscrowd[diff_cat_gt]==0]
                if len(diff_cat_gt) > 0:
                    # match only one Cls error
                    best_match = diff_cat_gt[np.argmax(
                        iou_pair[_pr_idx, diff_cat_gt] + np.exp(-gt_match_cnt[diff_cat_gt])
                    )]
                    gt_match_cnt[best_match] += 1
                    ret_ious = np.concatenate((ret_ious, [iou_pair[_pr_idx, best_match]]))
                    ret_match = np.concatenate((ret_match, np.array([[_pr_idx, best_match]])))
                    if iou_pair[_pr_idx, best_match] >= pos_thres:
                        ret_type = np.concatenate((ret_type, [6])) # Cls
                    else:
                        ret_type = np.concatenate((ret_type, [8])) # Cls+Loc
            for _gt_idx in np.where(gt_iscrowd==0)[0]:
                # if not matched as TP, Loc or Cls, consider as Miss (even if matched as Cls+Loc)
                if _gt_idx not in ret_match[ret_type!=8,1]:
                    ret_ious = np.concatenate((ret_ious, [0]))
                    ret_match = np.concatenate((ret_match, np.array([[-1, _gt_idx]])))
                    ret_type = np.concatenate((ret_type, [10])) # Miss
                gtm_pr_list = (ret_match[:, 1]==_gt_idx) & (ret_match[:, 0]!=-1)
                # select only one Non-Dup pair for each gt
                # in the order [TP, Loc, Cls, Loc+Cls]
                for rt in [5, 7, 6, 8]:
                    match_prs = ret_match[np.logical_and(gtm_pr_list, ret_type==rt), 0]
                    if len(match_prs) > 0:
                        best_match = match_prs[np.argsort(-pr_conf[match_prs])[0]]
                        # edit type of best_match to non-dup type by minus 4
                        ret_type[np.logical_and(ret_match[:,0]==best_match, gtm_pr_list)] = rt - 4
                        break

                # select one non-dup pair for each pr cat
                if len(pr_cat) == 0:
                    continue
                ret_pr_cat = pr_cat[ret_match[:, 0]]
                gtm_pr_cat = np.unique(ret_pr_cat[gtm_pr_list])
                for _cat in gtm_pr_cat:
                    if _cat == gt_cat[_gt_idx]:
                        continue
                    # if has been matched in a non-dup pair, continue
                    if np.any(ret_type[gtm_pr_list & (ret_pr_cat==_cat)]<=4):
                        continue
                    match_prs = ret_match[gtm_pr_list & (ret_type==6) & (ret_pr_cat==_cat), 0]
                    if len(match_prs) > 0:
                        best_match = match_prs[np.argsort(-pr_conf[match_prs])[0]]
                        # edit type of best_match to cls
                        ret_type[np.logical_and(ret_match[:,0]==best_match, gtm_pr_list)] = 11
                    else:
                        match_prs = ret_match[gtm_pr_list & (ret_type==8) & (ret_pr_cat==_cat), 0]
                        if len(match_prs) > 0:
                            best_match = match_prs[np.argsort(-pr_conf[match_prs])[0]]
                            # edit type of best_match to cls+loc
                            ret_type[np.logical_and(ret_match[:,0]==best_match, gtm_pr_list)] = 12

            return ret_match, ret_ious, ret_type

        self.pairs_map_under_iou_thresholds = {}
        bg_thres = 0.1 # minimum overlap
        for pos_thres in self.iou_thresholds:
            self.pairs_map_under_iou_thresholds[pos_thres] = {}
            for conf_thres in self.conf_thresholds:
                # only contains matched gt and pr
                predict_label_pairs = -1*np.ones((0, 2), dtype=np.int32)
                predict_label_ious = np.zeros(0)
                predict_type = np.zeros(0, dtype=np.int32)
                for imageidx in tqdm(range(len(self.image2index))):
                    if not self.segmentation:
                        matches, ious, types = compute_per_image(self.raw_predicts[self.imageid2raw_predict[imageidx][0]:self.imageid2raw_predict[imageidx][1]],
                                                    self.raw_labels[self.imageid2raw_label[imageidx][0]:self.imageid2raw_label[imageidx][1]], pos_thres, conf_thres, bg_thres)
                    else:
                        matches, ious, types = compute_per_image((self.raw_predicts[self.imageid2raw_predict[imageidx][0]:self.imageid2raw_predict[imageidx][1]],
                                                                self.predict_masks[self.imageid2raw_predict[imageidx][0]:self.imageid2raw_predict[imageidx][1]]),
                                                                (self.raw_labels[self.imageid2raw_label[imageidx][0]:self.imageid2raw_label[imageidx][1]],
                                                                self.label_masks[self.imageid2raw_label[imageidx][0]:self.imageid2raw_label[imageidx][1]]), 
                                                                pos_thres, conf_thres, bg_thres)
                    if len(matches)>0:
                        matches[matches[:,1]!=-1,1]+=self.imageid2raw_label[imageidx][0]
                        matches[matches[:,0]!=-1,0]+=self.imageid2raw_predict[imageidx][0]
                        predict_label_pairs = np.concatenate((predict_label_pairs, matches))
                        predict_label_ious = np.concatenate((predict_label_ious, ious))
                        predict_type = np.concatenate((predict_type, types))
                self.pairs_map_under_iou_thresholds[pos_thres][conf_thres] = (predict_label_pairs, predict_label_ious, predict_type)
        return self.pairs_map_under_iou_thresholds
    
    def constructRangeTree(self):
        self.rangeTrees = {}
        for iou_thres in self.iou_thresholds:
            self.rangeTrees[iou_thres] = {}
            for conf_thres in self.conf_thresholds:
                pairs, ious, types = self.pairs_map_under_iou_thresholds[iou_thres][conf_thres]
                directions = self.directions_map[iou_thres][conf_thres]

                pair_pr_size, pair_pr_cat, pair_pr_ar, pair_gt_size, pair_gt_cat, pair_gt_ar, pair_pr_conf = [],[],[],[],[],[],[]
                pair_size_cmp = []
                for p, i, t, d in tqdm(zip(pairs, ious, types, directions)):
                    pr, gt = p[0], p[1]
                    # gt class, size, ar
                    if gt == -1:
                        pair_gt_cat.append(len(self.names)-1)
                        pair_gt_size.append(0)
                        pair_gt_ar.append(0)
                        pair_size_cmp.append(0)
                    else:
                        pair_gt_cat.append(self.raw_labels[gt, 0])
                        pair_gt_size.append(min(1,self.label_size[gt]))
                        pair_gt_ar.append(self.label_true_ar[gt])
                        if pr == -1:
                            pair_size_cmp.append(0)
                        else:
                            if i > iou_thres:
                                pair_size_cmp.append(0)
                            else:
                                if self.predict_size[pr] > self.label_size[gt]:
                                    pair_size_cmp.append(1)
                                else:
                                    pair_size_cmp.append(2)
                    # pr class, size, ar, conf
                    if pr == -1:
                        pair_pr_cat.append(len(self.names)-1)
                        pair_pr_size.append(0)
                        pair_pr_ar.append(0)
                        pair_pr_conf.append(0)
                    else:
                        pair_pr_cat.append(self.raw_predicts[pr, 0])
                        pair_pr_size.append(self.predict_size[pr])
                        pair_pr_ar.append(self.predict_true_ar[pr])
                        pair_pr_conf.append(self.raw_predicts[pr, 1])

                pair_pr_cat, pair_gt_cat = np.array(pair_pr_cat), np.array(pair_gt_cat)
                pair_size_cmp = np.array(pair_size_cmp)
                pair_pr_conf, pair_pr_size, pair_pr_ar, pair_gt_size, pair_gt_ar = \
                    np.array(pair_pr_conf), np.array(pair_pr_size), np.array(pair_pr_ar), np.array(pair_gt_size), np.array(pair_gt_ar)
                tree = RangeTree()
                tree.AddFeatures([
                    ('label_aspect_ratio', 'index', 0),
                    ('label_size', 'index', 1),
                    ('predict_size', 'index', 2),
                    ('predict_aspect_ratio', 'index', 3),
                    ('conf_range', 'index', 4),
                    ('predict', 'other', 5),
                    ('label', 'other', 6),
                    ('types', 'other', 7),
                    ('size_comparison', 'other', 8),
                    ('direction', 'other', 9)
                ])
                tmp_directions = directions.copy()
                tmp_directions[tmp_directions==-1] = 8
                data = np.concatenate([[pair_gt_ar], [pair_gt_size], [pair_pr_size], [pair_pr_ar], 
                                       [pair_pr_conf], [pair_pr_cat], [pair_gt_cat], [types], [pair_size_cmp], [tmp_directions]]).T
                tree.Init(data)
                self.rangeTrees[iou_thres][conf_thres] = tree

    def filterSamples(self, query = None):
        """
            return index of pairs in predict_label_pairs
        """
        iou_thres, conf_thres = self.getThresholds(query)
        tree = self.rangeTrees[iou_thres][conf_thres]
        query = self.getQuery(query)
        sample_idx = tree.QueryIndex(query)
        return sample_idx

    def getQuery(self, query):
        default_query = {
            "label_size": [0, 1],
            "predict_size": [0, 1],
            "label_aspect_ratio": [0, 1],
            "predict_aspect_ratio": [0, 1],
            "conf_range": [0, 1],
            "label": np.arange(len(self.classID2Idx)).tolist(),
            "predict": np.arange(len(self.classID2Idx)).tolist(),
            "types": [1, 2, 3, 4, 9, 10, 11, 12],
            "size_comparison": [0, 1, 2], # 0: good, 1: predict > label, 2: label > predict
            "direction": [0,1,2,3,4,5,6,7,8], # 0-8 for 9 different directions
        }
        new_query = default_query
        if query is not None:
            new_query = {**default_query, **query}
            for k in query.keys():
                if k not in default_query:
                    del new_query[k]
        return new_query

    def hoverMatrixCell(self, query, targets):
        iou_thres, conf_thres = self.getThresholds(query)
        tree = self.rangeTrees[iou_thres][conf_thres]
        ret_dict = {}
        query = self.getQuery(query)
        for tar, ran in targets.items():
            if tar.startswith('conf') or tar.startswith('pr'):
                query_types = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12]
            else:
                query_types = [1, 2, 3, 4, 10]
            dist = tree.QueryDistribution(tar, {
                **query,
                tar: [max(ran[0], query[tar][0]), min(ran[1], query[tar][1])],
                "types": query_types,
            }, {'min': ran[0], 'max': ran[1]})[1]
            ret_dict[tar] = dist
        return ret_dict

    def getConfusionMatrix(self, query = None):
        """filtered confusion matrix

        Args:
            querys (dict): {label/predict size:[a, b], label/predict aspect_ratio:[a, b], direction: [0,..,8],
            label/predict: np.arange(len(self.names)-1)}
        """
        statistics_modes = ['count']
        if query is not None and "return" in query:
            statistics_modes = query['return']
        iou_thres, conf_thres = self.getThresholds(query)
        tar_label, tar_predict = None, None
        if 'label' in query:
            tar_label = query['label']
        if 'predict' in query:
            tar_predict = query['predict']
        query["label"] = np.arange(len(self.classID2Idx)).tolist()
        query["predict"] = np.arange(len(self.classID2Idx)).tolist()
        tree = self.rangeTrees[iou_thres][conf_thres]
        ret_matrices = []
        query = self.getQuery(query)
        # print(query)
        count_mat = None
        for statistics_mode in statistics_modes:
            mat = []
            if statistics_mode == 'count':
                mat = tree.QueryMatrix('label', 'predict', query)
                count_mat = mat
            elif statistics_mode == 'direction':
                for i in range(9):
                    mat.append(tree.QueryMatrix('label', 'predict', {**query, 'direction': [i]}))
                mat = np.concatenate([np.array(mm).reshape(np.array(mm).shape+(1,)) for mm in mat], axis=2).tolist()
            elif statistics_mode =='size_comparison':
                for i in range(1, 3):
                    mat.append(tree.QueryMatrix('label', 'predict', {**query, 'size_comparison': [i]}))
                mat = np.concatenate([np.array(mm).reshape(np.array(mm).shape+(1,)) for mm in mat], axis=2).tolist()
            ret_matrices.append(mat)
        if tar_label is not None:
            for mat in ret_matrices:
                for i in range(len(mat)):
                    for j in range(len(mat[0])):
                        if i in tar_label and j in tar_predict:
                            continue
                        if type(mat[i][j]) == list:
                            mat[i][j] = [0] * len(mat[i][j])
                        else:
                            mat[i][j] = 0
        # print(ret_matrices)
        # reorder after normalization by row
        if count_mat is not None:
            from scipy.cluster import hierarchy
            count_mat = np.array(count_mat, dtype=np.float64)
            reorder_hierarchy = self.hierarchy.copy()
            top_level_mat = np.zeros((len(reorder_hierarchy), len(reorder_hierarchy)), dtype=np.float64)
            for i in range(len(reorder_hierarchy)):
                for j in range(len(reorder_hierarchy)):
                    row_ids = [self.name2idx[name] for name in reorder_hierarchy[i]["children"]]
                    col_ids = [self.name2idx[name] for name in reorder_hierarchy[j]["children"]]
                    top_level_mat[i][j] = np.sum(count_mat[row_ids][:, col_ids])
            top_level_mat /= (top_level_mat.sum(axis=1)+1).astype(np.float64) # normalize by row
            top_order = hierarchy.leaves_list(hierarchy.optimal_leaf_ordering(hierarchy.linkage(top_level_mat, 'ward'), top_level_mat))
            reorder_hierarchy = [reorder_hierarchy[i] for i in top_order]
            count_mat /= (count_mat.sum(axis=1)+1).astype(np.float64)
            for i in range(len(reorder_hierarchy)):
                if len(reorder_hierarchy[i]["children"]) < 3:
                    continue
                cld_ids = [self.name2idx[name] for name in reorder_hierarchy[i]["children"]]
                cld_mat = count_mat[cld_ids][:, cld_ids]
                cld_order = hierarchy.leaves_list(hierarchy.optimal_leaf_ordering(hierarchy.linkage(cld_mat, 'ward'), cld_mat))
                reorder_hierarchy[i]["children"] = [reorder_hierarchy[i]["children"][j] for j in cld_order]
            # print(reorder_hierarchy)
            
        return {
            'matrix': ret_matrices,
            'hierarchy': reorder_hierarchy,
        }

    def getDistributionByAttrName(self, query, target_attr, attr_range=[0, 1]):
        iou_thres, conf_thres = self.getThresholds(query)
        tree = self.rangeTrees[iou_thres][conf_thres]
        query = self.getQuery(query)
        query[target_attr] = [max(attr_range[0], query[target_attr][0]), min(attr_range[1], query[target_attr][1])]
        if target_attr.startswith('conf') or target_attr.startswith('pr'):
            query_types = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12]
        else:
            query_types = [1, 2, 3, 4, 10]
        query["types"] = query_types
        dist = tree.QueryDistribution(target_attr, query, {'min': attr_range[0], 'max': attr_range[1]})[1]
        return dist

    def getZoomInDistribution(self, query):
        assert "query_key" in query
        target = query["query_key"]
        target_range = query["range"]
        K = 50
        split_pos = np.array([target_range[0]+i*(target_range[1]-target_range[0])/K for i in range(K+1)])
        all_dist = self.getDistributionByAttrName({}, target, target_range)
        select_dist = self.getDistributionByAttrName(query, target, target_range)
        return {
            'allDist': all_dist,
            'selectDist': select_dist,
            'split': split_pos.tolist()
        }

    def transformBottomLabelToTop(self, topLabels):
        topLabelChildren = {}
        topLabelSet = set(topLabels)
        def dfs(nodes):
            childrens = []
            for root in nodes:
                if type(root)==str:
                    childrens.append(root)
                    if root in topLabelSet:
                        topLabelChildren[root] = [root]
                else:
                    rootChildren = dfs(root['children'])
                    childrens += rootChildren
                    if root['name'] in topLabelSet:
                        topLabelChildren[root['name']] = rootChildren
            return childrens
        dfs(self.hierarchy)
        childToTop = {}
        for topLabelIdx in range(len(topLabels)):
            for child in topLabelChildren[topLabels[topLabelIdx]]:
                childToTop[child] = topLabelIdx
        n = len(self.names)
        labelTransform = np.zeros(n, dtype=int)
        for i in range(n):
            if not childToTop.__contains__(self.names[i]):
                pass
                # print('not include ' + self.names[i])
            else:
                labelTransform[i] = childToTop[self.names[i]]
        return labelTransform.astype(int)
  
    def pairIDtoImageID(self, boxID, iou_thres, conf_thres):
        # boxId here is pair id
        pairs, _, _ = self.pairs_map_under_iou_thresholds[iou_thres][conf_thres]
        if pairs[boxID, 1] == -1:
            return self.raw_predict2imageid[pairs[boxID, 0]]
        return self.raw_label2imageid[pairs[boxID, 1]]
    
    def _getBoxesByImgId(self, img_id: int, iou_thres: float, conf_thres: float):
        predict_label_pairs, _, _ = self.pairs_map_under_iou_thresholds[iou_thres][conf_thres]
        # as 1 gt may occur in many pairs, so pr_boxes will only contain predict indexes, and so as gt_boxes
        pr_boxes = predict_label_pairs[np.logical_and(predict_label_pairs[:, 0]>=self.imageid2raw_predict[img_id][0],
                                                      predict_label_pairs[:, 0]< self.imageid2raw_predict[img_id][1]), 0]
        gt_boxes = np.arange(self.imageid2raw_label[img_id][0], self.imageid2raw_label[img_id][1])
        return pr_boxes.tolist(), gt_boxes.tolist()

    def _getBoxByBoxId(self, box_id: int, iou_thres: float, conf_thres: float):
        predict_label_pairs, _, _ = self.pairs_map_under_iou_thresholds[iou_thres][conf_thres]
        pr, gt = predict_label_pairs[box_id]
        pr_box, gt_box = [], []
        if pr > -1:
            pr_box.append(int(pr))
        if gt > -1:
            gt_box.append(int(gt))
        if gt > -1 and pr > -1:
            cand_pairs = predict_label_pairs[(predict_label_pairs[:,1]==gt) & (predict_label_pairs[:,0]!=-1) & (predict_label_pairs[:,0]!=pr)]
            cand_pairs = cand_pairs[self.raw_predicts[cand_pairs[:,0], 0]==self.raw_predicts[pr, 0]]
            pr_box += cand_pairs[:, 0].tolist()

        return pr_box, gt_box
        
    def getImagebox(self, boxID: int, showall: str, iou_thres: float, conf_thres: float):
        finalBoxes = []
        img_format = os.listdir(self.images_path)[0].split('.')[-1]
        img = Image.open(os.path.join(self.images_path, self.index2image[self.pairIDtoImageID(boxID, iou_thres, conf_thres)]+f'.{img_format}'))
        amp = [img.width,img.height]
        if showall == 'all':
            imgID = self.pairIDtoImageID(boxID, iou_thres, conf_thres)
            pr_boxes, gt_boxes = self._getBoxesByImgId(imgID, iou_thres, conf_thres)
        elif showall == 'single':
            pr_boxes, gt_boxes = self._getBoxByBoxId(boxID, iou_thres, conf_thres)
        if not self.segmentation:
            for box in pr_boxes:
                finalBoxes.append({
                    "box": (self.raw_predicts[box, 2:6]).tolist(),
                    "size": float(self.predict_size[box]),
                    "type": "pred",
                    "class": self.names[int(self.raw_predicts[box, 0])],
                    "id": box,
                    "score": float(self.raw_predicts[box, 1])
                })
            for box in gt_boxes:
                finalBoxes.append({
                    "box": (self.raw_labels[box, 1:5]).tolist(),
                    "size": float(self.label_size[box]),
                    "type": "gt",
                    "class": self.names[int(self.raw_labels[box, 0])],
                    "id": box,
                    "score": 0
                })
        else:
            for box in pr_boxes:
                polygon = mask_to_polygons(mask_util.decode({'counts': self.predict_masks[box].encode('utf-8'), 
                                                                    'size': self.raw_predicts[box, 2:4].astype(np.int32)}))[0]
                polygon = [poly.reshape(-1, 2).tolist() for poly in polygon]
                finalBoxes.append({
                    "poly": polygon,
                    "size": float(self.predict_size[box]),
                    "type": "pred",
                    "class": self.names[int(self.raw_predicts[box, 0])],
                    "id": box,
                    "score": float(self.raw_predicts[box, 1])
                })
            for box in gt_boxes:
                polygon = mask_to_polygons(mask_util.decode({'counts': self.label_masks[box], 
                                                                    'size': self.raw_labels[box, 2:4].astype(np.int32)}))[0]
                polygon = [poly.reshape(-1, 2).tolist() for poly in polygon]
                finalBoxes.append({
                    "poly": polygon,
                    "size": float(self.label_size[box]),
                    "type": "gt",
                    "class": self.names[int(self.raw_labels[box, 0])],
                    "id": box,
                    "score": 0
                })
        return {
            "boxes": finalBoxes,
            "image": amp,
            "seg": self.segmentation
        }
    
    def getImage(self, boxID: int, show: str, showall: str, iou_thres: float, conf_thres: float, hideBox = False,
                 gt_color = 'rgb(27, 251, 254)', pr_color = 'rgb(253, 6, 253)'):
        # gt_color = (27, 251, 254)
        # pr_color = (253, 6, 253)
        img_format = os.listdir(self.images_path)[0].split('.')[-1]
        img = Image.open(os.path.join(self.images_path, self.index2image[self.pairIDtoImageID(boxID, iou_thres, conf_thres)]+f'.{img_format}'))
        amp = np.array([img.width,img.height,img.width,img.height])
        if show=='box':
            # first get box position and crop
            predictXYXY_arr, labelXYXY_arr = [], []
            pr_boxes, gt_boxes = self._getBoxByBoxId(boxID, iou_thres, conf_thres)
            for predictBox in pr_boxes:
                if not self.segmentation:
                    predictXYXY_arr.append(xywh2xyxy(self.raw_predicts[predictBox, 2:6]*amp).tolist())
                else:
                    predictXYXY_arr.append(xywh2xyxy(self.predict_bbox[predictBox]*amp).tolist())
            for labelBox in gt_boxes:
                if not self.segmentation:
                    labelXYXY_arr.append(xywh2xyxy(self.raw_labels[labelBox, 1:5]*amp).tolist())
                else:
                    labelXYXY_arr.append(xywh2xyxy(self.label_bbox[labelBox]*amp).tolist())
            im, cropbox = self.cropImageByBox(img, predictXYXY_arr, labelXYXY_arr, [img.width, img.height])
            if True:
                anno = Annotator(np.array(im), pil=True)
            else:
                # to gray image
                anno = Annotator(np.repeat(np.array(im).mean(axis=2, keepdims=True), 3, axis=2).astype(np.uint8), pil=True)
            predict_polys_arr, label_polys_arr = [], []
            for predictBox, predictXYXY in zip(pr_boxes, predictXYXY_arr):
                predictXYXY[0] -= cropbox[0]
                predictXYXY[2] -= cropbox[0]
                predictXYXY[1] -= cropbox[1]
                predictXYXY[3] -= cropbox[1]
                if self.segmentation:
                    predict_polys = mask_to_polygons(mask_util.decode({'counts': self.predict_masks[predictBox].encode('utf-8'), 
                                                                    'size': self.raw_predicts[predictBox, 2:4].astype(np.int32)}))[0]
                    predict_polys = [poly.reshape(-1, 2) for poly in predict_polys]
                    predict_polys = [poly - cropbox[:2] for poly in predict_polys]
                    predict_polys_arr += predict_polys
            for labelBox, labelXYXY in zip(gt_boxes, labelXYXY_arr):
                labelXYXY[0] -= cropbox[0]
                labelXYXY[2] -= cropbox[0]
                labelXYXY[1] -= cropbox[1]
                labelXYXY[3] -= cropbox[1]
                if self.segmentation:
                    label_polys = mask_to_polygons(mask_util.decode({'counts': self.label_masks[labelBox].encode('utf-8'), 
                                                                    'size': self.raw_labels[labelBox, 2:4].astype(np.int32)}))[0]
                    label_polys = [poly.reshape(-1, 2) for poly in label_polys]
                    label_polys = [poly - cropbox[:2] for poly in label_polys]
                    label_polys_arr += label_polys
            stroke = int(max(anno.im.width, anno.im.height)/20)
            if not self.segmentation:
                for predictXYXY in predictXYXY_arr:
                    anno.box_label(predictXYXY, color=pr_color, width=stroke)
                for labelXYXY in labelXYXY_arr:
                    anno.box_label(labelXYXY, color=gt_color, width=max(math.ceil(stroke*0.8), 1))
            else:
                for poly in predict_polys_arr:
                    anno.polygon(poly.reshape(-1).tolist(), outline_color=pr_color, width=stroke)
                for poly in label_polys_arr:
                    anno.polygon(poly.reshape(-1).tolist(), outline_color=gt_color, width=stroke)
        else:
            if True:
                anno = Annotator(np.array(img), pil=True)
            else:
                # to gray image
                anno = Annotator(np.repeat(np.array(img).mean(axis=2, keepdims=True), 3, axis=2).astype(np.uint8), pil=True)
            if showall == 'all':
                imgID = self.pairIDtoImageID(boxID, iou_thres, conf_thres)
                pr_boxes, gt_boxes = self._getBoxesByImgId(imgID, iou_thres, conf_thres)
            elif showall == 'single':
                pr_boxes, gt_boxes = self._getBoxByBoxId(boxID, iou_thres, conf_thres)
            for box in pr_boxes:
                if not self.segmentation:
                    predictXYXY = xywh2xyxy(self.raw_predicts[box, 2:6]*amp).tolist()
                    anno.box_label(predictXYXY, color=pr_color)
                else:
                    predict_polys = mask_to_polygons(mask_util.decode({'counts': self.predict_masks[box].encode('utf-8'), 
                                                                    'size': self.raw_predicts[box, 2:4].astype(np.int32)}))[0]
                    for poly in predict_polys:
                        anno.polygon(poly.tolist(), outline_color=pr_color)
            for box in gt_boxes:
                if not self.segmentation:
                    labelXYXY = xywh2xyxy(self.raw_labels[box, 1:5]*amp).tolist()
                    anno.box_label(labelXYXY, color=gt_color)
                else:
                    label_polys = mask_to_polygons(mask_util.decode({'counts': self.label_masks[box].encode('utf-8'), 
                                                                    'size': self.raw_labels[box, 2:4].astype(np.int32)}))[0]
                    for poly in label_polys:
                        anno.polygon(poly.tolist(), outline_color=gt_color)
        output = io.BytesIO()
        if hideBox:
            img.save(output, format="JPEG")
        else:
            anno.im.save(output, format="JPEG")
        return output
            
    def cropImageByBox(self, img, predictBox, labelBox, shape):
        box = [-1, -1, -1, -1]
        for bb in (predictBox + labelBox):
            if box[0]==-1:
                box = bb.copy()
            else:
                box = [
                    min(box[0], bb[0]),
                    min(box[1], bb[1]),
                    max(box[2], bb[2]),
                    max(box[3], bb[3])
                ]
        center = [(box[0]+box[2])/2, (box[1]+box[3])/2]
        size = max((box[2]-box[0])/2, (box[3]-box[1])/2)
        if (box[2]-box[0])*(box[3]-box[1])<400:
            size += 10
        box = [
            max(center[0]-size, 0),
            max(center[1]-size, 0),
            min(center[0]+size, shape[0]),
            min(center[1]+size, shape[1])
        ]
        return img.crop(box), box
        
    def getImagesInConsuionMatrixCell(self, labels: list, preds: list, query = None) -> list:
        """
        return images in a cell of confusionmatrix

        Args:
            labels (list): true labels of corresponding cell
            preds (list): predicted labels of corresponding cell

        Returns:
            list: images id
        """ 
        # convert list of label names to dict
        # find images
        labelSet = set()
        for label in labels:
            labelSet.add(self.name2idx[label])
        predSet = set()
        for label in preds:
            predSet.add(self.name2idx[label])
        query["label"] = list(labelSet)
        query["predict"] = list(predSet)
        sample_idx = self.filterSamples(query)
        return sample_idx

    def getClassStatistics(self, query = None):
        """
            area: [0, 1, 2, 3] => [all, small, medium, large]
            mdets: [0, 1, 2] => [1, 10, 100]
            ap: 2 / 1 / 0 => gt quantity / precision / recall
            iouThr: None / 0.50 / 0.75
        """
        default_query = {
            "ap": 1
        }
        if query is not None:
            query = {**default_query, **query}
        query["types"] = [i for i in range(1, 13)]
        iou_thres, conf_thres = self.getThresholds(query)
        pairs, _, types = self.pairs_map_under_iou_thresholds[iou_thres][conf_thres]
        all_pair_ids = np.array(self.filterSamples(query))
        pairs, types = pairs[all_pair_ids], types[all_pair_ids]
        ap = query['ap']
        ret_arr = []
        TP_prs = pairs[types==1, 0]
        for i in range(len(self.classID2Idx)-1):
            cat_prs = pairs[np.logical_and(pairs[:, 0]!=-1, self.raw_predicts[pairs[:, 0], 0]==i), 0]
            cat_prs = cat_prs[np.argsort(-self.raw_predicts[cat_prs, 1])]
            tp = np.isin(cat_prs, TP_prs)
            fp = ~tp
            tp = np.cumsum(tp)
            fp = np.cumsum(fp)
            nd = len(tp)
            gt_count = np.count_nonzero(self.raw_labels[np.unique(pairs[pairs[:,1]!=-1, 1]), 0]==i)
            if ap == 2: # quantity of gt
                ret_arr.append(gt_count)
                continue
            if gt_count == 0:
                ret_arr.append(0)
                continue
            else:
                rc = tp / gt_count
            pr = tp / (fp+tp+np.spacing(1))
            if ap == 0:
                if nd:
                    ret_arr.append(rc[-1])
                else:
                    ret_arr.append(0)
            else:
                q = np.zeros((101,))
                pr = pr.tolist(); q = q.tolist()
                for i in range(nd-1, 0, -1):
                    if pr[i] > pr[i-1]:
                        pr[i-1] = pr[i]

                inds = np.searchsorted(rc, np.linspace(.0, 1.00, int(np.round((1.00 - .0) / .01)) + 1, endpoint=True), side='left')
                try:
                    for ri, pi in enumerate(inds):
                        q[ri] = pr[pi]
                except:
                    pass
                ret_arr.append(np.mean(q))
        return np.array(ret_arr).tolist()

    def getSlices(self, query):
        iou_thres, conf_thres = self.getThresholds(query)
        pairs, ious, types = self.pairs_map_under_iou_thresholds[iou_thres][conf_thres]
        directions = self.directions_map[iou_thres][conf_thres]

        pair_pr_size, pair_pr_cat, pair_pr_ar, pair_gt_size, pair_gt_cat, pair_gt_ar, pair_pr_conf = [],[],[],[],[],[],[]
        for p, i, t, d in tqdm(zip(pairs, ious, types, directions)):
            pr, gt = p[0], p[1]
            # gt class, size, ar
            if gt == -1:
                pair_gt_cat.append(len(self.names)-1)
                pair_gt_size.append(-1)
                pair_gt_ar.append(-1)
            else:
                pair_gt_cat.append(self.raw_labels[gt, 0])
                pair_gt_size.append(min(1,self.label_size[gt]))
                pair_gt_ar.append(self.label_true_ar[gt])
            # pr class, size, ar, conf
            if pr == -1:
                pair_pr_cat.append(len(self.names)-1)
                pair_pr_size.append(-1)
                pair_pr_ar.append(-1)
                pair_pr_conf.append(-1)
            else:
                pair_pr_cat.append(self.raw_predicts[pr, 0])
                pair_pr_size.append(self.predict_size[pr])
                pair_pr_ar.append(self.predict_true_ar[pr])
                pair_pr_conf.append(self.raw_predicts[pr, 1])

        pair_pr_cat, pair_gt_cat = np.array(pair_pr_cat), np.array(pair_gt_cat)
        pair_pr_conf, pair_pr_size, pair_pr_ar, pair_gt_size, pair_gt_ar = \
            np.array(pair_pr_conf), np.array(pair_pr_size), np.array(pair_pr_ar), np.array(pair_gt_size), np.array(pair_gt_ar)

        # remove duplicate
        non_dup_pairs = np.isin(types, [1,3])

        pair_data_dict = {
            'gt_ar': pair_gt_ar,
            'gt_size': pair_gt_size,
            'pr_size': pair_pr_size,
            'pr_ar': pair_pr_ar,
            'pr_conf': pair_pr_conf
        }

        non_dup_pair_data_dict = {
            'gt_ar': pair_gt_ar[non_dup_pairs],
            'gt_size': pair_gt_size[non_dup_pairs],
            'pr_size': pair_pr_size[non_dup_pairs],
            'pr_ar': pair_pr_ar[non_dup_pairs],
            'pr_conf': pair_pr_conf[non_dup_pairs]
        }

        def discretize_data_by_equal_frequency(data, K=10):
            sorted_data = np.array(sorted(data))
            data_split = []
            if sorted_data[0] < 0:
                data_split.append(-1)
                # K -= 1
            sorted_data = sorted_data[sorted_data>=0]
            cnt = len(sorted_data)
            for i in range(K+1):
                data_split.append(sorted_data[min(cnt//K*i, cnt-1)])
            data_split[-1]+=1e-6
            return data_split

        pair_data_split = {}
        for key, data in non_dup_pair_data_dict.items():
            pair_data_split[key] = discretize_data_by_equal_frequency(data, K=10)
        pair_data_split_100 = {}
        for key, data in non_dup_pair_data_dict.items():
            pair_data_split_100[key] = discretize_data_by_equal_frequency(data, K=100)
        split_info_dict = {}
        for key, splits in pair_data_split.items():
            K = len(splits)
            split_info_dict[key] = ['[{},{})'.format(
                round(splits[i], 4), round(splits[i+1], 4)) for i in range(K-1)]

        def construct_dataFrame(data_dict, target_idx):
            data_columns = []
            discretized_data = np.zeros((len(target_idx), 0), dtype=bool)
            for key, data in data_dict.items():
                data_split = pair_data_split[key]
                K = len(data_split) - 1
                for i in range(K):
                    sp_data = np.zeros((len(target_idx), 1), dtype=bool)
                    sp_data[np.logical_and(data[target_idx]>=data_split[i], data[target_idx]<data_split[i+1])]=True
                    discretized_data = np.concatenate((discretized_data, sp_data), axis=1)
                    data_columns.append(' '.join([key, str(i), \
                                        '~'.join([str(round(data_split[i], 4)), str(round(data_split[i+1], 4))])]))
            df = pd.DataFrame(discretized_data, columns=data_columns)
            return df

        transform_name_dict = {
            'gt_ar': "label_aspect_ratio",
            'gt_size': "label_size",
            'pr_conf': "conf_range",
            'pr_ar': "predict_aspect_ratio",
            'pr_size': "predict_size",
        }
        min_sup = 0.1
        slice_arr = []
        for i in range(len(self.names)-1):
            for j in range(len(self.names)-1):
                if i!=j:
                    continue
                target_idx = np.where(np.logical_and(pair_pr_cat[non_dup_pairs]==i, pair_gt_cat[non_dup_pairs]==j))[0]
                if np.count_nonzero(target_idx) < 100:
                    continue
                all_idx = np.where(np.logical_and(pair_pr_cat==i, pair_gt_cat==j))[0]
                non_dup_df = construct_dataFrame(non_dup_pair_data_dict, target_idx)
                all_df = construct_dataFrame(pair_data_dict, all_idx)
                freq_df = apriori(non_dup_df, min_support=min_sup, use_colnames=True)
                for sup, col_names in freq_df.values:
                    item_idx = non_dup_df[list(col_names)].all(1).to_numpy()
                    pr_idx = all_df[list(col_names)].all(1).to_numpy()
                    tp = types[all_idx][pr_idx]==1
                    gt_count = np.count_nonzero(item_idx)
                    if gt_count < 50:
                        continue
                    slice_dict = {
                        'pr_cat': self.names[i],
                        'gt_cat': self.names[j],
                        'support': round(sup, 3),
                        'quantity': gt_count,
                        'subset_size': gt_count,
                        'recall': round(np.count_nonzero(tp)/gt_count, 3),
                        'precision': round(np.count_nonzero(tp)/np.count_nonzero(pr_idx), 3),
                        'info': { # for query
                            'predict': [i],
                            'label': [j],
                        }
                    }

                    # slice ap
                    cat_prs = pairs[all_idx][pr_idx, 0]
                    cat_ord = np.argsort(-self.raw_predicts[cat_prs, 1])
                    cat_prs = cat_prs[cat_ord]
                    tp = tp[cat_ord]
                    fp = ~tp
                    tp = np.cumsum(tp)
                    fp = np.cumsum(fp)
                    nd = len(tp)
                    rc = tp / gt_count
                    pr = tp / (fp + tp + np.spacing(1))
                    q = np.zeros((101,))
                    pr = pr.tolist(); q = q.tolist()
                    for ii in range(nd-1, 0, -1):
                        if pr[ii] > pr[ii-1]:
                            pr[ii-1] = pr[ii]
                    inds = np.searchsorted(rc, np.linspace(.0, 1.00, int(np.round((1.00 - .0) / .01)) + 1, endpoint=True), side='left')
                    try:
                        for ri, pi in enumerate(inds):
                            q[ri] = pr[pi]
                    except:
                        pass
                    slice_dict['ap'] = round(np.mean(q), 3)

                    for col in non_dup_pair_data_dict.keys():
                        slice_dict[col+'_ave'] = round(non_dup_pair_data_dict[col][target_idx][item_idx].mean(), 4)
                        slice_dict[col] = round((bisect.bisect_left(pair_data_split_100[col], slice_dict[col+'_ave'])-1)/100, 4)

                    for col in list(col_names):
                        col_arr = col.split(' ')
                        slice_dict['info'][transform_name_dict[col_arr[0]]] = \
                            [float(rr) for rr in col_arr[2].split('~')]
                    slice_arr.append(slice_dict)

        return {
            'data': slice_arr,
            'split': split_info_dict
        }


def box_area(box):
    # box = xyxy(4,n)
    return (box[2] - box[0]) * (box[3] - box[1])

def xywh2xyxy(x):
    # Convert nx4 boxes from [x, y, w, h] to [x1, y1, x2, y2] where xy1=top-left, xy2=bottom-right
    y = np.copy(x)
    if len(x.shape)==1:
        y[0] = x[0] - x[2] / 2  # top left x
        y[1] = x[1] - x[3] / 2  # top left y
        y[2] = x[0] + x[2] / 2  # bottom right x
        y[3] = x[1] + x[3] / 2  # bottom right y
        return y
    else:
        y[:, 0] = x[:, 0] - x[:, 2] / 2  # top left x
        y[:, 1] = x[:, 1] - x[:, 3] / 2  # top left y
        y[:, 2] = x[:, 0] + x[:, 2] / 2  # bottom right x
        y[:, 3] = x[:, 1] + x[:, 3] / 2  # bottom right y
        return y

def cal_iou(pr, gt, iscrowd = None):
        # https://github.com/pytorch/vision/blob/master/torchvision/ops/boxes.py
        """
            Return intersection-over-union (Jaccard index) of boxes.
            Both sets of boxes are expected to be in (x1, y1, x2, y2) format.
            Arguments:
                pr (Tensor[N, 4])
                gt (Tensor[M, 4])
                iscrowd ([M])
            Returns:
                iou (Tensor[N, M]): the NxM matrix containing the pairwise
                    IoU values for every element in boxes1 and boxes2
        """
        pr, gt = xywh2xyxy(pr), xywh2xyxy(gt)
        (a1, a2), (b1, b2) = np.array_split(pr[:, None],2,axis=2), np.array_split(gt, 2, axis=1)
        inter = (np.minimum(a2, b2) - np.maximum(a1, b1)).clip(0).prod(2)
        union = (box_area(pr.T)[:, None] + box_area(gt.T) - inter)
        if iscrowd is not None:
            crowd_idx = np.where(iscrowd == 1)[0]
            if len(crowd_idx) > 0:
                union[:, crowd_idx] = box_area(pr.T)[:, None]
        return inter / (union + 1e-6)

def box_iou(box1, box2):
    # https://github.com/pytorch/vision/blob/master/torchvision/ops/boxes.py
    """
    Return intersection-over-union (Jaccard index) of boxes.
    Both sets of boxes are expected to be in (x1, y1, x2, y2) format.
    Arguments:
        box1 (Tensor[N, 4])
        box2 (Tensor[M, 4])
    Returns:
        iou (Tensor[N, M]): the NxM matrix containing the pairwise
            IoU values for every element in boxes1 and boxes2
    """
    # inter(N,M) = (rb(N,M,2) - lt(N,M,2)).clamp(0).prod(2)
    (a1, a2), (b1, b2) = np.array_split(box1[:, None],2,axis=2), np.array_split(box2, 2, axis=1)
    inter = (np.minimum(a2, b2) - np.maximum(a1, b1)).clip(0).prod(2)
    union = (box_area(box1.T)[:, None] + box_area(box2.T) - inter)
    # IoU = inter / (area1 + area2 - inter)
    return inter / (union + 1e-6), union

def mask_to_polygons(mask):
    # https://github.com/facebookresearch/detectron2/blob/main/detectron2/utils/visualizer.py
    import cv2
    # cv2.RETR_CCOMP flag retrieves all the contours and arranges them to a 2-level
    # hierarchy. External contours (boundary) of the object are placed in hierarchy-1.
    # Internal contours (holes) are placed in hierarchy-2.
    # cv2.CHAIN_APPROX_NONE flag gets vertices of polygons from contours.
    mask = np.ascontiguousarray(mask)  # some versions of cv2 does not support incontiguous arr
    res = cv2.findContours(mask.astype("uint8"), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    hierarchy = res[-1]
    if hierarchy is None:  # empty mask
        return [], False
    has_holes = (hierarchy.reshape(-1, 4)[:, 3] >= 0).sum() > 0
    res = res[-2]
    res = [x.flatten() for x in res]
    # These coordinates from OpenCV are integers in range [0, W-1 or H-1].
    # We add 0.5 to turn them into real-value coordinate space. A better solution
    # would be to first +0.5 and then dilate the returned polygon by 0.5.
    res = np.array([x + 0.5 for x in res if len(x) >= 6], dtype=object)
    return res, has_holes
