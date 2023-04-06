<template>
    <svg :id="widgetId" width="100%" height="100%" ref="svg"></svg>
</template>

<script>
import * as d3 from 'd3';
window.d3 = d3;
import Util from './Util.vue';
import GlobalVar from './GlovalVar.vue';
import {brushX} from 'd3-brush';
import debounce from 'lodash/debounce';

export default {
    name: 'ScentedBarchart',
    mixins: [Util, GlobalVar],
    props: {
        allData: {
            type: Array,
            default: undefined,
        },
        title: {
            type: String,
            default: '',
        },
        selectData: {
            type: Array,
            default: undefined,
        },
        queryKey: {
            type: String,
            default: '',
        },
        xSplit: {
            type: Array,
            default: undefined,
        },
        displayMode: {
            type: String,
            default: 'log',
        },
        barNum: {
            type: Number,
            default: 10,
        },
        dataRangeAll: {
            type: Array,
            default: undefined,
        },
        hideUnfiltered: {
            type: Boolean,
            default: false,
        },
        selectingRange: {
            type: Boolean,
            default: false,
        },
    },
    computed: {
        widgetId: function() {
            return 'scented-barchart-svg-'+this.queryKey;
        },
        mainSvg: function() {
            return d3.select('#'+this.widgetId);
        },
        alldataG: function() {
            return this.mainSvg.select('#all-data-g');
        },
        selectDataG: function() {
            return this.mainSvg.select('#select-data-g');
        },
        pos2DataRangeShow: function() {
            return this.globalAttrs.xType([this.xScale(0), this.xScale(1)], this.dataRangeShow);
        },
        dataRangeShow2Pos: function() {
            return this.globalAttrs.xType(this.dataRangeShow, [this.xScale(0), this.xScale(1)]);
        },
        dataRangeAll2Pos: function() {
            return this.globalAttrs.xType(this.dataRangeAll, [this.xScale(0), this.xScale(1)]);
        },
    },
    mounted: function() {

    },
    watch: {
        allData: function() {
            this.render();
        },
        selectData: function() {
            this.render();
        },
        displayMode: function() {
            this.render();
        },
        hideUnfiltered: function() {
            this.render();
        },
        selectingRange: function() {
        },
    },
    data: function() {
        return {
            globalAttrs: {
                'marginTop': 20, // top margin, in pixels
                'marginRight': 0, // right margin, in pixels
                'marginBottom': 22, // bottom margin, in pixels
                'guideLineMarginBottom': 14, // bottom margin, in pixels
                'marginLeft': 0, // left margin, in pixels
                'insetLeft': 1, // inset left edge of bar
                'insetRight': 1, // inset right edge of bar:
                'xType': d3.scaleLinear, // type of x-scale
                'yType': d3.scaleLinear, // type of y-scale
                // 'unselectFill': 'rgb(227,227,227)',
                'unselectFill': 'rgb(245,245,245)',
                // 'selectFill': 'rgb(167,167,167)',
                'selectFill': 'rgb(216,216,216)',
            },
            textAttrs: {
                // 'font-family': 'Comic Sans MS',
                'font-weight': 'normal',
                'font-size': 12,
                'font-size-small': 10,
            },
            selectDataRectG: null,
            allDataRectG: null,
            drawAxis: false,
            xScale: undefined,
            yScale: undefined,
            brush: brushX(),
            lastSelection: null,
            dataRangeShow: undefined, // range to show data in bins
            zoominterval: undefined,
            zoom: null,
            selectRangeLeft: -1,
            selectRangeRight: -1,
            selected: false,
            zoomed: false,
            textDigits: 4,
        };
    },
    methods: {
        resetSelect: function() {
            const that = this;
            const triangleY = this.globalAttrs.height-this.globalAttrs.marginBottom+6;
            that.mainSvg.selectAll('#remove-brush-button').remove();
            that.mainSvg.select('text.rangeText').text('');
            that.selectRangeLeft = that.dataRangeShow[0];
            that.selectRangeRight = that.dataRangeShow[1];
            that.mainSvg.select('#triangle-left')
                .attr('transform', `translate(${that.xScale(0)} ${triangleY})`);
            that.mainSvg.select('#triangle-right')
                .attr('transform', `translate(${that.xScale(1)} ${triangleY})`);
            that.mainSvg.select('#emp-line')
                .attr('opacity', 0);
            if (this.selected) {
                const query = {};
                query[that.queryKey] = that.dataRangeAll;
                that.$emit('hoverBarchart', query);
            }
            this.selected = false;
        },
        createResetBrush: function() {
            if (this.mainSvg.select('#remove-brush-button').size() > 0) return;
            const that = this;
            this.mainSvg
                .append('text')
                .attr('id', 'remove-brush-button')
                .attr('x', this.globalAttrs['width'] - this.globalAttrs['marginRight'])
                .attr('y', that.globalAttrs['marginTop']-5)
                .attr('fill', 'currentColor')
                .attr('text-anchor', 'end')
                .attr('cursor', 'pointer')
                .attr('font-family', that.textAttrs['font-family'])
                .attr('font-weight', that.textAttrs['font-weight'])
                .attr('font-size', that.textAttrs['font-size'])
                .text('reset select')
                .on('click', ()=> {
                    that.resetSelect();
                });
        },
        render: async function() {
            const xRange = [this.globalAttrs['marginLeft'], this.globalAttrs['width'] - this.globalAttrs['marginRight']]; // [left, right]
            // add minimum height 1 for non-zero value
            const yRange = [this.globalAttrs['height'] - this.globalAttrs['marginBottom']-1, this.globalAttrs['marginTop']]; // [bottom, top]
            const xDomain = [-0.05, 1.05];
            let yDomain;
            if (this.hideUnfiltered) yDomain = [0, this.cal(d3.max(this.selectData)+1)+0.01];
            else yDomain = [0, this.cal(d3.max(this.allData))];
            this.xScale = this.globalAttrs['xType'](xDomain, xRange);
            this.yScale = this.globalAttrs['yType'](yDomain, yRange);
            const that = this;
            if (this.drawAxis === false) {
                this.drawAxis = true;
                this.dataRangeShow = [Number(this.dataRangeAll[0]), Number(this.dataRangeAll[1])];
                that.mainSvg
                    .append('text')
                    .attr('class', 'rangeText')
                    .attr('x', that.globalAttrs['width']/2)
                    .attr('y', that.globalAttrs['marginTop']-5)
                    .attr('fill', 'rgb(159,159,159)')
                    .attr('font-family', that.textAttrs['font-family'])
                    .attr('font-weight', that.textAttrs['font-weight'])
                    .attr('font-size', that.textAttrs['font-size'])
                    .style('pointer-events', 'none')
                    .style('-webkit-user-select', 'none')
                    .style('-moz-user-select', 'none')
                    .style('-ms-user-select', 'none')
                    .style('user-select', 'none')
                    .style('cursor', 'default')
                    .text('');
                this.selectRangeLeft = this.dataRangeShow[0];
                this.selectRangeRight = this.dataRangeShow[1];

                // horizontal line
                this.mainSvg
                    .append('line')
                    .attr('transform', `translate(0,${this.getYVal(0)})`)
                    .attr('stroke-opacity', 0.2)
                    .attr('stroke', 'currentColor')
                    .attr('x1', this.globalAttrs['marginLeft'])
                    .attr('x2', this.globalAttrs['width'] - this.globalAttrs['marginLeft'] - this.globalAttrs['marginRight']);
                const width1 = this.getTextWidth(`${this.dataRangeShow[0].toFixed(this.textDigits)}`,
                    `${this.textAttrs['font-weight']} ${this.textAttrs['font-size-small']}px ${this.textAttrs['font-family']}`);
                const width2 = this.getTextWidth(`${this.dataRangeShow[1].toFixed(this.textDigits)}`,
                    `${this.textAttrs['font-weight']} ${this.textAttrs['font-size-small']}px ${this.textAttrs['font-family']}`);
                this.mainSvg
                    .append('text')
                    .attr('class', 'info-text')
                    .attr('id', 'show-text-left')
                    .attr('x', Math.max(this.xScale(0)-width1, 2))
                    .attr('y', this.globalAttrs.height-this.globalAttrs.guideLineMarginBottom+
                        that.textAttrs['font-size-small'])
                    .attr('fill', 'rgb(159,159,159)')
                    .attr('font-family', that.textAttrs['font-family'])
                    .attr('font-weight', that.textAttrs['font-weight'])
                    .attr('font-size', that.textAttrs['font-size-small'])
                    .style('pointer-events', 'none')
                    .style('-webkit-user-select', 'none')
                    .style('-moz-user-select', 'none')
                    .style('-ms-user-select', 'none')
                    .style('user-select', 'none')
                    .style('cursor', 'default')
                    .text(`${this.dataRangeShow[0].toFixed(this.textDigits)}`);
                this.mainSvg
                    .append('text')
                    .attr('class', 'info-text')
                    .attr('id', 'show-text-right')
                    .attr('x', Math.min(this.xScale(1), this.globalAttrs.width-width2-2))
                    .attr('y', this.globalAttrs.height-this.globalAttrs.guideLineMarginBottom+
                        that.textAttrs['font-size-small'])
                    .attr('fill', 'rgb(159,159,159)')
                    .attr('font-family', that.textAttrs['font-family'])
                    .attr('font-weight', that.textAttrs['font-weight'])
                    .attr('font-size', that.textAttrs['font-size-small'])
                    .style('pointer-events', 'none')
                    .style('-webkit-user-select', 'none')
                    .style('-moz-user-select', 'none')
                    .style('-ms-user-select', 'none')
                    .style('user-select', 'none')
                    .style('cursor', 'default')
                    .text(`${this.dataRangeShow[1].toFixed(this.textDigits)}`);
                this.mainSvg
                    .append('g')
                    .attr('id', 'all-data-g');

                this.mainSvg
                    .append('g')
                    .attr('id', 'select-data-g');

                const triangle = d3.symbol().size(30).type(d3.symbolTriangle);
                const triangleY = this.globalAttrs.height-this.globalAttrs.marginBottom+6;
                const drag = function() {
                    const dragged = function(e, d) {
                        // eslint-disable-next-line no-invalid-this
                        const tmp = d3.select(this);
                        // eslint-disable-next-line no-invalid-this
                        if (this.id === 'triangle-left') {
                            that.selectRangeLeft = Math.min(that.selectRangeRight,
                                Math.max(that.pos2DataRangeShow(that.xScale(0)), that.pos2DataRangeShow(e.x)));
                            tmp.attr('transform', `translate(${that.dataRangeShow2Pos(that.selectRangeLeft)} ${triangleY})`);
                        } else {
                            that.selectRangeRight = Math.min(that.pos2DataRangeShow(that.xScale(1)),
                                Math.max(that.selectRangeLeft, that.pos2DataRangeShow(e.x)));
                            tmp.attr('transform', `translate(${that.dataRangeShow2Pos(that.selectRangeRight)} ${triangleY})`);
                        }
                        that.mainSvg.select('text.rangeText')
                            .text(`[${that.selectRangeLeft.toFixed(that.textDigits)}, ${that.selectRangeRight.toFixed(that.textDigits)}]`);
                        that.mainSvg.select('#emp-line')
                            .attr('opacity', 1)
                            .attr('x1', that.dataRangeShow2Pos(that.selectRangeLeft))
                            .attr('x2', that.dataRangeShow2Pos(that.selectRangeRight));
                    };
                    const dragended = function(e, d) {
                        that.selected = true;
                        that.createResetBrush();
                        const query = {};
                        query[that.queryKey] = [that.selectRangeLeft, that.selectRangeRight];
                        that.$emit('hoverBarchart', query);
                    };
                    return d3.drag().on('drag', dragged).on('end', dragended);
                };
                this.mainSvg
                    .append('path')
                    .attr('id', 'triangle-left')
                    .attr('d', triangle)
                    .attr('transform', `translate(${this.xScale(0)} ${triangleY})`)
                    .attr('fill', 'rgb(127,127,127)')
                    .call(drag());
                this.mainSvg
                    .append('path')
                    .attr('id', 'triangle-right')
                    .attr('d', triangle)
                    .attr('transform', `translate(${this.xScale(1)} ${triangleY})`)
                    .attr('fill', 'rgb(127,127,127)')
                    .call(drag());

                const customZoomEnd = function(type) {
                    that.allDataRectG
                        .selectAll('rect')
                        .transition()
                        .duration(that.transformDuration)
                        .attr('opacity', 0);
                    that.selectDataRectG
                        .selectAll('rect')
                        .transition()
                        .duration(that.transformDuration)
                        .attr('opacity', 0);
                    that.zoomed = true;
                    that.$emit('selectRange', that.queryKey, that.dataRangeShow);
                    that.resetSelect();
                };
                const customDelta = function(event) {
                    return -event.deltaY * (event.deltaMode === 1 ? 0.01 : event.deltaMode ? 1 : 0.001);
                };
                const debouncedZoomEnd = debounce(customZoomEnd, 1000);
                this.zoom = d3.zoom()
                    .scaleExtent([1, 100])
                    .translateExtent([[this.xScale(0), this.globalAttrs['marginTop']],
                        [this.xScale(1), this.globalAttrs['height'] - this.globalAttrs['marginBottom']]])
                    .wheelDelta(customDelta);
                this.mainSvg.call(this.zoom
                    .on('zoom', function({transform}) {
                        if (that.selectingRange) {
                            return;
                        }
                        that.alldataG.style('transform', 'translateX(' + transform.x + 'px) scaleX(' + transform.k + ')');
                        that.selectDataG.style('transform', 'translateX(' + transform.x + 'px) scaleX(' + transform.k + ')');
                        that.dataRangeShow = transform.rescaleX(that.dataRangeAll2Pos)
                            .interpolate(d3.interpolateRound).domain();
                        let shift = 0;
                        if (that.dataRangeShow[0] < that.dataRangeAll[0]) shift = that.dataRangeAll[0] - that.dataRangeShow[0];
                        if (that.dataRangeShow[1] > that.dataRangeAll[1]) shift = that.dataRangeAll[1] - that.dataRangeShow[1];
                        that.dataRangeShow = [that.dataRangeShow[0] + shift, that.dataRangeShow[1] + shift];
                        that.dataRangeShow = [Number(that.dataRangeShow[0]), Number(that.dataRangeShow[1])];
                        that.mainSvg.select('#show-text-left')
                            .text(`${that.dataRangeShow[0].toFixed(that.textDigits)}`);
                        that.mainSvg.select('#show-text-right')
                            .text(`${that.dataRangeShow[1].toFixed(that.textDigits)}`);
                    })
                    .on('end', function(event) {
                        const type = event && event.sourceEvent && event.sourceEvent.type;
                        debouncedZoomEnd(type);
                    }))
                    .on('mousedown.zoom', null)
                    .on('dblclick.zoom', null);

                this.mainSvg
                    .append('text')
                    .attr('class', 'info-text')
                    .attr('x', 20)
                    .attr('y', that.globalAttrs['marginTop']-5)
                    .attr('fill', 'currentColor')
                    .attr('font-family', that.textAttrs['font-family'])
                    .attr('font-weight', that.textAttrs['font-weight'])
                    .attr('font-size', that.textAttrs['font-size'])
                    .style('pointer-events', 'none')
                    .style('-webkit-user-select', 'none')
                    .style('-moz-user-select', 'none')
                    .style('-ms-user-select', 'none')
                    .style('user-select', 'none')
                    .style('cursor', 'default')
                    .text(this.title);

                that.mainSvg
                    .append('circle')
                    .attr('cx', 13)
                    .attr('cy', that.globalAttrs['marginTop']-9)
                    .attr('r', 2)
                    .attr('fill', 'currentColor');

                // emphasize line
                this.mainSvg
                    .append('line')
                    .attr('id', 'emp-line')
                    .attr('transform', `translate(0,${this.getYVal(0)})`)
                    .attr('opacity', 0)
                    .attr('stroke-width', 2)
                    .attr('stroke', 'rgb(67,67,67)');
            }
            const selectDataBins = [];
            const allDataBins = [];
            const rectWidth = 1 / this.barNum;
            for (let i = 0; i < this.allData.length; ++i) {
                selectDataBins.push({
                    'id': i,
                    'val': this.selectData[i],
                    'x0': i * rectWidth,
                    'x1': (i+1) * rectWidth,
                });
                allDataBins.push({
                    'id': i,
                    'val': this.hideUnfiltered?0:this.allData[i],
                    'x0': i * rectWidth,
                    'x1': (i+1) * rectWidth,
                });
            }
            this.allDataRectG = this.alldataG.selectAll('g.allDataRect').data(allDataBins, (d)=>d.id);
            this.selectDataRectG = this.selectDataG.selectAll('g.selectDataRect').data(selectDataBins, (d)=>d.id);
            await this.remove();
            await this.update();
            await this.transform();
            await this.create();
            this.zoomed = false;
        },
        create: async function() {
            const that = this;
            return new Promise((resolve, reject) => {
                const allDataRectG = that.allDataRectG.enter()
                    .append('g')
                    .attr('class', 'allDataRect');

                allDataRectG.transition()
                    .duration(that.createDuration)
                    .attr('opacity', 1)
                    .on('end', resolve);

                allDataRectG.append('rect')
                    .attr('x', (d) => that.xScale(d.x0) + that.globalAttrs['insetLeft'])
                    .attr('width', (d) => Math.max(0, that.xScale(d.x1) - that.xScale(d.x0) -
                                                      that.globalAttrs['insetLeft'] - that.globalAttrs['insetRight']))
                    .attr('y', (d, i) => that.getYVal(that.cal(d.val)))
                    .attr('height', (d, i) => that.getYVal(0) - that.getYVal(that.cal(d.val)))
                    .attr('fill', that.globalAttrs['unselectFill'])
                    .append('title')
                    .text((d, i) => [`${d.x0.toFixed(1)} ≤ x < ${d.x1.toFixed(1)}`, `quantity: ${d.val}`].join('\n'));

                const selectDataRectG = that.selectDataRectG.enter()
                    .append('g')
                    .attr('class', 'selectDataRect');

                selectDataRectG.transition()
                    .duration(that.createDuration)
                    .attr('opacity', 1)
                    .on('end', resolve);

                selectDataRectG.append('rect')
                    .attr('x', (d) => that.xScale(d.x0) + that.globalAttrs.insetLeft)
                    .attr('width', (d) => Math.max(0, that.xScale(d.x1) - that.xScale(d.x0) -
                                                      that.globalAttrs.insetLeft - that.globalAttrs.insetRight))
                    .attr('y', (d, i) => that.getYVal(that.cal(d.val)))
                    .attr('height', (d, i) => that.getYVal(0) - that.getYVal(that.cal(d.val)))
                    .attr('fill', that.globalAttrs.selectFill);

                this.mainSvg.selectAll('.shelter').remove();
                this.mainSvg
                    .append('rect')
                    .attr('class', 'shelter')
                    .attr('x', this.xScale(-0.5))
                    .attr('y', this.yScale.range()[1])
                    .attr('width', this.xScale(0) - this.xScale(-0.5))
                    .attr('height', this.yScale.range()[0] + 1 - this.yScale.range()[1])
                    .attr('fill', 'rgb(255,255,255)');
                this.mainSvg
                    .append('rect')
                    .attr('class', 'shelter')
                    .attr('x', this.xScale(1))
                    .attr('y', this.yScale.range()[1])
                    .attr('width', this.xScale(1.05) - this.xScale(1))
                    .attr('height', this.yScale.range()[0] + 1 - this.yScale.range()[1])
                    .attr('fill', 'rgb(255,255,255)');
                if ((that.selectDataRectG.enter().size() === 0) && (that.allDataRectG.enter().size() === 0)) {
                    resolve();
                }
            });
        },
        update: async function() {
            const that = this;
            return new Promise((resolve, reject) => {
                that.allDataRectG.each(function(d, i) {
                    const transformK = (that.dataRangeShow[1]-that.dataRangeShow[0]) / (that.dataRangeAll[1]-that.dataRangeAll[0]);
                    if (that.zoomed) {
                        // eslint-disable-next-line no-invalid-this
                        d3.select(this).select('rect')
                            .attr('x', (d) => {
                                return that.dataRangeAll2Pos(that.dataRangeShow[0] + (that.dataRangeShow[1]-that.dataRangeShow[0]) *i / that.barNum) +
                                transformK * that.globalAttrs.insetLeft;
                            })
                            .attr('width', (d) => Math.max(0,
                                (that.dataRangeAll2Pos(that.dataRangeShow[1]) - that.dataRangeAll2Pos(that.dataRangeShow[0])) / that.barNum -
                                transformK * (that.globalAttrs.insetLeft + that.globalAttrs.insetRight)))
                            .attr('height', that.getYVal(0) - that.getYVal(that.cal(d.val)))
                            .attr('y', that.getYVal(that.cal(d.val)))
                            .attr('opacity', 0);
                        // eslint-disable-next-line no-invalid-this
                        d3.select(this).select('rect')
                            .transition()
                            .duration(that.updateDuration)
                            .attr('opacity', 1)
                            .on('end', resolve);
                    } else {
                        // eslint-disable-next-line no-invalid-this
                        d3.select(this).select('rect')
                            .attr('x', (d) => {
                                return that.dataRangeAll2Pos(that.dataRangeShow[0] + (that.dataRangeShow[1]-that.dataRangeShow[0]) *i / that.barNum) +
                                transformK * that.globalAttrs.insetLeft;
                            })
                            .attr('width', (d) => Math.max(0,
                                (that.dataRangeAll2Pos(that.dataRangeShow[1]) - that.dataRangeAll2Pos(that.dataRangeShow[0])) / that.barNum -
                                transformK * (that.globalAttrs.insetLeft + that.globalAttrs.insetRight)))
                            .transition()
                            .duration(that.updateDuration)
                            .attr('height', that.getYVal(0) - that.getYVal(that.cal(d.val)))
                            .attr('y', that.getYVal(that.cal(d.val)))
                            .on('end', resolve);
                    }
                });
                that.selectDataRectG.each(function(d, i) {
                    const transformK = (that.dataRangeShow[1]-that.dataRangeShow[0]) / (that.dataRangeAll[1]-that.dataRangeAll[0]);
                    if (that.zoomed) {
                        // eslint-disable-next-line no-invalid-this
                        d3.select(this).select('rect')
                            .attr('x', (d) => {
                                return that.dataRangeAll2Pos(that.dataRangeShow[0] + (that.dataRangeShow[1]-that.dataRangeShow[0])*i/that.barNum) +
                                transformK * that.globalAttrs.insetLeft;
                            })
                            .attr('width', (d) => Math.max(0,
                                (that.dataRangeAll2Pos(that.dataRangeShow[1]) - that.dataRangeAll2Pos(that.dataRangeShow[0])) / that.barNum -
                                transformK * (that.globalAttrs.insetLeft + that.globalAttrs.insetRight)))
                            .attr('y', that.getYVal(that.cal(d.val)))
                            .attr('height', that.getYVal(0) - that.getYVal(that.cal(d.val)))
                            .attr('opacity', 0);
                        // eslint-disable-next-line no-invalid-this
                        d3.select(this).select('rect')
                            .transition()
                            .duration(that.updateDuration)
                            .attr('opacity', 1)
                            .on('end', resolve);
                    } else {
                        // eslint-disable-next-line no-invalid-this
                        d3.select(this).select('rect')
                            .attr('x', (d) => {
                                return that.dataRangeAll2Pos(that.dataRangeShow[0] + (that.dataRangeShow[1]-that.dataRangeShow[0]) *i / that.barNum) +
                                transformK * that.globalAttrs.insetLeft;
                            })
                            .attr('width', (d) => Math.max(0,
                                (that.dataRangeAll2Pos(that.dataRangeShow[1]) - that.dataRangeAll2Pos(that.dataRangeShow[0])) / that.barNum -
                                transformK * (that.globalAttrs.insetLeft + that.globalAttrs.insetRight)))
                            .transition()
                            .duration(that.updateDuration)
                            .attr('height', that.getYVal(0) - that.getYVal(that.cal(d.val)))
                            .attr('y', that.getYVal(that.cal(d.val)))
                            .on('end', resolve);
                    }
                });
                if ((that.selectDataRectG.size() === 0) && (that.allDataRectG.size() === 0)) {
                    resolve();
                }
            });
        },
        remove: async function() {
            const that = this;
            return new Promise((resolve, reject) => {
                that.allDataRectG.exit()
                    .transition()
                    .duration(that.removeDuration)
                    .attr('opacity', 0)
                    .remove()
                    .on('end', resolve);
                that.selectDataRectG.exit()
                    .transition()
                    .duration(that.removeDuration)
                    .attr('opacity', 0)
                    .remove()
                    .on('end', resolve);

                if ((that.selectDataRectG.exit().size() === 0) && (that.allDataRectG.exit().size() === 0)) {
                    resolve();
                }
            });
        },
        transform: async function() {
        },
        cal: function(d) {
            if (this.displayMode === 'log') return Math.log10(Math.max(1, d));
            else if (this.displayMode === 'linear') return d;
        },
        getYVal: function(y) {
            if (y === 0) return this.globalAttrs.height - this.globalAttrs.marginBottom;
            else return this.yScale(y);
        },
        getSplit: function(range, num) {
            const split = [];
            const interval = (range[1] - range[0]) / num;
            for (let i = 0; i < num; i++) {
                split.push(range[0] + i * interval);
            }
            split.push(range[1]);
            return split;
        },
    },
    mounted: function() {
        this.globalAttrs['width'] = this.$refs.svg.clientWidth;
        this.globalAttrs['height'] = this.$refs.svg.clientHeight;
    },
};
</script>

<style scoped>
/* text.info-text {
    cursor: default;
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
    user-select: none;
} */
</style>
