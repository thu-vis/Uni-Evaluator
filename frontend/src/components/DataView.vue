<template>
    <div id="data-content">
        <div id="left-widgets">
            <div id="toolbox-container">
                <div class="toolbar-title">
                    <span>Settings</span>
                    <i v-if="isLoading" class="el-icon-loading"></i>
                </div>
                <div class="toolbox">
                    <div class="mode-select">
                        <span class="select-label">Dataset</span>
                        <el-select v-model="TMatrixDataSource" @change="changeMatrixDataSource" size="mini">
                            <el-option
                                label="test"
                                value="valid">
                            </el-option>
                            <el-option
                                label="train"
                                value="train">
                            </el-option>
                        </el-select>
                    </div>
                    <div class="mode-select">
                        <span class="select-label">IoU Threshold</span>
                        <el-select v-model="iouThreshold" @change="changeIouThreshold" size="mini">
                            <el-option
                                v-for="item in iouThresholds"
                                :key="item"
                                :label="item"
                                :value="item">
                            </el-option>
                        </el-select>
                    </div>
                    <div class="mode-select">
                        <span class="select-label">Matrix Normalization</span>
                        <el-select v-model="normalizationMode" size="mini">
                            <el-option
                                v-for="item in normalizationModes"
                                :key="item.value"
                                :label="item.label"
                                :value="item.value">
                            </el-option>
                        </el-select>
                    </div>
                    <div class="mode-select">
                        <span class="select-label">Statistics</span>
                        <el-select v-model="statisticsMode" @change="changeStatisticsMode" size="mini">
                            <el-option
                                v-for="item in statisticsModes"
                                :key="item.value"
                                :label="item.label"
                                :value="item.value">
                            </el-option>
                        </el-select>
                    </div>
                    <div class="mode-select">
                        <span class="select-label">Hide Unfiltered</span>
                        <el-select v-model="hideUnfiltered" size="mini">
                            <el-option
                                v-for="item in filterModes"
                                :key="item.value"
                                :label="item.label"
                                :value="item.value">
                            </el-option>
                        </el-select>
                    </div>
                </div>
            </div>

            <div id="barcharts-container">
                <div class="toolbar-title">
                    <span>Filters</span>
                </div>
                <div id="scented-barcharts">
                    <scented-barchart v-for="value in barData" :key="value.key" :barNum="barNum" :dataRangeAll="value.allRange"
                        :hideUnfiltered="hideUnfiltered" :allData="value.allData" :title="value.name" :queryKey="value.key"
                        :selectData="value.selectData" :xSplit="value.split" :displayMode="displayMode" :selectingRange="value.isLoading"
                        @hoverBarchart="fetchAllBarchartData" @selectRange="zoomInBarchart"></scented-barchart>
                </div>
            </div>
            <div id="legends-container">
                <div class="toolbar-title">Legends</div>
                <legends></legends>
            </div>
        </div>
        <div id="matrices-container">
            <div class="toolbar-title" id="grid-toolbar">
                <span>Performance</span>
            </div>
            <div id="slices-container">
                <div class="title-font"  id="grid-toolbar">
                    <span>Subsets</span>
                    <span style="font-weight: 300; margin-left: 35px;">Minimum subset size:</span>
                    <el-slider v-model="minSupport" :min="0" :max="0.5" :step="0.1"
                        style="width: 80px; margin-left: 10px;" @change="changeMinSupport"></el-slider>
                </div>
                <div class="slices">
                    <slices ref="table" :dataSlices="slices" :sliceSplits="sliceSplits" @showSlice="showSlice" :minSupport="minSupport"></slices>
                </div>
            </div>
            <div class="title-font" id="grid-toolbar">
                <span>Matrix</span>
                <div class="grid-icons">
                    <img id="matrix-normal-icon" class="grid-icon" src="/static/images/square-2.svg" @click="changeShowNormal">
                    <img id="matrix-size-comparison-icon" class="grid-icon" src="/static/images/pie-chart.svg" @click="changeShowSizeComparison">
                    <img id="matrix-direction-icon" class="grid-icon" src="/static/images/directions.svg" @click="changeShowDirection">
                    <img id="grid-home-icon" class="grid-icon" src="/static/images/home.svg" @click="resetMatrix">
                    <img id="matrix-zoomin-icon" class="grid-icon" :src="`/static/images/${matrixzoommode}.svg`" @click="matrixzoom">
                </div>
            </div>
            <div id="confusion-matrix-container">
                <confusion-matrix ref="matrix" @hoverConfusion="hoverConfusion" :matrixMode="matrixMode" @clickCell="clickConfusionCell"
                    :confusionMatrix="confusionMatrix" :classStatistics="classStatistics" :statisticsInfo="statisticsMode"
                    :normalizationMode="normalizationMode"></confusion-matrix>
            </div>
        </div>
        <div id="grid-view-container">
            <div class="toolbar-title" id="grid-toolbar">
                <span>Instances</span>
                <div class="grid-icons">
                    <img id="grid-zoomin-icon" class="grid-icon" src="/static/images/zoomin.svg" @click="initGridLayoutLasso">
                    <img id="grid-home-icon" class="grid-icon" src="/static/images/home.svg" @click="gridLayoutZoomin()">
                </div>
            </div>
            <div id="grid-layout-container">
                <grid-layout ref="grid" :iouThreshold="iouThreshold" :confThreshold="confThreshold"></grid-layout>
            </div>
        </div>
    </div>
</template>

<script>
import Vue from 'vue';
import ConfusionMatrix from './ConfusionMatrix.vue';
import ScentedBarchart from './ScentedBarchart.vue';
import GridLayout from './GridLayout.vue';
import Slices from './Slices.vue';
import Legends from './Legends.vue';
import {Select, Option, Icon, Button, Checkbox, CheckboxGroup, Slider} from 'element-ui';
import Util from './Util.vue';
import {mapGetters, mapMutations} from 'vuex';

Vue.use(Select);
Vue.use(Option);
Vue.use(Icon);
Vue.use(Button);
Vue.use(Checkbox);
Vue.use(CheckboxGroup);
Vue.use(Slider);

export default {
    components: {ConfusionMatrix, ScentedBarchart, GridLayout, Slices, Legends},
    name: 'DataView',
    mixins: [Util],
    data() {
        return {
            matrixzoommode: 'zoomin',
            TMatrixDataSource: 'valid',
            TGridDataSource: 'single',
            iouThreshold: 0.75,
            iouThresholds: [
                0.5, 0.75,
            ],
            confThreshold: 0.1,
            confThresholds: [
                0.1,
            ],
            defaultQuery: {
                conf_range: [0, 1],
                types: [1, 2, 3, 4, 9, 10, 11, 12],
            },
            query: {
                conf_range: [0, 1],
                types: [1, 2, 3, 4, 9, 10, 11, 12],
            },
            hoverInterval: undefined,
            barNum: 50,
            confusionMatrix: undefined,
            classStatistics: undefined,
            matrixMode: 'confusion', // confusion, size, direction
            normalizationMode: 'row',
            normalizationModes: [{
                value: 'total',
                label: 'none',
            }, {
                value: 'col',
                label: 'by column',
            }, {
                value: 'row',
                label: 'by row',
            }],
            statisticsMode: 'AP',
            statisticsModes: [{
                value: 'AP',
                label: 'precision',
            }, {
                value: 'AR',
                label: 'recall',
            }, {
                value: 'quantity',
                label: 'quantity',
            }],
            displayMode: 'linear',
            displayModes: [{
                value: 'linear',
                label: 'linear',
            }, {
                value: 'log',
                label: 'log',
            }],
            filterModes: [{
                value: false,
                label: 'show unfiltered',
            }, {
                value: true,
                label: 'hide unfiltered',
            }],
            // attributes for barcharts
            // data contents: key, name, allData, split, selectData, buffer, allRange, showRange, isLoading
            barData: {
                'conf_range': {
                    key: 'conf_range',
                    name: 'Prediction confidence',
                    isLoading: false,
                    allRange: [0, 1],
                    showRange: [0, 1],
                    allData: [],
                    split: [],
                    selectData: [],
                    buffer: [],
                },
                'label_size': {
                    key: 'label_size',
                    name: 'Size of ground truth',
                    isLoading: false,
                    allRange: [0, 1],
                    showRange: [0, 1],
                    allData: [],
                    split: [],
                    selectData: [],
                    buffer: [],
                },
                'predict_size': {
                    key: 'predict_size',
                    name: 'Size of predicted objects',
                    isLoading: false,
                    allRange: [0, 1],
                    showRange: [0, 1],
                    allData: [],
                    split: [],
                    selectData: [],
                    buffer: [],
                },
                'label_aspect_ratio': {
                    key: 'label_aspect_ratio',
                    name: 'Aspect ratio of ground truth',
                    isLoading: false,
                    allRange: [0, 1],
                    showRange: [0, 1],
                    allData: [],
                    split: [],
                    selectData: [],
                    buffer: [],
                },
                'predict_aspect_ratio': {
                    key: 'predict_aspect_ratio',
                    name: 'Aspect ratio of predicted objects',
                    isLoading: false,
                    allRange: [0, 1],
                    showRange: [0, 1],
                    allData: [],
                    split: [],
                    selectData: [],
                    buffer: [],
                },
            },
            // status flag
            gettingMatrix: true,
            hideUnfiltered: false,

            // buffer for grid layout
            selectLabels: undefined,
            selectPredicts: undefined,

            // slices data
            slices: [],
            sliceSplits: {},
            minSupport: 0.1,

            matrixChanged: false,
        };
    },
    computed: {
        ...mapGetters([
            'matrixDataSource',
            'gridDataSource',
            'labelnames',
        ]),
        isLoading: function() {
            let loading = false;
            for (const value of Object.values(this.barData)) {
                loading |= value.isLoading;
            }
            loading |= this.gettingMatrix;
            return loading;
        },
    },
    methods: {
        ...mapMutations([
            'setMatrixDataSource',
            'setGridDataSource',
        ]),
        changeMinSupport: function() {
            this.$refs.table.getDataAndRender();
        },
        changeMatrixDataSource: function(val) {
            console.log('changeMatrixDataSource');
            this.setMatrixDataSource(val);
            this.fetchAllBarchartData();
            this.$refs.grid.initLayout();
        },
        changeIouThreshold: function() {
            this.query['iou_thres'] = this.iouThreshold;
            that.fetchAllBarchartData();
            const that = this;
            const store = this.$store;
            this.$refs.grid.clearImageWidgets();
            if (this.selectLabels === undefined) {
                setTimeout(function() {
                    that.$refs.grid.initLayout();
                }, 1000);
                return;
            }
            this.matrixDataPost(store.getters.URL_GET_IMAGES_IN_MATRIX_CELL, {
                labels: that.selectLabels,
                preds: that.selectPredicts,
                query: that.query,
            }).then(function(response) {
                const images = response.data;
                if (images.length>0) {
                    console.log(images.length);
                    that.$refs.grid.showBottomNodes(images, false);
                } else {
                    console.log('no images');
                }
            });
        },
        changeShowDirection: function() {
            this.matrixMode = 'direction';
        },
        changeShowSizeComparison: function() {
            this.matrixMode = 'size';
        },
        changeShowNormal: function() {
            this.matrixMode = 'confusion';
        },
        resetMatrix: function() {
            if (this.matrixChanged) {
                this.matrixChanged = false;
                this.query = this.defaultQuery;
                this.setConfusionMatrix();
            }
        },
        matrixzoom: function() {
            if (Object.keys(this.$refs.matrix.pinclasses).length === 0) return;
            this.$refs.matrix.enablePin = !this.$refs.matrix.enablePin;
            this.$refs.matrix.legendExist = false;
            this.matrixzoommode = this.$refs.matrix.enablePin?'zoomout':'zoomin';
            this.$refs.matrix.getDataAndRender();
        },
        setConfusionMatrix: function(query) {
            this.gettingMatrix = true;
            this.classStatistics = undefined;
            if (query===undefined) {
                query = {};
            }
            query = {...this.query, ...query};
            query['iou_thres'] = this.iouThreshold;
            query['conf_thres'] = this.confThreshold;
            const returnList = ['count', 'size_comparison', 'direction'];
            query['return'] = returnList;
            const store = this.$store;
            const that = this;
            this.matrixDataPost(store.getters.URL_GET_CONFUSION_MATRIX, query===undefined?{}:{query: query})
                .then(function(response) {
                    that.confusionMatrix = response.data;
                    console.log(response.data);
                    that.gettingMatrix = false;
                    that.setClassStatistics();
                });
        },
        changeStatisticsMode: function() {
            this.setClassStatistics();
        },
        setThresholds: function() {
            this.query['iou_thres'] = this.iouThreshold;
            this.query['conf_thres'] = this.confThreshold;
        },
        setClassStatistics: function() {
            const store = this.$store;
            const that = this;
            this.setThresholds();
            if (this.statisticsMode === 'AP') {
                this.query['ap'] = 1;
            } else if (this.statisticsMode === 'AR') {
                this.query['ap'] = 0;
            } else {
                this.query['ap'] = 2;
            }
            this.matrixDataPost(store.getters.URL_GET_CLASS_STATISTICS, {query: this.query})
                .then(function(response) {
                    that.classStatistics = response.data;
                });
        },
        hoverConfusion: function(labelClasses, predictClasses, baridx) {
            const store = this.$store;
            const that = this;
            if (that.hoverInterval !== undefined) {
                clearTimeout(that.hoverInterval);
            }
            that.hoverInterval = setTimeout(function() {
                if (labelClasses === undefined || predictClasses === undefined || labelClasses[0] === undefined || predictClasses[0] === undefined) {
                    for (const key of Object.keys(that.barData)) {
                        that.barData[key].selectData = that.barData[key].buffer;
                    }
                    return;
                }
                if (baridx===undefined) baridx=0;
                const query = {...that.query, 'predict': predictClasses, 'label': labelClasses};
                if (baridx > 0 && baridx < 10) query['direction'] = [baridx - 1];
                else if (baridx >= 10) query['size_comparison'] = [baridx - 10];
                const targets = {};
                for (const key of Object.keys(that.barData)) {
                    targets[key] = that.barData[key].showRange;
                }
                that.matrixDataPost(store.getters.URL_HOVER_CONFUSION_MATRIX, {
                    query: query,
                    targets: targets,
                })
                    .then(function(response) {
                        for (const key of Object.keys(that.barData)) {
                            that.barData[key].selectData = response.data[key];
                        }
                    });
            }, 150);
        },
        fetchAllBarchartData: function(query) {
            // console.log(query);
            if (query === undefined) {
                query = {};
            }
            query['iou_thres'] = this.iouThreshold;
            query['conf_thres'] = this.confThreshold;
            const store = this.$store;
            this.query = {...this.query, ...query};
            this.setConfusionMatrix(this.query);

            for (const key of Object.keys(this.barData)) {
                const barData = this.barData[key];
                barData.isLoading = true;
                const postQuery = {...this.query, 'query_key': key, 'range': barData.showRange};
                this.matrixDataPost(store.getters.URL_GET_ZOOM_IN_DIST, {query: postQuery})
                    .then(function(response) {
                        barData.allData = response.data.allDist;
                        barData.selectData = response.data.selectDist;
                        barData.split = response.data.split;
                        barData.buffer = barData.selectData;
                        barData.isLoading = false;
                    });
            }
        },
        zoomInBarchart: function(queryKey, showRange) {
            const query = this.query;
            query['query_key'] = queryKey;
            query['range'] = showRange;
            query['iou_thres'] = this.iouThreshold;
            query['conf_thres'] = this.confThreshold;
            const barData = this.barData[queryKey];
            barData.showRange = showRange;
            barData.isLoading = true;
            this.matrixDataPost(this.$store.getters.URL_GET_ZOOM_IN_DIST, {query: query})
                .then(function(response) {
                    barData.allData = response.data.allDist;
                    barData.selectData = response.data.selectDist;
                    barData.split = response.data.split;
                    barData.buffer = barData.selectData;
                    barData.isLoading = false;
                });
        },
        clickConfusionCell: function(d, q) {
            const store = this.$store;
            const that = this;
            that.query['iou_thres'] = that.iouThreshold;
            that.query['conf_thres'] = that.confThreshold;
            if (q===undefined) q = {};

            // buffer for update
            that.selectLabels = d.rowNode.leafs;
            that.selectPredicts = d.colNode.leafs;

            this.matrixDataPost(store.getters.URL_GET_IMAGES_IN_MATRIX_CELL, {
                labels: d.rowNode.leafs,
                preds: d.colNode.leafs,
                query: Object.assign(q, that.query),
            }).then(function(response) {
                const images = response.data;
                if (images.length>0) {
                    console.log(images.length);
                    that.$refs.grid.showBottomNodes(images, false);
                } else {
                    console.log('no images');
                }
            });
        },
        showSlice: function(d) {
            const store = this.$store;
            const that = this;
            this.query = {...this.defaultQuery, ...d.info};
            this.setConfusionMatrix(d.info);
            console.log(this.query);
            this.matrixChanged = true;

            this.matrixDataPost(store.getters.URL_GET_IMAGES_IN_SLICE, {
                query: {
                    iou_thres: that.iouThreshold,
                    conf_thres: that.confThreshold,
                    ...that.query,
                },
            }).then(function(response) {
                const images = response.data;
                if (images.length>0) {
                    console.log(images.length);
                    that.$refs.grid.showBottomNodes(images, false);
                } else {
                    console.log('no images');
                }
            });
        },
        initGridLayoutLasso: function() {
            this.$refs.grid.initlasso();
        },
        gridLayoutZoomin: function() {
            this.selectLabels = undefined;
            this.selectPredicts = undefined;
            this.$refs.grid.zoomin();
        },
        setSlices: function() {
            const store = this.$store;
            const that = this;
            const query = this.query;
            query['iou_thres'] = this.iouThreshold;
            query['conf_thres'] = this.confThreshold;
            this.matrixDataPost(store.getters.URL_GET_SLICES, {query: query})
                .then(function(response) {
                    console.log(response.data);
                    that.slices = response.data.data;
                    that.sliceSplits = response.data.split;
                });
        },
    },
    mounted: function() {
        this.fetchAllBarchartData();
        this.setSlices();
    },
};
</script>

<style scoped>
.select-label {
    /* font-family: Comic Sans MS; */
    font-weight: normal;
    font-size: 10px;
    display: block;
    float: left;
    width: 120px;
    line-height: 28px;
}

.mode-select>.el-select {
    width: 120px;
}
.toolbox {
    border: 1px solid #c1c1c1;
    border-radius: 5px;
}

.mode-select {
    margin: 2px;
    display: flex;
    justify-content: space-around;
}

#data-content {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: row;
}

#toolbox-container {
    display: flex;
    flex-direction: column;
}

#barcharts-container {
    margin: 5px 0 0 0;
    display: flex;
    height: 35%;
    flex-direction: column;
    justify-content: flex-start;
}

#selection-container {
    margin: 5px 0 0 0;
    display: flex;
    flex-direction: column;
    flex: 100 1 auto;
    overflow: auto;
}

#legends-container {
    /* margin: 5px 0 0 0; */
    display: flex;
    flex-direction: column;
    height: 100%;
}

#slices-container {
    margin: 5px 0 5px 0;
    display: flex;
    flex-direction: column;
    height: 33.4%;
    overflow: hidden;
}

.slices {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
}

#selections {
    height: 100%;
    border: 1px solid #c1c1c1;
    border-radius: 5px;
    flex: 10 1 auto;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    align-items: center;
}

#stat {
    height: 100%;
    border: 1px solid #c1c1c1;
    border-radius: 5px;
    flex: 10 1 auto;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    align-items: center;
}

#matrices-container {
    padding: 2px;
    width: 41%;
    height: calc(100% - 4px);
    display: flex;
    flex-direction: column;
}

#confusion-matrix-container {
    /* width: 100%; */
    height: 100%;
    border: 1px solid #c1c1c1;
    border-radius: 5px;
}

#cluster-table-container {
    /* width: 100%; */
    height: 100%;
    border: 1px solid #c1c1c1;
    border-radius: 5px;
}

#grid-view-container {
    padding: 2px;
    width: 41%;
    height: calc(100% - 4px);
    display: flex;
    flex-direction: column;
}

#grid-layout-container {
    /* width: 100%; */
    height: 100%;
    border: 1px solid #c1c1c1;
    border-radius: 5px;
}


#left-widgets {
    padding: 2px;
    width: 18%;
    height: calc(100% - 4px);
    display: flex;
    flex-direction: column;
}

#scented-barcharts>svg {
    width: 100%;
    height: 20%;
}

#scented-barcharts {
    border: 1px solid #c1c1c1;
    border-radius: 5px;
    height: calc(100% - 25px);
    flex-shrink: 10;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
}


.grid-icons {
    display: flex;
    justify-content: flex-start;
    align-items: center;
    margin: 0 0 0 25px;
    flex-shrink: 1;
    /* align-self: flex-start; */
}

.title-font {
    font-size: 15px;
    /* font-family: "Roboto", "Helvetica", "Arial", sans-serif; */
    font-weight: 600;
    color: rgb(120, 120, 120);
    padding-left: 10px;
}

.grid-icon {
    width: 15px;
    height: 15px;
    margin: 0 5px 0 5px;
    cursor: pointer;
}

#grid-toolbar {
    display: flex;
    flex-direction: row;
    justify-content: flex-start;
    align-items: center;
}

#selection-add-icon {
    margin: 5px 20px 0 0;
    align-self: flex-end;
}

#color-legends {
    display: flex;
    font-weight: normal;
    font-size: 10px;
    margin: 0 0 0 80px;
    align-items: center;
}

.color-legend-rect {
    width: 10px;
    height: 10px;
    margin: 0 0 0 15px;
}

.color-legend-text {
    margin: 0 0 0 3px;
}

/deep/ .el-slider__button {
    width: 8px;
    height: 8px;
    border: 2px solid #808080;
    background-color: #FFF;
    border-radius: 50%;
    -webkit-transition: .2s;
    transition: .2s;
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
    user-select: none;
}

/deep/ .el-slider__bar {
    height: 5px;
    background-color: #d8d8d8;
    border-top-left-radius: 2.5px;
    border-bottom-left-radius: 2.5px;
    position: absolute;
}

/deep/ .el-slider__runway {
    width: 100%;
    height: 5px;
    margin: 10px 0;
    background-color: #f5f5f5;
    border-radius: 2.5px;
    position: relative;
    cursor: pointer;
    vertical-align: middle;
}
</style>
