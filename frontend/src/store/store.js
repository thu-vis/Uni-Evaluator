import Vue from 'vue';
import Vuex from 'vuex';
Vue.use(Vuex);

export default new Vuex.Store({
    state: {
        APIBASE: BACKEND_BASE_URL,
        labelHierarchy: undefined,
        labelnames: [],
        dataName: '',
        matrixDataSource: 'valid', // valid or train
        gridDataSource: 'single', // single or combined
        directionLen: 9,
    },
    mutations: {
        setMetadata(state, metadata) {
            state.labelHierarchy = metadata.hierarchy;
            state.labelnames = metadata.names;
            state.dataName = metadata.dataName;
        },
        setMatrixDataSource(state, matrixDataSource) {
            state.matrixDataSource = matrixDataSource;
        },
        setGridDataSource(state, gridDataSource) {
            state.gridDataSource = gridDataSource;
        },
    },
    getters: {
        confusionMatrix: (state) => state.confusionMatrix,
        labelHierarchy: (state) => state.labelHierarchy,
        labelnames: (state) => state.labelnames,
        dataName: (state) => state.dataName,
        matrixDataSource: (state) => state.matrixDataSource,
        gridDataSource: (state) => state.gridDataSource,
        directionLen: (state) => state.directionLen,
        URL_GET_METADATA: (state) => state.APIBASE + '/api/metadata',
        URL_GET_CONFUSION_MATRIX: (state) => state.APIBASE + '/api/confusionMatrix',
        URL_HOVER_CONFUSION_MATRIX: (state) => state.APIBASE + '/api/hoverMatrixCell',
        URL_GET_ZOOM_IN_DIST: (state) => state.APIBASE + '/api/zoomInDist',
        URL_GET_IMAGE: (state) => {
            return (boxID, showmode, showAllBox, iou, conf, hidebox=false) => state.APIBASE +
            `/api/image?boxID=${boxID}&show=${showmode}&showall=${showAllBox}&iou=${iou}&conf=${conf}` +
            `&hidebox=${hidebox}&gridSource=${state.gridDataSource}&matrixSource=${state.matrixDataSource}`;
        },
        URL_GET_IMAGEBOX: (state) => state.APIBASE + '/api/imagebox',
        URL_GET_IMAGES: (state) => state.APIBASE + '/api/images',
        URL_GET_IMAGES_IN_MATRIX_CELL: (state) => state.APIBASE+'/api/imagesInCell',
        URL_GET_IMAGES_IN_SLICE: (state) => state.APIBASE+'/api/showSlice',
        URL_GET_GRID: (state) => state.APIBASE + '/api/grid',
        URL_GET_CLASS_STATISTICS: (state) => state.APIBASE + '/api/classStatistics',
        URL_GET_SLICES: (state) => state.APIBASE + '/api/slices',
    },
});
