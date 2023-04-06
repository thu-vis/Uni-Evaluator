#! /usr/bin/python3
import os
import argparse
from flask import Flask, jsonify, request, make_response
from data.dataCtrler import DataCtrler
from data.interaction import GridInteraction
from flask_cors import CORS
app = Flask(__name__)
CORS(app)

trainDataCtrler, validDataCtrler, singleValidGrid, singleTrainGrid, combinedValidGrid, combinedTrainGrid = None, None, None, None, None, None

def dataCtrlerChoose(request):
    global trainDataCtrler, validDataCtrler, singleValidGrid, singleTrainGrid, combinedValidGrid, combinedTrainGrid
    if request.json is not None and 'source' in request.json:
        source = request.json['source']
    else:
        source = request.args['source']
    if source=='train':
        return trainDataCtrler
    else:
        return validDataCtrler

def gridInteractionChoose(request):
    global trainDataCtrler, validDataCtrler, singleValidGrid, singleTrainGrid, combinedValidGrid, combinedTrainGrid
    if request.json is not None and 'matrixSource' in request.json:
        matrixSource = request.json['matrixSource']
    else:
        matrixSource = request.args['matrixSource']
    if request.json is not None and 'gridSource' in request.json:
        gridSource = request.json['gridSource']
    else:
        gridSource = request.args['gridSource']
    
    if matrixSource == 'valid':
        if gridSource == 'single':
            return singleValidGrid
        else:
            return combinedValidGrid
    else:
        if gridSource == 'single':
            return singleTrainGrid
        else:
            return combinedTrainGrid

@app.route('/api/metadata', methods=["POST"])
def metaData():
    dataCtrler = dataCtrlerChoose(request)
    return jsonify(dataCtrler.getMetaData())

@app.route('/api/confusionMatrix', methods=["POST"])
def confusionMatrix():
    dataCtrler = dataCtrlerChoose(request)
    query = None
    if 'query' in request.json:
        query = request.json['query']
    return jsonify(dataCtrler.getConfusionMatrix(query))

@app.route('/api/hoverMatrixCell', methods=["POST"])
def hoverMatrixCell():
    dataCtrler = dataCtrlerChoose(request)
    query = request.json['query']
    targets = request.json['targets']
    return jsonify(dataCtrler.hoverMatrixCell(query, targets))

@app.route('/api/zoomInDist', methods=["POST"])
def zoomInDist():
    dataCtrler = dataCtrlerChoose(request)
    query = None
    if 'query' in request.json:
        query = request.json['query']
    return jsonify(dataCtrler.getZoomInDistribution(query))

@app.route('/api/imagebox', methods=["POST"])
def imagebox():
    gridInteraction = gridInteractionChoose(request)
    boxID = int(request.json['boxID'])
    showall = request.json['showall']
    conf_thres = request.json['conf']
    iou_thres = request.json['iou']
    return jsonify(gridInteraction.getImageBoxDetail(boxID, showall, iou_thres, conf_thres))

@app.route('/api/image', methods=["GET"])
def imageGradient():
    gridInteraction = gridInteractionChoose(request)
    boxID = int(request.args['boxID'])
    showmode = request.args['show']
    showall = request.args['showall']
    iou_thres = float(request.args['iou'])
    conf_thres = float(request.args['conf'])
    hideBox = False
    if 'hidebox' in request.args:
        hideBox = request.args['hidebox']=='true'
    image_binary = gridInteraction.getImageThumbnail(boxID, showall, iou_thres, conf_thres, hideBox).getvalue()
    response = make_response(image_binary)
    response.headers.set('Content-Type', 'image/jpeg')
    response.headers.set(
        'Content-Disposition', 'attachment', filename='%s.jpg' % boxID)
    return response

@app.route('/api/images', methods=["POST"])
def imagesGradient():
    gridInteraction = gridInteractionChoose(request)
    boxIDs = request.json['boxIDs']
    showmode = request.json['show']
    iou_thres = request.json['iou']
    conf_thres = request.json['conf']
    return jsonify(gridInteraction.getImagesInGridLayout(boxIDs, showmode, iou_thres, conf_thres))

@app.route('/api/imagesInCell', methods=["POST"])
def confusionMatrixCell():
    dataCtrler = dataCtrlerChoose(request)
    labels = request.json['labels']
    preds = request.json['preds']
    query = None
    if 'query' in request.json:
        query = request.json['query']
    return jsonify(dataCtrler.getImagesInConsuionMatrixCell(labels, preds, query))

@app.route('/api/grid', methods=["POST"])
def grid():
    gridInteraction = gridInteractionChoose(request)
    nodes = request.json['nodes']
    constraints = None
    if 'constraints' in request.json:
        constraints = request.json['constraints']
    depth = request.json['depth']
    aspectRatio = 1
    if 'aspectRatio' in request.json:
        aspectRatio = request.json['aspectRatio']
    zoomin = True
    if 'zoomin' in request.json:
        zoomin = request.json['zoomin']
    conf_thres = request.json['conf']
    iou_thres = request.json['iou']
    return jsonify(gridInteraction.gridZoomIn(nodes, constraints, depth, aspectRatio, zoomin, iou_thres, conf_thres))

@app.route('/api/classStatistics', methods=["POST"])
def classStatistics():
    dataCtrler = dataCtrlerChoose(request)
    query = None
    if 'query' in request.json:
        query = request.json['query']
    return jsonify(dataCtrler.getClassStatistics(query))

@app.route('/api/slices', methods=["POST"])
def problematicSlices():
    dataCtrler = dataCtrlerChoose(request)
    query = None
    if 'query' in request.json:
        query = request.json['query']
    ret_slices = dataCtrler.getSlices(query)
    return jsonify(ret_slices)

@app.route('/api/showSlice', methods=["POST"])
def showSlice():
    dataCtrler = dataCtrlerChoose(request)
    query = None
    if 'query' in request.json:
        query = request.json['query']
    return jsonify(dataCtrler.filterSamples(query))

def main():
    global trainDataCtrler, validDataCtrler, singleValidGrid, singleTrainGrid, combinedValidGrid, combinedTrainGrid
    parser = argparse.ArgumentParser(description='manual to this script')
    parser.add_argument("--dataPath", type=str, default="")
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5010)
    parser.add_argument("--seg", action='store_true')
    parser.add_argument("--dataName", type=str, default="")
    args = parser.parse_args()

    trainDataPath = os.path.join(args.dataPath, "train_data")
    validDataPath = os.path.join(args.dataPath, "test_data")
    if not os.path.exists(trainDataPath) and not os.path.exists(validDataPath):
        raise Exception("The data path does not exist.")
    
    trainDataCtrler, validDataCtrler = DataCtrler(args.dataName), DataCtrler(args.dataName)

    if os.path.exists(trainDataPath):
        trainBufferPath = os.path.join(trainDataPath, "buffer")
        trainDataCtrler.process(trainDataPath, trainBufferPath, segmentation=args.seg)
        singleTrainGrid = GridInteraction(trainDataCtrler)

    if os.path.exists(validDataPath):
        validBufferPath = os.path.join(validDataPath, "buffer")
        validDataCtrler.process(validDataPath, validBufferPath, segmentation=args.seg)
        singleValidGrid = GridInteraction(validDataCtrler)

    # combinedValidGrid = GridInteraction(validDataCtrler, trainDataCtrler)
    # combinedTrainGrid = GridInteraction(trainDataCtrler, validDataCtrler)

    app.run(port=args.port, host=args.host, threaded=True, debug=False)

if __name__ == "__main__":
    main()