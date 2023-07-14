/* eslint-disable vue/no-v-for-template-key-on-child */
<template>
    <div id="grid-layout" ref="grid">
        <svg id="grid-drawer" ref="gridsvg">
            <g id="grid-main-g" transform="translate(0,0)">
                <g id="grid-g"></g>
                <g id="highlight-g"></g>
                <g id="lasso-g"></g>
            </g>
        </svg>
        <waiting-icon v-if="rendering"></waiting-icon>

        <vue-draggable-resizable class="image-widget" v-for="node in showImages" :key="node.index" :lockAspectRatio="true"
            :handles="['tl','tr','bl','br']" :min-width="150" :x="widgetInitX" :y="widgetInitY" :w="gridWidthInitWidth" :h="gridWidthInitWidth"
                :onDragStart="disableHover" @dragstop="enableHover()"
                :onResizeStart="disableHover" @resizestop="onResizeEnd(node)">
                <div class="grid-widget-info">
                    <div class="grid-widget-toolbar">
                        <img class="grid-widget-icon" :id="'gird-widget-icon-'+node.index" :src="`/static/images/eye-${node.widgetmode}.png`"
                            @click="changeShowAll(node)"/>
                        <img class="grid-widget-icon" src="/static/images/close.png" @click="closeImageWidget(node)"/>
                    </div>
                    <div>ID: {{ node.index }}</div>
                    <div>Ground Truth: {{ labelnames[node.label] }}</div>
                    <div>Prediction: {{ labelnames[node.pred] }}</div>
                    <div>Confidence: {{ Math.round(node.confidence*100000)/100000 }}</div>
                    <div>Type: {{ getTypeInfo(node.type) }}</div>
                    <div class="widget-image-container">
                        <svg :id="'gird-widget-image-'+node.index" width="95%" height="95%" :ref="'image-'+node.index">
                            <image class="gird-widget-image" x="0" y="0"
                            :href="URL_GET_IMAGE(node.index, 'full', node.widgetmode, iouThreshold, confThreshold, gtColor, prColor, true)"></image>
                        </svg>
                    </div>
                </div>
        </vue-draggable-resizable>
    </div>
</template>

<script>
import {mapGetters} from 'vuex';
import * as d3 from 'd3';
window.d3 = d3;
require('../js/d3-lasso.js');
import Util from './Util.vue';
import GlobalVar from './GlovalVar.vue';
import WaitingIcon from './WaitingIcon.vue';
import {createPopper} from '@popperjs/core';
import VueDraggableResizable from 'vue-draggable-resizable';
import 'vue-draggable-resizable/dist/VueDraggableResizable.css';

export default {
    name: 'GridLayout',
    components: {WaitingIcon, VueDraggableResizable},
    mixins: [Util, GlobalVar],
    props: {
        iouThreshold: {
            type: Number,
            default: 0.5,
        },
        confThreshold: {
            type: Number,
            default: 0,
        },
    },
    computed: {
        ...mapGetters([
            'labelHierarchy',
            'labelnames',
            'URL_GET_GRID',
            'URL_GET_IMAGE',
            'URL_GET_IMAGES',
            'URL_GET_IMAGEBOX',
            'matrixDataSource',
        ]),
        svg: function() {
            return d3.select('#grid-drawer');
        },
        mainG: function() {
            return this.svg.select('#grid-main-g');
        },
        girdG: function() {
            return this.mainG.select('#grid-g');
        },
        lassoG: function() {
            return this.mainG.select('#lasso-g');
        },
        svgWidth: function() {
            return this.gridCellAttrs['size'] * this.gridInfo['width'];
        },
        svgHeight: function() {
            return this.gridCellAttrs['size'] * this.gridInfo['height'];
        },
        nodesDict: function() {
            const nodesDict = {};
            for (const node of this.nodes) {
                nodesDict[node.index] = node;
            }
            return nodesDict;
        },
        lasso: function() {
            return window.d3.lasso;
        },
        highlightG: function() {
            return this.mainG.select('#highlight-g');
        },
        widgetInitX: function() {
            return -this.gridWidthInitWidth;
        },
        widgetInitY: function() {
            return -this.$refs.grid.getBoundingClientRect().height+30;
        },
    },
    watch: {
        // all info was loaded
        labelnames: function() {
            if (!this.rendering && this.nodes.length>0 ) {
                this.rendering = true;
                this.render();
            }
        },
    },
    data: function() {
        return {
            nodes: [],
            showImageNodesMax: 1600,
            showImageNodes: [],
            depth: 0,
            gridInfo: {},
            rendering: false,

            gridCellsInG: undefined,
            lassoNodesInG: undefined,

            gridColor: 'rgb(127,127,127)',
            gtColor: 'rgb(27, 251, 254)',
            prColor: 'rgb(253, 6, 253)',

            gridCellAttrs: {
                'gClass': 'grid-cell-in-g',
                'size': 180,
                'stroke-width': 4,
                'stroke': 'gray',
                'rectOpacity': 1,
                'centerR': 3,
                'centerClass': 'lasso-node',
                'centerClassNotSelect': 'lasso-not-possible',
                'centerClassSelect': 'lasso-possible',
                'imageMargin': 4,
            },

            tooltipClass: 'cell-tooltip',
            typeInfo: [
                'Abandoned',
                'True postive',
                'Class error',
                'Location error',
                'Class & Location error',
                'Duplicate error',
                'Class & Duplicate error',
                'Location & Duplicate error',
                'Class & Location & Duplicate error',
                'Background error',
                'Missed groundtruth',
                'Class & Duplicate error',
                'Class & Location & Duplicate error',
            ],

            showImages: [],
            hoverEnable: true,
            gridWidthInitWidth: 400,
            defaultColor: 'gray',
        };
    },
    methods: {
        updateColors: function(gtColor, prColor) {
            this.gtColor = gtColor;
            this.prColor = prColor;
        },
        zoomin: function(nodes) {
            this.rendering = true;
            if (nodes===undefined) {
                // zoom home
                nodes = [];
                this.depth = 0;
            }
            if (nodes.length>0 && typeof(nodes[0])!=='number') {
                nodes = nodes.map((d) => d.index);
            }
            let findVal = false;
            for (const i of nodes) {
                if (i >= 0) {
                    findVal = true;
                    break;
                }
            }
            if (!findVal && nodes.length > 0) {
                this.rendering = false;
                return;
            }
            const that = this;
            const tsnes = nodes.map((d) => this.nodesDict[d].tsne);
            const data = nodes.length===0?{
                nodes: nodes,
                depth: this.depth,
                aspectRatio: that.getAspectRatio(),
                iou: that.iouThreshold,
                conf: that.confThreshold,
            }:{
                nodes: nodes,
                depth: this.depth,
                constraints: tsnes,
                aspectRatio: this.getAspectRatio(),
                iou: that.iouThreshold,
                conf: that.confThreshold,
            };
            this.gridDataSourcePost(this.URL_GET_GRID, data)
                .then(function(response) {
                    that.nodes = response.data.nodes;
                    that.depth = response.data.depth;
                    that.gridInfo = response.data.grid;
                    that.render();
                });
        },
        clearImageWidgets: function() {
            this.showImages = [];
        },
        showBottomNodes: function(nodes, zoomin=true) {
            this.rendering = true;
            if (nodes.length>0 && typeof(nodes[0])!=='number') {
                nodes = nodes.map((d) => d.index);
            }
            const that = this;
            this.gridDataSourcePost(this.URL_GET_GRID, {
                nodes: nodes,
                depth: 1000,
                aspectRatio: this.getAspectRatio(),
                zoomin: zoomin,
                iou: that.iouThreshold,
                conf: that.confThreshold,
            }).then(function(response) {
                that.nodes = response.data.nodes;
                that.depth = response.data.depth;
                that.gridInfo = response.data.grid;
                that.render();
            });
        },
        render: async function(changeColor = false) {
            // sort nodes and find most unconfident nodes
            this.nodes.sort(function(a, b) {
                return a.confidence-b.confidence;
            });
            for (let i=0; i<Math.min(this.showImageNodesMax, this.nodes.length); i++) {
                this.nodes[i].showImage = true;
            }

            // get images
            if (!changeColor) {
                await this.getImages();
            }

            this.gridCellsInG = this.girdG.selectAll('.'+this.gridCellAttrs['gClass']).data(this.nodes, (d)=>d.index);
            this.lassoNodesInG = this.lassoG.selectAll('.'+this.gridCellAttrs['centerClass']).data(this.nodes, (d)=>d.index);

            await this.remove();
            this.transform();
            await this.update();
            await this.create();

            this.gridCellsInG = this.girdG.selectAll('.'+this.gridCellAttrs['gClass']);
            this.lassoNodesInG = this.lassoG.selectAll('.'+this.gridCellAttrs['centerClass']);
            if (!changeColor) {
                this.rendering = false;
            }
        },
        create: async function() {
            const that = this;
            return new Promise((resolve, reject) => {
                const gridCellsInG = that.gridCellsInG.enter()
                    .append('g')
                    .attr('class', that.gridCellAttrs['gClass'])
                    .attr('opacity', 0)
                    .attr('transform', (d) => `translate(${(d.grid%that.gridInfo.width)*that.gridCellAttrs['size']},
                        ${Math.floor(d.grid/that.gridInfo.width)*that.gridCellAttrs['size']})`)
                    .on('mouseenter', function(e, d) {
                        // eslint-disable-next-line no-invalid-this
                        const node = d3.select(this).node();
                        if (that.hoverEnable) {
                            createPopper(node, that.createTooltip(d), {
                                modifiers: [
                                    {
                                        name: 'offset',
                                        options: {
                                            offset: [0, 8],
                                        },
                                    },
                                ],
                            });
                        }
                    })
                    .on('mouseleave', function() {
                        that.removeTooltip();
                    })
                    .on('click', function(e, d) {
                        that.createImageWidget(d);
                    });

                gridCellsInG.transition()
                    .duration(that.createDuration)
                    .attr('opacity', 1)
                    .on('end', resolve);

                gridCellsInG.append('rect')
                    .attr('class', 'imgcell')
                    .attr('x', 2)
                    .attr('y', 2)
                    .attr('width', that.gridCellAttrs['size']-4)
                    .attr('height', that.gridCellAttrs['size']-4)
                    .attr('stroke', (d) => that.gridColor)
                    .attr('stroke-width', (d) => that.gridCellAttrs['stroke-width'])
                    .attr('fill', 'rgb(255,255,255)')
                    .attr('opacity', 1);

                gridCellsInG.filter(function(d) {
                    return d.showImage;
                }).append('image')
                    .attr('x', that.gridCellAttrs['imageMargin'])
                    .attr('y', that.gridCellAttrs['imageMargin'])
                    .attr('width', that.gridCellAttrs['size']-2*that.gridCellAttrs['imageMargin'])
                    .attr('height', that.gridCellAttrs['size']-2*that.gridCellAttrs['imageMargin'])
                    // eslint-disable-next-line new-cap
                    .attr('xlink:href', (node) => node.img);

                that.lassoNodesInG.enter().append('circle')
                    .attr('class', that.gridCellAttrs['centerClass'])
                    .attr('r', that.gridCellAttrs['centerR'])
                    .attr('cx', (d)=>that.gridCellAttrs['size']/2+(d.grid%that.gridInfo.width)*that.gridCellAttrs['size'])
                    .attr('cy', (d)=>that.gridCellAttrs['size']/2+Math.floor(d.grid/that.gridInfo.width)*that.gridCellAttrs['size']);


                if ((that.gridCellsInG.enter().size() === 0) && (that.lassoNodesInG.enter().size() === 0)) {
                    resolve();
                }
            });
        },
        update: async function() {
            const that = this;
            return new Promise((resolve, reject) => {
                that.gridCellsInG.transition()
                    .duration(that.updateDuration)
                    .attr('transform', (d) => `translate(${(d.grid%that.gridInfo.width)*that.gridCellAttrs['size']},
                        ${Math.floor(d.grid/that.gridInfo.width)*that.gridCellAttrs['size']})`)
                    .on('end', resolve);

                that.gridCellsInG.selectAll('rect.imgcell')
                    .transition()
                    .duration(that.updateDuration)
                    .attr('fill', 'rgb(255,255,255)')
                    .attr('stroke', (d) => that.gridColor)
                    .attr('stroke-width', (d) => that.gridCellAttrs['stroke-width'])
                    .attr('opacity', 1)
                    .on('end', resolve);

                that.lassoNodesInG
                    .attr('cx', (d)=>that.gridCellAttrs['size']/2+(d.grid%that.gridInfo.width)*that.gridCellAttrs['size'])
                    .attr('cy', (d)=>that.gridCellAttrs['size']/2+Math.floor(d.grid/that.gridInfo.width)*that.gridCellAttrs['size']);

                if ((that.gridCellsInG.size() === 0) && (that.lassoNodesInG.size() === 0)) {
                    resolve();
                }
            });
        },
        remove: async function() {
            const that = this;
            return new Promise((resolve, reject) => {
                that.gridCellsInG.exit()
                    .transition()
                    .duration(that.removeDuration)
                    .attr('opacity', 0)
                    .remove()
                    .on('end', resolve);

                that.lassoNodesInG.exit()
                    .transition()
                    .duration(that.removeDuration)
                    .attr('opacity', 0)
                    .remove()
                    .on('end', resolve);

                if ((that.gridCellsInG.exit().size() === 0) && (that.lassoNodesInG.exit().size() === 0)) {
                    resolve();
                }
            });
        },
        transform: async function() {
            const that = this;
            return new Promise((resolve, reject) => {
                // compute transform
                const svgRealWidth = that.$refs.gridsvg.clientWidth;
                const svgRealHeight = that.$refs.gridsvg.clientHeight;
                let shiftx = 0;
                let shifty = 0;
                const scale = Math.min(1, svgRealWidth/that.svgWidth, svgRealHeight/that.svgHeight);
                shiftx = (svgRealWidth-scale*that.svgWidth)/2;
                shifty = (svgRealHeight-scale*that.svgHeight)/2;
                that.mainG.transition()
                    .duration(that.transformDuration)
                    .attr('transform', `translate(${shiftx} ${shifty}) scale(${scale})`)
                    .on('end', resolve);
            });
        },
        getImages: async function() {
            const that = this;
            return new Promise((resolve, reject) => {
                that.gridDataSourcePost(that.URL_GET_IMAGES, {
                    boxIDs: that.nodes.map((d) => d.index),
                    show: that.nodes.length<15?'full':'box',
                    iou: that.iouThreshold,
                    conf: that.confThreshold,
                    gtColor: that.gtColor,
                    prColor: that.prColor,
                }).then((response) => {
                    for (let i=0; i<that.nodes.length; i++) {
                        that.nodes[i].img = `data:image/jpeg;base64,${response.data[i]}`;
                    }
                    resolve();
                });
            });
        },
        initlasso: function() {
            // Lasso functions
            const that = this;
            const lassoStart = function() {
                lasso.items()
                    .classed('lasso-not-possible', true)
                    .classed('lasso-possible', false);
            };

            const lassoDraw = function() {
                // Style the possible dots
                lasso.possibleItems()
                    .classed('lasso-not-possible', false)
                    .classed('lasso-possible', true);

                // Style the not possible dot
                lasso.notPossibleItems()
                    .classed('lasso-not-possible', true)
                    .classed('lasso-possible', false);
            };

            const lassoEnd = function() {
            // Reset the color of all dots
                lasso.items()
                    .classed('lasso-not-possible', false)
                    .classed('lasso-possible', false);
                const selectednodes = lasso.selectedItems().data();
                if (selectednodes.length>0) {
                    that.zoomin(selectednodes);
                }
                that.stoplasso();
            };

            const lasso = window.d3.lasso()
                .closePathSelect(true)
                .closePathDistance(100)
                .items(this.lassoNodesInG)
                .targetArea(this.svg)
                .on('start', lassoStart)
                .on('draw', lassoDraw)
                .on('end', lassoEnd);

            this.svg.call(lasso);
        },
        stoplasso: function() {
            this.svg.select('.lasso').remove();
            this.svg.on('.drag', null);
        },
        highlightCells: function(cells) {
            const cellDict = {};
            const that = this;
            for (const cell of cells) cellDict[cell] = true;
            this.gridCellsInG.filter((d) => cellDict[d.index]!==undefined)
                .each(function(d) {
                    that.highlightG.append('rect')
                        .attr('x', (d.grid%that.gridInfo.width)*that.gridCellAttrs['size'])
                        .attr('y', Math.floor(d.grid/that.gridInfo.width)*that.gridCellAttrs['size'])
                        .attr('width', that.gridCellAttrs['size'])
                        .attr('height', that.gridCellAttrs['size'])
                        .attr('stroke', that.gridCellAttrs['stroke'])
                        .attr('stroke-width', 4)
                        .attr('fill', 'none');
                });
        },
        unhighlightCells: function(cells) {
            this.highlightG
                .selectAll('rect')
                .remove();
        },
        createTooltip: function(node) {
            const that = this;
            const getImageGradientURL = this.URL_GET_IMAGE;
            const tooltip = d3.select('#grid-layout').append('div').attr('class', that.tooltipClass).style('display', 'none');
            tooltip.style('display', 'flex');
            tooltip.html(`<div class="grid-tooltip-info">ID: ${node.index}</div>
                        <div>Ground Truth: ${that.labelnames[node.label]}</div>
                        <div>Prediction: ${that.labelnames[node.pred]}</div>
                        <div>Confidence: ${Math.round(node.confidence*100000)/100000}</div>
                        <div>Type: ${that.getTypeInfo(node.type)}</div>
                    <img class="gird-tooltip-image" src="${getImageGradientURL(node.index, 'full', 'single',
        that.iouThreshold, that.confThreshold, that.gtColor, that.prColor)}"/>
                    <div id="grid-tooltip-arrow" data-popper-arrow></div>`);
            return tooltip.node();
        },
        removeTooltip: function() {
            d3.selectAll('.'+this.tooltipClass).remove();
        },
        createImageWidget: function(node) {
            // eslint-disable-next-line new-cap
            node.widgetmode = 'single';
            if (this.showImages.indexOf(node) > -1) {
                return;
            }
            this.showImages.push(node);
            this.$nextTick(()=> {
                this.fetchAndDrawWidgetBox(node);
            });
        },
        getAspectRatio: function() {
            const svgRealWidth = this.$refs.gridsvg.clientWidth;
            const svgRealHeight = this.$refs.gridsvg.clientHeight;
            return svgRealHeight/svgRealWidth;
        },
        closeImageWidget: function(node) {
            this.hoverEnable = true;
            const index = this.showImages.indexOf(node);
            if (index>-1) {
                this.showImages.splice(index, 1);
            }
        },
        disableHover: function() {
            this.hoverEnable = false;
        },
        enableHover: function() {
            this.hoverEnable = true;
        },
        changeShowAll: function(node) {
            if (node.widgetmode === 'single') {
                node.widgetmode = 'all';
            } else if (node.widgetmode === 'all') {
                node.widgetmode = 'single';
            }
            d3.select('#gird-widget-icon-'+node.index).attr('src', `/static/images/eye-${node.widgetmode}.png`);
            this.fetchAndDrawWidgetBox(node);
        },
        onResizeEnd: function(node) {
            this.enableHover();
            this.fetchAndDrawWidgetBox(node);
        },
        drawWidgetBox: function(node) {
            const svg = d3.select('#gird-widget-image-'+node.index);
            const that = this;
            let boxes = node.boxes;
            const imagesize =node.imagesize;
            const svgsize = that.$refs['image-'+node.index][0].getBoundingClientRect();
            const scale = Math.min(svgsize.width/imagesize[0], svgsize.height/imagesize[1]);
            const realwidth = scale*imagesize[0];
            const realHeight = scale*imagesize[1];
            const xshift = (svgsize.width-realwidth)/2;
            const yshift = (svgsize.height-realHeight)/2;
            const MAP_HEIGHT = 2500;
            const MAP_WIDTH = MAP_HEIGHT * Math.sqrt(2);

            const MAX_TRANSLATE_X = MAP_WIDTH / 2;
            const MIN_TRANSLATE_X = -MAX_TRANSLATE_X;

            const MAX_TRANSLATE_Y = MAP_HEIGHT / 2;
            const MIN_TRANSLATE_Y = -MAX_TRANSLATE_Y;

            const MIN_RECT_WIDTH = 10;
            const MIN_RECT_HEIGHT = 10;

            const HANDLE_R = 2;
            const HANDLE_R_ACTIVE = 5;
            boxes = boxes.map(function(d, i) {
                return {
                    id: d.id,
                    x: (d.box[0]-d.box[2]/2)*realwidth+xshift,
                    y: (d.box[1]-d.box[3]/2)*realHeight+yshift,
                    width: d.box[2]*realwidth,
                    height: d.box[3]*realHeight,
                    ispred: d.type==='pred',
                    class: d.class,
                    score: d.score,
                };
            });
            svg.selectAll('g.imagebox').remove();
            let rects = svg.selectAll('g.imagebox').data(boxes);
            const image = svg.select('image');
            image.style('width', svgsize.width);
            image.style('height', svgsize.height);

            const resizerHover = function(e, d) {
                // eslint-disable-next-line no-invalid-this
                const el = d3.select(this); const isEntering = e.type === 'mouseenter';
                el
                    .classed('hovering', isEntering)
                    .attr(
                        'r',
                        isEntering || el.classed('resizing') ?
                            HANDLE_R_ACTIVE : HANDLE_R,
                    );
            };

            const rectHover = function(e, d) {
                // eslint-disable-next-line no-invalid-this
                const el = d3.select(this);
                const isEntering = e.type === 'mouseenter';
                el
                    .classed('hovering', isEntering)
                    .attr(
                        'stroke-width',
                        isEntering || el.classed('resizing') ?
                            5 : 2,
                    );
            };

            const rectResizeStartEnd = function(e) {
                // eslint-disable-next-line no-invalid-this
                const el = d3.select(this);
                const isStarting = e.type === 'start';
                // eslint-disable-next-line no-invalid-this
                d3.select(this)
                    .classed('resizing', isStarting)
                    .attr(
                        'r',
                        isStarting || el.classed('hovering') ?
                            HANDLE_R_ACTIVE : HANDLE_R,
                    );
            };

            const rectResizing = function(e, d) {
                const dragX = Math.max(
                    Math.min(e.x, MAX_TRANSLATE_X),
                    MIN_TRANSLATE_X,
                );

                const dragY = Math.max(
                    Math.min(e.y, MAX_TRANSLATE_Y),
                    MIN_TRANSLATE_Y,
                );

                // eslint-disable-next-line no-invalid-this
                if (d3.select(this).classed('topleft')) {
                    const newWidth = Math.max(d.width + d.x - dragX, MIN_RECT_WIDTH);

                    d.x += d.width - newWidth;
                    d.width = newWidth;

                    const newHeight = Math.max(d.height + d.y - dragY, MIN_RECT_HEIGHT);

                    d.y += d.height - newHeight;
                    d.height = newHeight;
                } else {
                    d.width = Math.max(dragX - d.x, MIN_RECT_WIDTH);
                    d.height = Math.max(dragY - d.y, MIN_RECT_HEIGHT);
                }

                update();
            };

            const rectMoveStartEnd = function(e, d) {
                // eslint-disable-next-line no-invalid-this
                d3.select(this).classed('moving', e.type === 'start');
            };

            const rectMoving = function(e, d) {
                const dragX = Math.max(
                    Math.min(e.x, MAX_TRANSLATE_X - d.width),
                    MIN_TRANSLATE_X,
                );

                const dragY = Math.max(
                    Math.min(e.y, MAX_TRANSLATE_Y - d.height),
                    MIN_TRANSLATE_Y,
                );

                d.x = dragX;
                d.y = dragY;

                update();
            };

            const update = function() {
                rects = svg.selectAll('g.imagebox').data(boxes, (d) => d.id);
                rects.exit().remove();

                const newRects = rects.enter()
                    .append('g')
                    .classed('imagebox', true);

                newRects
                    .append('rect')
                    .classed('bg', true)
                    .attr('fill', 'none')
                    .attr('stroke', (d) => d.ispred?that.prColor:that.gtColor)
                    .attr('stroke-width', 2)
                    .on('mouseenter mouseleave', rectHover)
                    .call(d3.drag()
                        .container(svg.node())
                        .on('start end', rectMoveStartEnd)
                        .on('drag', rectMoving),
                    )
                    .append('title')
                    .text((d)=>d.class===undefined?'':d.class+d.id+'\n'+d.score.toFixed(3));

                newRects
                    .append('g')
                    .classed('circles', true)
                    .each(function(d) {
                        // eslint-disable-next-line no-invalid-this
                        const circleG = d3.select(this);

                        circleG
                            .append('circle')
                            .classed('topleft', true)
                            .attr('r', HANDLE_R)
                            .on('mouseenter mouseleave', resizerHover)
                            .call(d3.drag()
                                .container(svg.node())
                                .subject(function(e) {
                                    return {x: e.x, y: e.y};
                                })
                                .on('start end', rectResizeStartEnd)
                                .on('drag', rectResizing),
                            );

                        circleG
                            .append('circle')
                            .classed('bottomright', true)
                            .attr('r', HANDLE_R)
                            .on('mouseenter mouseleave', resizerHover)
                            .call(d3.drag()
                                .container(svg.node())
                                .subject(function(e) {
                                    return {x: e.x, y: e.y};
                                })
                                .on('start end', rectResizeStartEnd)
                                .on('drag', rectResizing),
                            );
                    });

                const allRects = newRects.merge(rects);

                allRects
                    .attr('transform', function(d) {
                        return 'translate(' + d.x + ',' + d.y + ')';
                    });

                allRects
                    .select('rect.bg')
                    .attr('height', function(d) {
                        return d.height;
                    })
                    .attr('width', function(d) {
                        return d.width;
                    });

                allRects
                    .select('circle.bottomright')
                    .attr('cx', function(d) {
                        return d.width;
                    })
                    .attr('cy', function(d) {
                        return d.height;
                    });
            };
            update();
        },
        drawWidgetPolygon: function(node) {
            const svg = d3.select('#gird-widget-image-'+node.index);
            const that = this;
            let boxes = node.boxes;
            const imagesize =node.imagesize;
            const svgsize = that.$refs['image-'+node.index][0].getBoundingClientRect();
            const scale = Math.min(svgsize.width/imagesize[0], svgsize.height/imagesize[1]);
            const realwidth = scale*imagesize[0];
            const realHeight = scale*imagesize[1];
            const xshift = (svgsize.width-realwidth)/2;
            const yshift = (svgsize.height-realHeight)/2;

            boxes = boxes.map(function(d, i) {
                const polys = [];
                for (const poly of d.poly) {
                    polys.push(poly.map((d)=>[
                        d[0]*scale+xshift,
                        d[1]*scale+yshift,
                    ]));
                }
                return {
                    id: d.id,
                    polys: polys,
                    ispred: d.type==='pred',
                    class: d.class,
                    score: d.score,
                };
            });
            svg.selectAll('path.imagebox').remove();
            let polysg = svg.selectAll('path.imagebox').data(boxes);
            const image = svg.select('image');
            image.style('width', svgsize.width);
            image.style('height', svgsize.height);

            const drawPath = function(context, polys) {
                for (const poly of polys) {
                    context.moveTo(poly[0][0], poly[0][1]);
                    for (const node of poly) {
                        context.lineTo(node[0], node[1]);
                    }
                    context.lineTo(poly[0][0], poly[0][1]);
                }
            };

            const update = function() {
                polysg = svg.selectAll('path.imagebox').data(boxes, (d) => d.id);
                polysg.exit().remove();

                polysg.enter()
                    .append('path')
                    .classed('imagebox', true)
                    .attr('fill', 'none')
                    .attr('stroke', (d) => d.ispred?that.prColor:that.gtColor)
                    .attr('stroke-width', 2)
                    .on('mouseover', function() {
                        // eslint-disable-next-line no-invalid-this
                        const ele = d3.select(this);
                        ele.attr('stroke-width', 4);
                    })
                    .on('mouseout', function(e, d) {
                        // eslint-disable-next-line no-invalid-this
                        const ele = d3.select(this);
                        ele.attr('stroke-width', 2);
                    })
                    .attr('d', function(d) {
                        const context = d3.path();
                        drawPath(context, d.polys);
                        return context.toString();
                    })
                    .append('title')
                    .text((d)=>d.class===undefined?'':d.class+d.id+'\n'+d.score.toFixed(3));
            };
            update();
        },
        fetchAndDrawWidgetBox: function(node) {
            const that = this;

            that.gridDataSourcePost(that.URL_GET_IMAGEBOX, {
                boxID: node.index,
                showall: node.widgetmode,
                iou: that.iouThreshold,
                conf: that.confThreshold,
            }).then(function(response) {
                const boxes = response.data.boxes;
                node.boxes = boxes;
                node.imagesize = response.data.image;
                if (response.data.seg) {
                    that.drawWidgetPolygon(node);
                } else {
                    that.drawWidgetBox(node);
                }
            });
        },
        initLayout: function() {
            const that = this;
            this.rendering = true;
            this.gridDataSourcePost(that.URL_GET_GRID, {
                nodes: [],
                depth: 0,
                aspectRatio: this.getAspectRatio(),
                iou: that.iouThreshold,
                conf: that.confThreshold,
            }).then(function(response) {
                that.nodes = response.data.nodes;
                that.depth = response.data.depth;
                that.gridInfo = response.data.grid;
                if (that.labelnames.length>0) {
                    that.render();
                } else {
                    that.rendering = false;
                }
            });
        },
        getTypeInfo: function(idx) {
            if (idx < this.typeInfo.length) {
                return this.typeInfo[idx];
            }
            if (this.matrixDataSource === 'train') return 'Validation data';
            return 'Training data';
        },
    },
    mounted: function() {
        this.initLayout();
    },
};
</script>

<style>
#grid-layout {
    width: -moz-calc(100% - 20px);
    width: -webkit-calc(100% - 20px);
    width: -o-calc(100% - 20px);
    width: calc(100% - 20px);
    height: -moz-calc(100% - 20px);
    height: -webkit-calc(100% - 20px);
    height: -o-calc(100% - 20px);
    height: calc(100% - 20px);
    margin: 10px 10px 10px 10px;
    position: relative;
}

#grid-drawer {
    width: 100%;
    height: 100%;
    flex-shrink: 100;
}

.lasso-not-possible, .lasso-node {
    fill: none
}

.lasso-possible {
    fill: rgb(200,200,200);
}

.lasso path {
    stroke: rgb(80,80,80);
    stroke-width:2px;
}

.lasso .drawn {
    fill-opacity:.05 ;
}

.lasso .loop_close {
    fill:none;
    stroke-dasharray: 4,4;
}

.lasso .origin {
    fill:#3399FF;
    fill-opacity:.5;
}

.cell-tooltip {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: #ffffff;
  color: gray;
  font-weight: bold;
  padding: 5px 10px;
  font-size: 13px;
  border-radius: 4px;
}

.gird-tooltip-image {
    width: 100px;
    margin: 10px 0 0 0;
}

#grid-tooltip-arrow,
#grid-tooltip-arrow::before {
  position: absolute;
  width: 8px;
  height: 8px;
  background: inherit;
}

#grid-tooltip-arrow {
  visibility: hidden;
}

#grid-tooltip-arrow::before {
  visibility: visible;
  content: '';
  transform: rotate(45deg);
}

.cell-tooltip[data-popper-placement^='top'] > #grid-tooltip-arrow {
  bottom: -4px;
}

.cell-tooltip[data-popper-placement^='bottom'] > #grid-tooltip-arrow {
  top: -4px;
}

.cell-tooltip[data-popper-placement^='left'] > #grid-tooltip-arrow {
  right: -4px;
}

.cell-tooltip[data-popper-placement^='right'] > #grid-tooltip-arrow {
  left: -4px;
}

.grid-widget-info {
    display: flex;
    flex-direction: column;
    align-items: center;
    color: gray;
    font-weight: bold;
    font-size: 13px;
    background: #ffffff;
    width: 100%;
    height: 100%;
    border-radius: 10px;
}

.widget-image-container {
    width: 100%;
    height: 100%;
    min-height: 10px;
    margin: 5px 5px 5px 5px;
    display: flex;
    justify-content: center;
}

.gird-widget-image {
    width: 100%;
    height: 100%;
    object-fit: contain;
}

.image-widget {
    position: absolute;
    border-radius: 10px;
    border: 1px solid grey;
    box-shadow: grey 5px 5px 8px;
}

.grid-widget-toolbar {
    display: flex;
    flex-direction: row;
    justify-content: flex-end;
    align-items: center;
    height: 20px;
    width: 100%;
}

.grid-widget-icon {
    cursor: pointer;
    width: 15px;
    height: 15px;
    margin: 0 3px 0 3px;
}
</style>
