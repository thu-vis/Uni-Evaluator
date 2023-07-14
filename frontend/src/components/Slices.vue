<template>
    <div class="slices-content" ref="div">
        <svg class="slices-svg-title">
            <g id="slices-title-g"></g>
        </svg>
        <div class="slices-data-content">
            <svg class="slices-svg" width="100%" ref="svg">
                <g id="slices-g"></g>
            </svg>
        </div>
        <svg class="input-text">
            <g id="input-g">
                <rect x="1" y="1" width="120" height="45" stroke="rgb(67,67,67)" stroke-width="2"
                    fill="rgb(255,255,255)"></rect>
                <foreignObject x="6" y="5" width="160" height="160">
                    <input type="text" style="width: 100px;" id="input"/>
                </foreignObject>
            </g>
        </svg>
    </div>
</template>

<script>
// import Vue from 'vue';
// import * as VueLineUp from 'vue-lineup';
import {mapGetters} from 'vuex';
import * as d3 from 'd3';
import Util from './Util.vue';
import GlobalVar from './GlovalVar.vue';
window.d3 = d3;

// Vue.use(VueLineUp);

export default {
    name: 'Slices',
    mixins: [Util, GlobalVar],
    props: {
        dataSlices: {
            type: Array,
            default: undefined,
        },
        sliceSplits: {
            type: Object,
            default: undefined,
        },
        minSupport: {
            type: Number,
            default: 0.1,
        },
    },
    computed: {
        ...mapGetters(['labelnames']),
        svg: function() {
            return d3.select('.slices-svg');
        },
        titleG: function() {
            return d3.select('.slices-svg-title').select('g#slices-title-g');
        },
        slicesG: function() {
            return this.svg.select('g#slices-g');
        },
        inputSvg: function() {
            return d3.select('.input-text');
        },
        inputG: function() {
            return this.inputSvg.select('g#input-g');
        },
        dragG: function() {
            return this.inputSvg.select('g#drag-info');
        },
    },
    data() {
        return {
            posShift: ['left', 'upper left', 'upper', 'upper right', 'right',
                'lower right', 'lower', 'lower left'],
            sizeBias: ['larger', 'smaller'],
            errorTypes: [
                'Class error',
                'Location error',
                'Class & Location error',
                'Duplicate error',
                'Class & Duplicate error',
                'Location & Duplicate error',
                'Class & Location & Duplicate error',
                'Background error',
                'Missed groundtruth',
            ],
            lineHeight: 16,
            rectHeight: 8,
            titleHeight: 55,
            colWidth: [],
            colStart: [],
            colTitles: [],
            complementCols: [],
            fontSize: 14,
            showSlices: [],
            rawSlices: [],
            fillColor: 'rgb(216,216,216)',
            bgColor: 'rgb(245,245,245)',
            maxQuantity: 1,
            filterDict: {},
            filterAttr: '',
            shiftx: 0,
            sortAttr: 'id',
            sortType: 0, // 0 ascend, 1 descend
            combinedColumns: [],
            complementColumns: [],
        };
    },
    watch: {
        dataSlices: function() {
            const that = this;
            this.rawSlices = [];
            // this.colTitles = ['pr_cat', 'gt_cat', 'quantity', 'support', 'precision', 'recall',
            this.colTitles = ['pr_cat', 'gt_cat', 'subset_size', 'precision', 'recall',
                'pr_conf', 'gt_size', 'pr_size', 'gt_ar', 'pr_ar'];
            // 'pr_conf_d', 'gt_size_d', 'pr_size_d', 'gt_ar_d', 'pr_ar_d'];
            // 'pr_conf_ave', 'gt_size_ave', 'pr_size_ave', 'gt_ar_ave', 'pr_ar_ave'];
            this.colWidth = [];
            this.colTitles.forEach((element, index) => {
                if (index >= 3) that.colWidth.push(65);
                else if (index == 2) that.colWidth.push(70);
                else that.colWidth.push(50);
                // else that.colWidth.push(Math.max(50, that.getTextWidth('1-'+element, `normal ${that.fontSize}px Arial`)));
            });
            // calculate width for categories
            let maxWidth = 0;
            this.maxQuantity = 1;
            this.dataSlices.forEach((element, index) => {
                that.rawSlices.push({
                    ...element,
                    id: index,
                });
                maxWidth = Math.max(maxWidth, that.getTextWidth(element.pr_cat, `normal ${that.fontSize}px Arial`));
                maxWidth = Math.max(maxWidth, that.getTextWidth(element.gt_cat, `normal ${that.fontSize}px Arial`));
                that.maxQuantity = Math.max(that.maxQuantity, element.quantity);
            });
            maxWidth = Math.min(maxWidth, 65);
            that.colWidth[0] = maxWidth;
            that.colWidth[1] = maxWidth;
            this.updateColStart();
            const svgRealWidth = this.$refs.svg.clientWidth;
            const svgWidth = that.colStart[that.colStart.length-1]+that.colWidth[that.colWidth.length-1];
            // const scale = (svgRealWidth-5) / svgWidth;
            that.shiftx = (svgRealWidth - svgWidth) / 2;
            this.svg.attr('transform', `translate(${that.shiftx}, 4)`);
            d3.select('.slices-svg-title')
                .attr('width', svgWidth)
                .attr('height', that.titleHeight)
                .attr('transform', `translate(${that.shiftx}, 5)`);
            this.getDataAndRender();
        },
    },
    methods: {
        updateColStart: function() {
            this.colStart = [0];
            const that = this;
            this.colWidth.forEach((element, index) => {
                if (index < that.colWidth.length - 1) {
                    that.colStart.push(that.colStart[index] + element + 10);
                }
            });
        },
        clickSlice: function(d) {
            // console.log('click', d);
            this.$emit('showSlice', this.dataSlices[d.id]);
        },
        getDataAndRender: function() {
            // console.log(this.sortType, this.sortAttr);
            const that = this;
            this.showSlices = [];
            const sortSlices = this.rawSlices;
            if (that.combinedColumns.length > 0) {
                sortSlices.forEach((element, index) => {
                    element['combine'] = 0;
                    that.combinedColumns.forEach((el, ind) => {
                        const colName = that.colTitles[el];
                        // if (colName === 'precision' || colName === 'recall') {
                        //     element['combine'] += (1-element[colName]);
                        // } else {
                        //     element['combine'] += (element[colName]+1) / 10;
                        // }
                        if (that.complementColumns.indexOf(colName) >= 0) element['combine'] += 1 - element[colName];
                        else element['combine'] += element[colName];
                    });
                    element['combine'] /= that.combinedColumns.length;
                    element['combine'] = Math.max(0, element['combine']);
                });
            }
            // sort
            sortSlices.sort(function(a, b) {
                let flag;
                if (a[that.sortAttr] === b[that.sortAttr]) flag = (a.id > b.id)?1:-1;
                else flag = (a[that.sortAttr] > b[that.sortAttr])?1:-1;
                return that.sortType===0?flag:-flag;
            });
            // filter
            let idx = 0;
            sortSlices.forEach((element, index) => {
                let flag = true;
                for (const key in that.filterDict) {
                    if (that.filterDict[key].length > 0) {
                        if (element[key].indexOf(that.filterDict[key])===-1) {
                            flag = false;
                            break;
                        }
                    }
                }
                if (flag && element.support >= this.minSupport) {
                    that.showSlices.push({
                        ...element,
                        y: idx * that.lineHeight,
                    });
                    idx++;
                }
            });
            this.render();
        },
        swapColumn: function(colTitleClass, targetPos) {
            const srcColId = this.colTitles.indexOf(colTitleClass.split('-')[2]);
            targetPos += this.colStart[srcColId];
            let tgtColId = -1;
            for (let i = 0; i < this.colStart.length; ++i) {
                if (targetPos >= this.colStart[i] && targetPos <= this.colStart[i] + this.colWidth[i]) {
                    tgtColId = i;
                    break;
                }
            }
            if (tgtColId === -1) return;
            // console.log(tgtColId, colTitleClass);
            if (srcColId < 3 || tgtColId < 3 || srcColId === tgtColId) return;
            const newTitles = [];
            const newColWidth = [];
            for (let i = 0; i < this.colTitles.length; ++i) {
                if (i !== tgtColId && i !== srcColId) {
                    newTitles.push(this.colTitles[i]);
                    newColWidth.push(this.colWidth[i]);
                } else if (srcColId < tgtColId && tgtColId === i) {
                    newTitles.push(this.colTitles[srcColId]);
                    newColWidth.push(this.colWidth[srcColId]);
                    newTitles.push(this.colTitles[i]);
                    newColWidth.push(this.colWidth[i]);
                    this.combinedColumns = [i-1, i];
                } else if (tgtColId < srcColId && tgtColId === i) {
                    newTitles.push(this.colTitles[i]);
                    newColWidth.push(this.colWidth[i]);
                    newTitles.push(this.colTitles[srcColId]);
                    newColWidth.push(this.colWidth[srcColId]);
                    this.combinedColumns = [i, i+1];
                }
            }
            this.colTitles = newTitles;
            this.colWidth = newColWidth;
            this.updateColStart();
            this.getDataAndRender();
        },
        render: function() {
            const that = this;
            const drag = function() {
                const dragged = function(e, d) {
                    // eslint-disable-next-line no-invalid-this
                    const ge = d3.select(this);
                    const srcColId = that.colTitles.indexOf(ge.attr('id').split('-')[2]);
                    that.dragG.attr('opacity', 0.7)
                        .attr('transform', `translate(${e.x+that.colStart[srcColId]},${e.y})`);
                    that.dragG.select('rect')
                        .attr('width', ge.attr('width'));
                    that.dragG.select('text')
                        .text(ge.attr('id').split('-')[2]);
                    that.inputSvg.attr('transform', `translate(0,${-that.$refs.div.clientHeight})`);
                };
                const dragended = function(e, d) {
                    that.inputSvg.attr('transform', '');
                    that.dragG.attr('opacity', 0);
                    // eslint-disable-next-line no-invalid-this
                    that.swapColumn(this.id, e.x);
                };
                return d3.drag().on('drag', dragged).on('end', dragended);
            };
            const titleElem = this.titleG.selectAll('.col-title').data(this.colTitles, (d)=>d);
            titleElem.transition()
                .duration(that.updateDuration)
                .attr('transform', (d, i) => `translate(${this.colStart[i]}, 0)`);
            const combinedTitles = titleElem.filter((d, i)=>that.combinedColumns.indexOf(i)>=0)
                .selectAll('.title-info');
            combinedTitles.transition().duration(that.updateDuration)
                .attr('transform', 'translate(0,32)');
            combinedTitles.selectAll('.button').transition().duration(that.updateDuration)
                .attr('opacity', 0)
                .attr('pointer-events', 'none');
            const otherTitles = titleElem.filter((d, i)=>that.combinedColumns.indexOf(i)<0)
                .selectAll('.title-info');
            otherTitles.transition().duration(that.updateDuration)
                .attr('transform', 'translate(0,5)');
            otherTitles.selectAll('.button').transition().duration(that.updateDuration)
                .attr('opacity', 1)
                .attr('pointer-events', 'default');
            const combineHead = this.titleG.select('#combined-title');
            const withPrefix = (x) => (this.complementCols.indexOf(x) >= 0 ? '1-' : '') + x;
            const combinedText = () => `${withPrefix(this.colTitles[this.combinedColumns[0]])}` + ' + ' +
                    `${withPrefix(this.colTitles[this.combinedColumns[1]])}`;
            if (combineHead.size() === 0 && this.combinedColumns.length > 0) {
                const combinedTitleG = this.titleG.append('g').attr('id', 'combined-title')
                    .attr('transform', `translate(${this.colStart[this.combinedColumns[0]]},5)`)
                    .attr('opacity', 0);
                combinedTitleG.append('text')
                    .text(combinedText())
                    .attr('font-size', this.fontSize)
                    .attr('x', 0)
                    .attr('y', 8);

                combinedTitleG.append('svg:image')
                    .attr('class', 'button')
                    .attr('x', 0)
                    .attr('y', 11)
                    .attr('width', 16)
                    .attr('height', 16)
                    .attr('opacity', 1)
                    .attr('xlink:href', '/static/images/sort.svg')
                    .attr('cursor', 'pointer')
                    .on('click', (ev) => {
                        if (that.sortAttr === 'combine') {
                            that.sortType++;
                            if (that.sortType === 2) {
                                that.sortAttr = 'id';
                                that.sortType = 0;
                            }
                        } else {
                            that.sortAttr = 'combine';
                            that.sortType = 0;
                        }
                        that.getDataAndRender();
                    })
                    .append('title')
                    .text('Sort');

                combinedTitleG.append('svg:image')
                    .attr('class', 'button')
                    .attr('x', 20)
                    .attr('y', 11)
                    .attr('width', 16)
                    .attr('height', 16)
                    .attr('opacity', 1)
                    .attr('xlink:href', '/static/images/cross.svg')
                    .attr('cursor', 'pointer')
                    .on('click', (ev) => {
                        that.combinedColumns = [];
                        that.getDataAndRender();
                    })
                    .append('title')
                    .text('Remove combine');
                combinedTitleG.append('polyline')
                    .attr('points', `0,28
                        ${this.colWidth[this.combinedColumns[0]]+this.colWidth[this.combinedColumns[1]]+10},28`)
                    .attr('stroke', 'rgb(127,127,127)')
                    .attr('stroke-width', 2);
                combinedTitleG.transition()
                    .duration(that.updateDuration)
                    .attr('opacity', 1);
            } else if (this.combinedColumns.length > 0) {
                combineHead.attr('pointer-events', 'default');
                combineHead.select('text').text(combinedText());
                combineHead.attr('transform', `translate(${this.colStart[this.combinedColumns[0]]},5)`);
                combineHead.transition().duration(that.updateDuration)
                    .attr('opacity', 1);
            } else if (this.combinedColumns.length === 0 && combineHead.size() > 0) {
                combineHead.attr('pointer-events', 'none');
                combineHead.transition().duration(that.updateDuration)
                    .attr('opacity', 0);
            }

            const titleElemCreate = titleElem.enter().append('g')
                .attr('class', 'col-title')
                .attr('transform', (d, i) => `translate(${this.colStart[i]}, 0)`);
            titleElemCreate.append('rect')
                .attr('id', (d)=>`col-title-${d}`)
                .attr('fill', 'rgb(255,255,255)')
                .attr('x', 0)
                .attr('y', 0)
                .attr('width', (d, i)=>that.colWidth[i])
                .attr('height', that.titleHeight-2)
                .attr('cursor', 'grab')
                .call(drag());
            titleElemCreate.append('polyline')
                .attr('points', (d, i)=>`0,${this.titleHeight-2}
                    ${this.colWidth[i]},${this.titleHeight-2}`)
                .attr('stroke', 'rgb(127,127,127)')
                .attr('stroke-width', 2);
            const titleElemInfoCreate = titleElemCreate.append('g')
                .attr('class', 'title-info')
                .attr('transform', 'translate(0,5)');
            titleElemInfoCreate.append('text')
                .text((d) => d)
                .attr('font-size', this.fontSize)
                .attr('x', 0)
                .attr('y', 15);
            titleElemInfoCreate.each(function(d, i) {
                // eslint-disable-next-line no-invalid-this
                const ge = d3.select(this);
                ge.append('svg:image')
                    .attr('class', 'button')
                    .attr('x', 0)
                    .attr('y', 20)
                    .attr('width', 18)
                    .attr('height', 18)
                    .attr('opacity', 1)
                    .attr('xlink:href', '/static/images/sort.svg')
                    .attr('cursor', 'pointer')
                    .on('click', (ev) => {
                        if (that.sortAttr === d) {
                            that.sortType++;
                            if (that.sortType === 2) {
                                that.sortAttr = 'id';
                                that.sortType = 0;
                            }
                        } else {
                            that.sortAttr = d;
                            that.sortType = 0;
                        }
                        that.getDataAndRender();
                    })
                    .append('title')
                    .text('Sort');

                ge.filter((d) => d === 'precision' || d === 'recall').append('svg:image')
                    .attr('class', 'button')
                    .attr('x', 22)
                    .attr('y', 22)
                    .attr('width', 18)
                    .attr('height', 18)
                    .attr('opacity', 1)
                    .attr('xlink:href', '/static/images/c.png')
                    .attr('cursor', 'pointer')
                    .on('click', (ev) => {
                        const pos = that.complementColumns.indexOf(d);
                        let title = d3.selectAll('.title-info').select('text')._groups[0][i];
                        title = d3.select(title);
                        if (pos < 0) {
                            that.complementColumns.push(d);
                            const titleText = title.text();
                            title.text('1-' + titleText);
                            that.complementCols.push(titleText);
                        } else {
                            that.complementColumns.splice(pos, 1);
                            const titleText = title.text().slice(2);
                            title.text(titleText);
                            that.complementCols.splice(that.complementCols.indexOf(titleText), 1);
                        }
                        that.getDataAndRender();
                    })
                    .append('title')
                    .text('Complement');

                ge.filter((d) => d === 'pr_cat' || d === 'gt_cat').append('svg:image')
                    .attr('class', 'button')
                    .attr('x', 20)
                    .attr('y', 19)
                    .attr('width', 18)
                    .attr('height', 18)
                    .attr('opacity', 1)
                    .attr('xlink:href', '/static/images/filter.svg')
                    .attr('cursor', 'pointer')
                    .on('click', (ev) => {
                        that.inputG.attr('opacity', 1);
                        that.inputSvg.attr('transform', `translate(0,${-that.$refs.div.clientHeight})`);
                        that.inputG.attr('transform', `translate(${that.colStart[i] + that.shiftx + 15 + 20},45)`);
                        that.filterAttr = d;
                    })
                    .append('title')
                    .text('Filter');
            });
            const slicesInG = this.slicesG.selectAll('.slice-g').data(this.showSlices, (d)=>d.id);
            // exit
            slicesInG.exit().transition()
                .duration(this.removeDuration)
                .attr('opacity', 0)
                .remove();
            // transform
            // update
            this.svg.transition()
                .duration(that.updateDuration)
                .attr('height', that.lineHeight * that.showSlices.length);

            slicesInG.transition()
                .duration(that.updateDuration)
                .attr('transform', (d) => `translate(0, ${d.y+1})`);

            this.colTitles.forEach((element, index) => {
                slicesInG.selectAll(`g.col-${element}-cell`)
                    .transition()
                    .duration(that.updateDuration)
                    .attr('transform', `translate(${that.colStart[index]},0)`);
            });
            // create
            const createElem = slicesInG.enter().append('g').attr('class', 'slice-g')
                .attr('transform', (d) => `translate(0, ${d.y+1})`)
                .on('mouseover', function(ev, d) {
                    // eslint-disable-next-line no-invalid-this
                    d3.select(this)
                        .selectAll('.info')
                        .attr('opacity', 1);
                })
                .on('mouseout', function(ev, d) {
                    // eslint-disable-next-line no-invalid-this
                    d3.select(this)
                        .selectAll('.info')
                        .attr('opacity', 0);
                })
                .on('click', (ev, d) => {
                    console.log(d);
                    that.clickSlice(d);
                });

            createElem.append('rect')
                .attr('fill', 'rgb(255,255,255)')
                .attr('x', 0)
                .attr('y', 0)
                .attr('width', that.colStart[that.colStart.length-1]+that.colWidth[that.colWidth.length-1])
                .attr('height', that.lineHeight);

            const realTitles = this.colTitles.map((d, index) => ({
                element: d,
                index: index,
            }));

            const allElem = slicesInG.merge(createElem);

            let col = allElem
                .selectAll('.col-sub-cell')
                .data((d, dindex) => {
                    const currentData = [];
                    for (const e of realTitles) {
                        const element = e.element;
                        const index = e.index;
                        const ret = {
                            element,
                            text: '',
                            x: 0,
                            xRect: 0,
                            xText: 0,
                            yText: that.lineHeight/2+that.fontSize/2-3,
                            yRect: that.lineHeight/2-that.rectHeight/2-1,
                            bgWidth: that.colWidth[index] || 0,
                            width: 0,
                            height: that.rectHeight,
                            textClass: 'normal',
                            showText: 0,
                            showRect: 1,
                            offset: this.colStart[index],
                        };

                        ret.value = ret.text = d[element];
                        if (that.complementColumns.indexOf(element) >= 0) {
                            ret.value = 1 - ret.value;
                            ret.text = Number(ret.value).toFixed(3);
                        }
                        if (that.combinedColumns.indexOf(index) == 0) {
                            ret.bgWidth = this.colStart[index] - this.colStart[index - 1] + 1.5;
                        } else if (that.combinedColumns.indexOf(index) > 0) {
                            const last = currentData[currentData.length - 1];
                            const bgWidth = last.bgWidth + ret.bgWidth - 2.5;
                            last.bgWidth = bgWidth / 2;
                            ret.bgWidth = bgWidth / 2;
                            last.width = last.bgWidth * last.value;
                        }
                        ret.width = ret.bgWidth * ret.value;

                        if (that.combinedColumns.indexOf(index) > 0) {
                            const last = currentData[currentData.length - 1];
                            ret.offset = last.offset + last.bgWidth;
                            ret.xRect = last.width - last.bgWidth + 2.5;
                            ret.bgWidth += 2.5;
                            ret.text = Number(last.value + ret.value).toFixed(3);
                            ret.xText = last.offset - ret.offset;
                        }

                        if (element == 'subset_size') {
                            ret.width /= that.maxQuantity;
                        }

                        if (element === 'pr_cat' || element === 'gt_cat') {
                            ret.showText = 1;
                            ret.showRect = 0;
                        } else if (element.indexOf('precision') >= 0 ||
                            element.indexOf('recall') >= 0 || index < 14) {
                            ret.showText = 1;
                            ret.textClass = 'info';
                            if (that.combinedColumns.indexOf(index) == 0) {
                                ret.showText = 0;
                            }
                        }
                        currentData.push(ret);
                    }
                    return currentData;
                }, (d) => d.element);

            const colG = col.enter()
                .append('g')
                .attr('class', 'col-sub-cell');

            colG.filter((d) => d.showRect).append('rect')
                .attr('class', 'background');

            colG.filter((d) => d.showRect).append('rect')
                .attr('class', 'body');

            colG.filter((d) => d.showText).append('text')
                .attr('class', (d) => d.textClass)
                .attr('font-size', that.fontSize)
                .text((d) => (d.text.length > 10)?(d.text.slice(0, 8)+'..'):d.text);

            colG.filter((d) => d.showText && d.text.length > 10)
                .append('title')
                .text((d) => d.text);

            col = col.merge(colG);

            col.select('rect.background')
                .attr('fill', that.bgColor)
                .attr('y', (d) => d.yRect)
                .attr('height', (d) => d.height)
                .transition()
                .duration(that.updateDuration)
                .attr('x', (d) => d.x)
                .attr('width', (d) => d.bgWidth);

            col.select('rect.body')
                .attr('fill', that.fillColor)
                .attr('y', (d) => d.yRect)
                .attr('height', (d) => d.height)
                .transition()
                .duration(that.updateDuration)
                .attr('x', (d) => d.xRect)
                .attr('width', (d) => d.width);

            col.filter((d) => !d.showText)
                .select('text')
                .remove();

            col.filter((d) => d.showText)
                .select('text')
                .attr('class', (d) => d.textClass)
                .text((d) => (d.text.length > 10)?(d.text.slice(0, 8)+'..'):d.text)
                .attr('x', (d) => d.xText)
                .attr('y', (d) => d.yText);

            col.transition()
                .duration(that.updateDuration)
                .attr('transform', (d) => `translate(${d.offset}, 0)`);

            createElem.append('rect')
                .attr('class', 'info')
                .attr('fill', 'none')
                .attr('stroke-width', 2)
                .attr('stroke', 'rgb(127,127,127)')
                .attr('x', 1)
                .attr('y', 0)
                .attr('width', that.colStart[that.colStart.length-1]+that.colWidth[that.colWidth.length-1])
                .attr('height', that.lineHeight-2);

            col.selectAll('.info').attr('opacity', 0);
            createElem.selectAll('.info').attr('opacity', 0);
        },
    },
    mounted: function() {
        const h = this.$refs.div.clientHeight;
        const w = this.$refs.div.clientWidth;
        this.inputSvg
            .attr('width', w)
            .attr('height', h);
        this.inputG.attr('opacity', 0);
        this.inputG.append('svg:image')
            .attr('x', 20)
            .attr('y', 28)
            .attr('width', 15)
            .attr('height', 15)
            .attr('xlink:href', '/static/images/cross.svg')
            .attr('cursor', 'pointer')
            .on('click', (ev, d) => {
                this.inputSvg.attr('transform', '');
                this.inputG.attr('opacity', 0);
            })
            .append('title')
            .text('Cancel');
        this.inputG.append('svg:image')
            .attr('x', 85)
            .attr('y', 27)
            .attr('width', 15)
            .attr('height', 15)
            .attr('xlink:href', '/static/images/tick.svg')
            .attr('cursor', 'pointer')
            .on('click', (ev, d) => {
                this.inputG.attr('opacity', 0);
                this.inputSvg.attr('transform', '');
                this.filterDict[this.filterAttr] = document.getElementById('input').value;
                this.getDataAndRender();
            })
            .append('title')
            .text('Apply');
        this.inputSvg.append('g')
            .attr('id', 'drag-info');
        this.dragG.append('rect')
            .attr('x', -1)
            .attr('y', -1)
            .attr('width', 0)
            .attr('height', this.titleHeight)
            .attr('stroke', 'rgb(127,127,127)')
            .attr('stroke-width', 2)
            .attr('fill', 'rgb(255,255,255)');
        this.dragG.append('text')
            .attr('font-size', this.fontSize)
            .attr('x', 0)
            .attr('y', 13)
            .text('');
    },
};
</script>

<style scoped>
.slices-content {
    height: calc(100% - 2px);
    background: rgb(255, 255, 255);
    border: 1px solid #c1c1c1;
    border-radius: 5px;
}

.slices-data-content {
    height: calc(100% - 60px);
    display: block;
    overflow-x: hidden;
    overflow-y: auto;
}

.slices-data-content::-webkit-scrollbar {
    display: none;
}
</style>
