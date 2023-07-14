<template>
    <svg id="confusion-svg" width="100%" height="100%" ref="svg">
        <g id="main-g" transform="translate(0,0)">
            <g id="legend-g" transform="translate(0,0)" opacity="1"></g>
            <g id="horizon-text-g" transform="translate(0, 0)">
                <text id="horizon-legend" transform="translate(0,0) rotate(270)" text-anchor="middle" font-size="15" opacity="0"
                    font-weight="normal">Ground Truth</text>
            </g>
            <g id="vertical-text-g" transform="translate(0, 0) rotate(-90)">
                <text id="vertical-legend" transform="translate(0,0) rotate(90)" opacity="0"
                    text-anchor="middle" font-size="15" font-weight="normal">Prediction</text>
            </g>
            <g id="matrix-cells-g" transform="translate(0, 0)"></g>
            <g id="class-statistics-g" transform="translate(0, 0)"></g>
        </g>
    </svg>
</template>

<script>
import {mapGetters} from 'vuex';
import * as d3 from 'd3';
window.d3 = d3;
import Util from './Util.vue';
import GlobalVar from './GlovalVar.vue';
import clone from 'just-clone';

export default {
    name: 'ConfusionMatrix',
    mixins: [Util, GlobalVar],
    props: {
        confusionMatrix: {
            type: Array,
            default: undefined,
        },
        matrixMode: {
            type: String,
            default: 'confusion',
        },
        classStatistics: {
            type: Array,
            default: undefined,
        },
        normalizationMode: {
            type: String,
            default: 'row',
        },
        statisticsInfo: {
            type: String,
            default: '',
        },
    },
    computed: {
        ...mapGetters([
            'labelHierarchy',
            'labelnames',
            'dataName',
            'directionLen',
        ]),
        baseMatrix: function() {
            return this.confusionMatrix;
        },
        indexNames: function() {
            return this.labelnames;
        },
        rawHierarchy: function() {
            return this.labelHierarchy;
        },
        name2index: function() {
            const result = {};
            for (let i=0; i<this.indexNames.length; i++) {
                result[this.indexNames[i]] = i;
            }
            return result;
        },
        svg: function() {
            return d3.select('#confusion-svg');
        },
        matrixWidth: function() {
            return this.showNodes.length * this.cellAttrs['size'];
        },
        svgWidth: function() {
            return this.leftCornerSize + this.textMatrixMargin + this.matrixWidth + 50;// legend height
        },
        colorCellSize: function() {
            return this.showColor?this.cellAttrs['size']*0.7:0;
        },
        colorCellMargin: function() {
            return this.showColor?10:0;
        },
        horizonTextG: function() {
            return this.svg.select('g#horizon-text-g');
        },
        verticalTextG: function() {
            return this.svg.select('g#vertical-text-g');
        },
        matrixCellsG: function() {
            return this.svg.select('g#matrix-cells-g');
        },
        legendG: function() {
            return this.svg.select('g#legend-g');
        },
        mainG: function() {
            return this.svg.select('g#main-g');
        },
        statG: function() {
            return this.svg.select('g#class-statistics-g');
        },
        horizonLegend: function() {
            return this.svg.select('text#horizon-legend');
        },
        verticalLegend: function() {
            return this.svg.select('text#vertical-legend');
        },
        maxHorizonTextWidth: function() {
            let maxwidth = 0;
            for (const node of this.showNodes) {
                const textwidth = this.getTextWidth(node.name,
                    `${this.horizonTextAttrs['font-weight']} ${this.horizonTextAttrs['font-size']}px ${this.horizonTextAttrs['font-family']}`);
                const arrowIconNum = node.children.length===0?node.depth:node.depth+1;
                maxwidth = Math.max(maxwidth, this.horizonTextAttrs['leftMargin']*node.depth + textwidth +
                    arrowIconNum*(this.horizonTextAttrs['font-size'] + this.horizonTextAttrs['iconMargin'])+
                    this.colorCellSize+this.colorCellMargin+15);
            }
            return maxwidth+15;
        },
        legendWidth: function() {
            return Math.min(250, this.matrixWidth+this.leftCornerSize);
        },
        leftCornerSize: function() {
            return this.maxHorizonTextWidth;
        },
        colorScaleDefault: function() {
            const colorRange = [d3.rgb('rgb(232,243,250)'), d3.rgb('rgb(18,131,192)')];
            if (this.normalizationMode !== 'total') {
                return d3.scaleSequential([0, 1], colorRange).clamp(true);
            } else return d3.scaleSequential([0, this.maxCellValue], colorRange).clamp(true);
        },
    },
    mounted: function() {
        // init legend
        this.horizonLegend.attr('opacity', 0);
        this.verticalLegend.attr('opacity', 0);
        this.hierarchy = this.getHierarchy(this.rawHierarchy);
        this.getDataAndRender();
    },
    watch: {
        labelHierarchy: function(newLabelHierarchy, oldLabelHierarchy) {
            this.hierarchy = this.getHierarchy(newLabelHierarchy);
            this.getDataAndRender();
        },
        confusionMatrix: function() {
            this.legendExist = false;
            this.getDataAndRender();
        },
        matrixMode: function() {
            this.getDataAndRender();
        },
        normalizationMode: function() {
            this.legendExist = false;
            this.getDataAndRender();
        },
        classStatistics: function() {
            this.getDataAndRender();
        },
    },
    data: function() {
        return {
            hierarchy: {},
            // layout
            textGWidth: 0,
            cellWidth: 10,
            textMatrixMargin: 10,
            showNodes: [],
            cells: [],
            classStatShow: [],
            // layout elements
            horizonTextinG: null,
            verticalTextinG: null,
            matrixCellsinG: null,
            classStatinG: null,
            // render attrs
            horizonTextAttrs: {
                'gClass': 'horizon-one-line-g',
                'leftMargin': 30,
                'text-anchor': 'start',
                'font-family': 'Arial',
                'font-weight': 'normal',
                'font-size': 15,
                'iconMargin': 5,
                'iconDy': 3,
                'indent-line-stroke': 'gray',
                'indent-line-stroke-width': 2,
            },
            verticalTextAttrs: {
                'gClass': 'vertical-one-line-g',
                'leftMargin': 30,
                'text-anchor': 'start',
                'font-family': 'Arial',
                'font-weight': 'normal',
                'font-size': 15,
                'iconMargin': 5,
                'iconDy': 3,
                'indent-line-stroke': 'gray',
                'indent-line-stroke-width': 2,
            },
            cellAttrs: {
                'gClass': 'one-cell-g',
                'size': 30,
                'stroke-width': '1px',
                'stroke': 'gray',
                'slash-text-stroke': 'gray',
                'text-fill': '#FF6A6A',
                'text-anchor': 'start',
                'font-family': 'Arial',
                'font-weight': 'normal',
                'font-size': 15,
                'cursor': 'pointer',
                'direction-color': 'rgb(97,97,97)',
                'size-color': ['rgb(216,216,216)', 'rgb(250,188,5)', 'rgb(124,198,39)'],
            },
            statAttrs: {
                'gClass': 'class-stat-g',
                'width': 50,
                'height': 5,
                'font-family': 'Arial',
                'font-weight': 'normal',
                'font-size': 13,
                'bg-color': 'rgb(245,245,245)',
                'color': 'rgb(216,216,216)',
            },
            legendExist: false,
            // buffer
            maxCellCount: 0,
            maxCellValue: 0,
            columnSum: [],
            rowSum: [],

            enablePin: false,
            pinclasses: {},
        };
    },
    methods: {
        getHierarchy: function(hierarchy) {
            hierarchy = clone(hierarchy);
            const postorder = function(root, depth) {
                if (typeof(root) !== 'object') {
                    return {
                        name: root,
                        expand: false,
                        leafs: [root],
                        children: [],
                        depth: depth,
                    };
                }
                root.expand = false;
                root.depth = depth;
                let leafs = [];
                const newChildren = [];
                for (const child of root.children) {
                    const newChild = postorder(child, depth+1);
                    leafs = leafs.concat(newChild.leafs);
                    newChildren.push(newChild);
                }
                root.children = newChildren;
                root.leafs = leafs;
                return root;
            };
            for (let i=0; i<hierarchy.length; i++) {
                hierarchy[i] = postorder(hierarchy[i], 0);
            }
            return hierarchy;
        },
        getShowNodes: function(hierarchy) {
            let showNodes = [];
            const stack = Object.values(hierarchy).reverse();
            for (const node of stack) {
                node.pin = this.pinclasses[node.name]===true;
                node.virtual = false;
            }
            let lastNode = null;
            while (stack.length>0) {
                const top = stack.pop();
                showNodes.push(top);
                if (top.expand) {
                    for (let i=top.children.length-1; i>=0; i--) {
                        stack.push(top.children[i]);
                        top.children[i].pin = top.pin || this.pinclasses[top.children[i].name];
                    }
                }
                if (this.enablePin && !top.pin && (!lastNode || lastNode.pin)) {
                    showNodes.push({
                        children: [],
                        depth: 1000,
                        expand: false,
                        virtual: true,
                        name: '',
                        leafs: [''],
                        pin: false,
                    });
                }
                lastNode = top;
            }
            // filter out unpin classes
            const minDepth = Math.min(...showNodes.map((d) => d.depth));
            if (this.enablePin) {
                showNodes.forEach((d) => {
                    if (d.depth == 1000) {
                        d.depth = minDepth;
                    }
                });
                showNodes = showNodes.filter((d) => d.pin || d.virtual);
            }
            showNodes.forEach((node, i) => {
                node.textWidth = this.getTextWidth(node.name,
                    `${this.horizonTextAttrs['font-weight']} ${this.horizonTextAttrs['font-size']}px ${this.horizonTextAttrs['font-family']}`);
                node.textPosition = i*this.cellAttrs['size'];
                if (node.depth == minDepth) {
                    node.oldIndex = i;
                    node.oldPosition = i*this.cellAttrs['size'];
                    return;
                } else {
                    node.oldIndex = 0;
                    node.oldPosition = 0;
                }
                for (let j = i - 1; j >= 0; --j) {
                    if (showNodes[j].depth < showNodes[i].depth) {
                        node.oldIndex = j;
                        node.oldPosition = j*this.cellAttrs['size'];
                        break;
                    }
                }
            });
            console.log('showNodes', showNodes);
            // change depth
            const isTopNodes={};
            const showHierarchy = {};
            for (const node of showNodes) {
                showHierarchy[node.name] = true;
                for (const child of node.children) {
                    isTopNodes[child.name] = false;
                }
            }
            for (let i=0; i<showNodes.length; i++) {
                const node = showNodes[i];
                if (isTopNodes[node.name] !== false) {
                    node.depth = 0;
                    for (const child of node.children) {
                        child.depth = 1;
                    }
                }
            }
            return showNodes;
        },
        getDataAndRender: function() {
            if (this.confusionMatrix===undefined || this.labelHierarchy===undefined || this.classStatistics === undefined) {
                return;
            }
            // get nodes to show
            this.showNodes = this.getShowNodes(this.hierarchy);
            // get cells to render
            this.cells = [];
            this.classStatShow = [];
            this.classStatShow.push({
                val: this.statisticsInfo==='quantity'?d3.sum(this.classStatistics):d3.mean(this.classStatistics),
                row: -1.5,
                key: 'all',
            });
            this.classStatShow.push({
                val: -1,
                row: -2.2,
                key: 'info',
                text: this.statisticsInfo==='AP'?'precision':this.statisticsInfo==='AR'?'recall':'quantity',
            });
            this.maxCellValue = 0;
            this.maxCellCount = 0;
            this.columnSum = Array(this.showNodes.length).fill(0);
            this.rowSum = Array(this.showNodes.length).fill(0);
            for (let i=0; i<this.showNodes.length; i++) {
                if (this.showNodes[i].virtual) continue;
                const nodea = this.showNodes[i];
                let isBackground = false;
                let tmp = 0;
                for (const leaf of nodea.leafs) {
                    if (leaf === 'background') {
                        isBackground = true;
                        break;
                    }
                    tmp += this.classStatistics[this.name2index[leaf]];
                }
                if (!isBackground) {
                    this.classStatShow.push({
                        val: this.statisticsInfo==='quantity'?tmp:tmp / nodea.leafs.length,
                        row: i,
                        key: nodea.name,
                    });
                }
                const isHideNode = function(node) {
                    return node.expand===true && node.children.length>0;
                };
                for (let j=0; j<this.showNodes.length; j++) {
                    if (this.showNodes[j].virtual) continue;
                    const nodeb = this.showNodes[j];
                    const cell = {
                        key: nodea.name+','+nodeb.name,
                        info: this.getTwoCellConfusion(nodea, nodeb),
                        row: i,
                        column: j,
                        rowNode: nodea,
                        colNode: nodeb,
                    };
                    if (!isHideNode(this.showNodes[cell.column])) {
                        this.rowSum[i] += cell.info.count;
                    }
                    if (!isHideNode(this.showNodes[cell.row])) {
                        this.columnSum[j] += cell.info.count;
                    }
                    this.cells.push(cell);
                    if (!this.isHideCell(cell)) {
                        this.maxCellValue = Math.max(this.maxCellValue, cell.info.val);
                    }
                    if (!this.isHideCell(cell) && i!==this.showNodes.length-1 && j!==this.showNodes.length-1) {
                        this.maxCellCount = Math.max(this.maxCellCount, cell.info.count);
                    }
                }
            }
            this.render();
        },
        render: async function() {
            this.horizonTextinG = this.horizonTextG.selectAll('g.'+this.horizonTextAttrs['gClass']).data(this.showNodes, (d)=>d.name);
            this.verticalTextinG = this.verticalTextG.selectAll('g.'+this.verticalTextAttrs['gClass']).data(this.showNodes, (d)=>d.name);
            this.matrixCellsinG = this.matrixCellsG.selectAll('g.'+this.cellAttrs['gClass']).data(this.cells, (d)=>d.key);
            this.classStatinG = this.statG.selectAll('g.'+this.statAttrs['gClass']).data(this.classStatShow, (d)=>d.key);
            if (!this.legendExist) {
                this.drawLegend();
                this.legendExist = true;
            }
            await this.remove();
            this.transform();
            await this.update();
            await this.create();
        },
        create: async function() {
            const that = this;
            return new Promise((resolve, reject) => {
                const icony = that.cellAttrs['size']/2-that.horizonTextAttrs['font-size']/2+that.horizonTextAttrs['iconDy'];
                const horizonTextinG = that.horizonTextinG.enter()
                    .append('g')
                    .attr('class', that.horizonTextAttrs['gClass'])
                    .attr('opacity', 0)
                    .attr('transform', (d) => `translate(${d.depth*that.horizonTextAttrs['leftMargin']}, ${d.oldPosition})`)
                    .on('mouseover', function(e, d) {
                        that.mainG.select(`#class-pin-icon-${d.name}`).attr('opacity', 1);
                    })
                    .on('mouseout', function(e, d) {
                        that.mainG.select(`#class-pin-icon-${d.name}`).attr('opacity', that.pinclasses[d.name]?1:0);
                    });

                horizonTextinG.transition()
                    .duration(that.createDuration)
                    .attr('opacity', 1)
                    .attr('transform', (d) => `translate(${d.depth*that.horizonTextAttrs['leftMargin']}, ${d.textPosition})`)
                    .on('end', resolve);

                horizonTextinG.append('text')
                    .attr('x', (d) => (d.depth>0?0:that.horizonTextAttrs['font-size'] +
                        that.horizonTextAttrs['iconMargin'])+that.colorCellSize + that.colorCellMargin)
                    .attr('y', 0)
                    .attr('dy', that.cellAttrs['size']/2+that.horizonTextAttrs['font-size']/2)
                    .attr('text-anchor', that.horizonTextAttrs['text-anchor'])
                    .attr('font-size', that.horizonTextAttrs['font-size'])
                    .attr('font-weight', that.horizonTextAttrs['font-weight'])
                    .attr('font-family', that.horizonTextAttrs['font-family'])
                    .text((d) => d.name);

                horizonTextinG.append('rect')
                    .attr('x', 0)
                    .attr('y', 0)
                    .attr('width', (d) => that.maxHorizonTextWidth - (d.depth*that.horizonTextAttrs['leftMargin']))
                    .attr('height', that.cellAttrs['size'])
                    .attr('opacity', 0);

                horizonTextinG
                    .filter((d) => d.name.length > 0)
                    .append('image')
                    .attr('class', 'class-pin-icon')
                    .attr('id', (d) => `class-pin-icon-${d.name}`)
                    .attr('xlink:href', (d) => '/static/images/pin.svg')
                    .attr('x', (d) => (d.depth>0?0:that.horizonTextAttrs['font-size'] +
                        that.horizonTextAttrs['iconMargin'])+that.colorCellSize + that.colorCellMargin + d.textWidth)
                    .attr('y', icony)
                    .attr('width', that.horizonTextAttrs['font-size'])
                    .attr('height', that.horizonTextAttrs['font-size'])
                    .attr('cursor', 'pointer')
                    .attr('opacity', (d) => that.pinclasses[d.name]?1:0)
                    .on('click', function(e, d) {
                        that.pinclasses[d.name] = !that.pinclasses[d.name];
                        // eslint-disable-next-line no-invalid-this
                        d3.select(this).attr('opacity', (d) => that.pinclasses[d.name]?1:0);
                    });

                horizonTextinG
                    .append('image')
                    .attr('class', 'class-zoom')
                    .attr('xlink:href', (d) => '/static/images/'+(d.virtual?'3dot.svg':(d.children.length>1?'arrow.svg':'dot.svg')))
                    // .attr('xlink:href', (d) => '/static/images/'+(d.children.length>1?'arrow.svg':'dot.svg'))
                    .attr('x', 0)
                    .attr('y', icony)
                    .attr('opacity', (d)=>d.depth===0?1:0)
                    .attr('width', that.horizonTextAttrs['font-size'])
                    .attr('height', that.horizonTextAttrs['font-size'])
                    .attr('transform', (d) => `rotate(${d.expand?90:0} 
                        ${that.horizonTextAttrs['font-size']/2} ${icony+that.horizonTextAttrs['font-size']/2})`)
                    .attr('cursor', 'pointer')
                    .on('click', function(e, d) {
                        if (d.children.length===1) return;
                        d.expand = !d.expand;
                        that.legendExist = false;
                        that.getDataAndRender();
                    });

                horizonTextinG.filter((d) => d.children.length>0)
                    .append('path')
                    .attr('stroke', that.horizonTextAttrs['indent-line-stroke'])
                    .attr('stroke-width', that.horizonTextAttrs['indent-line-stroke-width'])
                    .attr('d', (d)=>{
                        // find expand child length
                        const stack = [d];
                        let expandlen = 0;
                        if (d.expand) {
                            while (stack.length > 0) {
                                const top = stack.pop();
                                for (const child of top.children) {
                                    if (child.children.length>0 && child.expand===true) {
                                        stack.push(child);
                                    }
                                    expandlen++;
                                }
                            }
                        }
                        const linelen = that.cellAttrs['size']*expandlen;
                        const x = that.horizonTextAttrs['font-size']/2;
                        return `M ${x} ${that.cellAttrs['size']} L ${x} ${that.cellAttrs['size']+linelen}`;
                    });

                const verticalTextinG = that.verticalTextinG.enter()
                    .append('g')
                    .attr('class', that.verticalTextAttrs['gClass'])
                    .attr('opacity', 0)
                    .attr('transform', (d) => `translate(${d.depth*that.verticalTextAttrs['leftMargin']}, ${d.oldPosition})`);

                verticalTextinG.transition()
                    .duration(that.createDuration)
                    .attr('transform', (d) => `translate(${d.depth*that.verticalTextAttrs['leftMargin']}, ${d.textPosition})`)
                    .attr('opacity', 1)
                    .on('end', resolve);

                verticalTextinG.append('text')
                    .attr('x', (d) => (d.depth>0?0:that.verticalTextAttrs['font-size'] +
                        that.verticalTextAttrs['iconMargin'])+that.colorCellSize + that.colorCellMargin)
                    .attr('y', 0)
                    .attr('dy', that.cellAttrs['size']/2+that.horizonTextAttrs['font-size']/2)
                    .attr('text-anchor', that.verticalTextAttrs['text-anchor'])
                    .attr('font-size', that.verticalTextAttrs['font-size'])
                    .attr('font-weight', that.verticalTextAttrs['font-weight'])
                    .attr('font-family', that.verticalTextAttrs['font-family'])
                    .text((d) => d.name);

                verticalTextinG
                    .append('image')
                    .attr('class', 'class-zoom')
                    .attr('xlink:href', (d) => '/static/images/'+(d.virtual?'3dot.svg':(d.children.length>1?'arrow.svg':'dot.svg')))
                    // .attr('xlink:href', (d) => '/static/images/'+(d.children.length>1?'arrow.svg':'dot.svg')))
                    .attr('x', 0)
                    .attr('y', icony)
                    .attr('opacity', (d)=>d.depth>0?0:1)
                    .attr('width', that.verticalTextAttrs['font-size'])
                    .attr('height', that.verticalTextAttrs['font-size'])
                    .attr('transform', (d) => `rotate(${d.expand?90:0} 
                        ${that.verticalTextAttrs['font-size']/2} ${icony+that.verticalTextAttrs['font-size']/2})`)
                    .attr('cursor', 'pointer')
                    .on('click', function(e, d) {
                        if (d.children.length===1) return;
                        d.expand = !d.expand;
                        that.legendExist = false;
                        that.getDataAndRender();
                    });

                verticalTextinG.filter((d) => d.children.length>0)
                    .append('path')
                    .attr('stroke', that.verticalTextAttrs['indent-line-stroke'])
                    .attr('stroke-width', that.verticalTextAttrs['indent-line-stroke-width'])
                    .attr('d', (d)=>{
                        // find expand child length
                        const stack = [d];
                        let expandlen = 0;
                        if (d.expand) {
                            while (stack.length > 0) {
                                const top = stack.pop();
                                for (const child of top.children) {
                                    if (child.children.length>0 && child.expand===true) {
                                        stack.push(child);
                                    }
                                    expandlen++;
                                }
                            }
                        }
                        const linelen = that.cellAttrs['size']*expandlen;
                        const x = that.verticalTextAttrs['font-size']/2;
                        return `M ${x} ${that.cellAttrs['size']} L ${x} ${that.cellAttrs['size']+linelen}`;
                    });

                const matrixCellsinG = that.matrixCellsinG.enter()
                    .append('g')
                    .attr('class', that.cellAttrs['gClass'])
                    .attr('opacity', 0)
                    .attr('cursor', (d)=>that.isHideCell(d)?'default':that.cellAttrs['cursor'])
                    .attr('transform', (d) => `translate(${d.column*that.cellAttrs['size']}, 
                        ${d.row*that.cellAttrs['size']})`)
                    .on('mouseover', function(e, d) {
                        if (that.isHideCell(d)) return;
                        if (that.matrixMode === 'direction' && d.info.direction !== undefined) {
                            // eslint-disable-next-line no-invalid-this
                            d3.select(this).select('.dir-circle')
                                .transition()
                                .duration(that.updateDuration)
                                .attr('transform', (d)=>`translate(${that.cellAttrs['size']/2},${that.cellAttrs['size']/2})
                                    scale(1)
                                    translate(${-that.cellAttrs['size']/2},${-that.cellAttrs['size']/2})`);
                            // eslint-disable-next-line no-invalid-this
                            d3.select(this).select('.dir-circle-ctx')
                                .transition()
                                .duration(that.updateDuration)
                                .attr('transform', (d)=>`translate(${that.cellAttrs['size']/2},${that.cellAttrs['size']/2})
                                    scale(1)
                                    translate(${-that.cellAttrs['size']/2},${-that.cellAttrs['size']/2})`);
                            for (let i = 0; i < 8; ++i) {
                                // eslint-disable-next-line no-invalid-this
                                d3.select(this).selectAll('.dir-'+i)
                                    .transition()
                                    .duration(that.updateDuration)
                                    .attr('transform', (d)=>`translate(${that.cellAttrs['size']/2},${that.cellAttrs['size']/2})
                                    scale(1)
                                    translate(${-that.cellAttrs['size']/2},${-that.cellAttrs['size']/2})
                                    rotate(${i*45} ${that.cellAttrs['size']/2} ${that.cellAttrs['size']/2})`);
                            }
                        } else if (that.matrixMode === 'size' && d.info.sizeCmp !== undefined) {
                            // eslint-disable-next-line no-invalid-this
                            d3.select(this).selectAll('.size-circle')
                                .transition()
                                .duration(that.updateDuration)
                                .attr('transform', `translate(${that.cellAttrs.size/2} ${that.cellAttrs.size/2})`);
                        }
                        // highlight row and column
                        that.matrixCellsG.append('rect')
                            .attr('class', `highlight`)
                            .attr('x', 0)
                            .attr('y', that.cellAttrs['size']*d.row)
                            .attr('width', that.cellAttrs['size']*that.showNodes.length)
                            .attr('height', that.cellAttrs['size'])
                            .attr('stroke', that.cellAttrs['stroke'])
                            .attr('stroke-width', '3px')
                            .attr('opacity', 1)
                            .attr('fill', 'none');
                        that.matrixCellsG.append('rect')
                            .attr('class', `highlight`)
                            .attr('x', that.cellAttrs['size']*d.column)
                            .attr('y', 0)
                            .attr('width', that.cellAttrs['size'])
                            .attr('height', that.cellAttrs['size']*that.showNodes.length)
                            .attr('stroke', that.cellAttrs['stroke'])
                            .attr('stroke-width', '3px')
                            .attr('opacity', 1)
                            .attr('fill', 'none');
                    })
                    .on('mouseout', function(e, d) {
                        // eslint-disable-next-line no-invalid-this
                        const cell = d3.select(this);
                        if (that.matrixMode === 'confusion') {
                            cell.select('rect').attr('stroke-width', that.cellAttrs['stroke-width']);
                        } else {
                            cell.select('rect').attr('stroke-width', 0);
                        }

                        if (that.matrixMode === 'direction' && d.info.direction !== undefined) {
                            // eslint-disable-next-line no-invalid-this
                            d3.select(this).select('.dir-circle')
                                .transition()
                                .duration(that.updateDuration)
                                .attr('transform', (d)=>`translate(${that.cellAttrs['size']/2},${that.cellAttrs['size']/2})
                                    scale(${that.sizeScale(d)})
                                    translate(${-that.cellAttrs['size']/2},${-that.cellAttrs['size']/2})`);
                            // eslint-disable-next-line no-invalid-this
                            d3.select(this).select('.dir-circle-ctx')
                                .transition()
                                .duration(that.updateDuration)
                                .attr('transform', (d)=>`translate(${that.cellAttrs['size']/2},${that.cellAttrs['size']/2})
                                    scale(1)
                                    translate(${-that.cellAttrs['size']/2},${-that.cellAttrs['size']/2})`);
                            for (let i = 0; i < 8; ++i) {
                                // eslint-disable-next-line no-invalid-this
                                d3.select(this).selectAll('.dir-'+i)
                                    .transition()
                                    .duration(that.updateDuration)
                                    .attr('transform', (d)=>`translate(${that.cellAttrs['size']/2},${that.cellAttrs['size']/2})
                                        scale(${that.sizeScale(d)})
                                        translate(${-that.cellAttrs['size']/2},${-that.cellAttrs['size']/2})
                                        rotate(${i*45} ${that.cellAttrs['size']/2} ${that.cellAttrs['size']/2})`);
                            }
                        } else if (that.matrixMode === 'size' && d.info.sizeCmp !== undefined) {
                            // eslint-disable-next-line no-invalid-this
                            d3.select(this).selectAll('.size-circle')
                                .transition()
                                .duration(that.updateDuration)
                                .attr('transform', (d) => `translate(${that.cellAttrs.size/2} ${that.cellAttrs.size/2}) scale(${that.sizeScale(d)})`);
                        }
                        that.matrixCellsG.selectAll(`.highlight`).remove();
                    });

                matrixCellsinG.transition()
                    .duration(that.createDuration)
                    .delay(that.createDuration)
                    .attr('opacity', (d)=>(that.isHideCell(d)?0:1))
                    .attr('transform', (d) => `translate(${d.column*that.cellAttrs['size']}, 
                        ${d.row*that.cellAttrs['size']})`)
                    .on('end', resolve);

                matrixCellsinG.append('rect')
                    .attr('x', 0)
                    .attr('y', 0)
                    .attr('width', that.cellAttrs['size'])
                    .attr('height', that.cellAttrs['size'])
                    .attr('stroke', that.cellAttrs['stroke'])
                    .attr('stroke-width', that.cellAttrs['stroke-width'])
                    .attr('opacity', that.matrixMode==='confusion'?1:0)
                    .attr('fill', (d)=>d.info.count===0?'rgb(255,255,255)':that.getFillColor(d))
                    .on('click', function(e, d) {
                        that.$emit('clickCell', d);
                        // if (that.matrixMode==='confusion') that.$emit('clickCell', d);
                    })
                    .on('mouseover', function(e, d) {
                        if (that.isHideCell(d)) return;
                        const labelTarget = [];
                        const predictTarget = [];
                        for (const name of d.rowNode.leafs) {
                            labelTarget.push(that.name2index[name]);
                        }
                        for (const name of d.colNode.leafs) {
                            predictTarget.push(that.name2index[name]);
                        }
                        that.$emit('hoverConfusion', labelTarget, predictTarget);
                    })
                    .on('mouseout', function(e, d) {
                        that.$emit('hoverConfusion');
                    });

                // normal mode: sign for empty cells
                matrixCellsinG.append('path')
                    .attr('id', 'empty-line')
                    .attr('d', `M ${that.cellAttrs['size']*0.25} ${that.cellAttrs['size']*0.25} 
                        L ${that.cellAttrs['size']*0.75} ${that.cellAttrs['size']*0.75}`)
                    .attr('stroke', that.cellAttrs['slash-text-stroke'])
                    .attr('opacity', (d)=>d.info.count===0&&that.matrixMode==='confusion'?1:0);
                matrixCellsinG.append('title')
                    .text((d)=>`count: ${d.info.count}`);

                if (that.matrixMode==='confusion') {
                    // remove direction
                    that._remove_direction(matrixCellsinG, resolve);
                    // remove size comparison
                    that._remove_sizeComparison(matrixCellsinG, resolve);
                    // set normal vis
                    that._create_normal(matrixCellsinG, resolve);
                } else if (that.matrixMode==='direction') {
                    // remove normal
                    that._remove_normal(matrixCellsinG, resolve);
                    // remove size comparison
                    that._remove_sizeComparison(matrixCellsinG, resolve);
                    // set direction vis
                    that._create_direction(matrixCellsinG, resolve);
                } else if (that.matrixMode==='size') {
                    // remove normal
                    that._remove_normal(matrixCellsinG, resolve);
                    // remove direction
                    that._remove_direction(matrixCellsinG, resolve);
                    // set size comparison vis
                    that._create_sizeComparison(matrixCellsinG, resolve);
                }

                // show matrix legend text
                if (that.horizonLegend.attr('opacity')==0) {
                    that.horizonLegend
                        .transition()
                        .duration(that.createDuration)
                        .attr('opacity', 1)
                        .on('end', resolve);
                    that.verticalLegend
                        .transition()
                        .duration(that.createDuration)
                        .attr('opacity', 1)
                        .on('end', resolve);
                }

                const classStatinG = that.classStatinG.enter()
                    .append('g')
                    .attr('opacity', 0)
                    .attr('class', that.statAttrs['gClass']);
                classStatinG.transition()
                    .duration(that.createDuration)
                    .attr('opacity', 1)
                    .on('end', resolve);
                classStatinG.filter((d) => d.val === -1).append('text')
                    .text((d) => d.text)
                    .attr('y', (d)=>that.cellAttrs.size*d.row+that.cellAttrs.size-that.statAttrs.height-3)
                    .attr('x', 0)
                    .attr('font-size', that.statAttrs['font-size'])
                    .attr('font-weight', that.statAttrs['font-weight'])
                    .attr('font-family', that.statAttrs['font-family']);
                classStatinG.filter((d) => d.val > -1).each(function(d) {
                    // eslint-disable-next-line no-invalid-this
                    const ge = d3.select(this);
                    ge.append('rect')
                        .attr('class', 'statBgRect')
                        .attr('x', 0)
                        .attr('y', (d)=>that.cellAttrs.size*d.row+that.cellAttrs.size-that.statAttrs.height)
                        .attr('width', that.statAttrs.width)
                        .attr('height', that.statAttrs.height)
                        .attr('fill', that.statAttrs['bg-color']);
                    const divi = that.statisticsInfo==='quantity'?d3.sum(that.classStatistics):1;
                    ge.append('rect')
                        .attr('class', 'statRect')
                        .attr('x', 0)
                        .attr('y', (d)=>that.cellAttrs.size*d.row+that.cellAttrs.size-that.statAttrs.height)
                        .attr('width', (d)=>that.statAttrs.width*d.val / divi)
                        .attr('height', that.statAttrs.height)
                        .attr('fill', that.statAttrs['color']);
                    ge.append('text')
                        .text(function(d) {
                            if (that.statisticsInfo !== 'quantity') return d.val.toFixed(3);
                            if (d.val < 1000) return String(d.val);
                            if (d.val < 1000000) return (d.val/1000).toFixed(0) + 'K';
                            return (d.val/1000000).toFixed(0) + 'M';
                        })
                        .attr('y', (d)=>that.cellAttrs.size*d.row+that.cellAttrs.size-that.statAttrs.height-3)
                        .attr('x', 0)
                        .attr('font-size', that.statAttrs['font-size'])
                        .attr('font-weight', that.statAttrs['font-weight'])
                        .attr('font-family', that.statAttrs['font-family']);
                });

                if ((that.horizonTextinG.enter().size() === 0) && (that.verticalTextinG.enter().size() === 0) &&
                    (that.matrixCellsinG.enter().size() === 0) && (that.classStatinG.enter().size() === 0)) {
                    resolve();
                }
            });
        },
        update: async function() {
            const that = this;
            return new Promise((resolve, reject) => {
                that.horizonTextinG
                    .transition()
                    .duration(that.updateDuration)
                    .attr('transform', (d) => `translate(${d.depth*that.horizonTextAttrs['leftMargin']}, ${d.textPosition})`)
                    .on('end', resolve);

                that.horizonTextinG.select('text')
                    .transition()
                    .duration(that.updateDuration)
                    .attr('x', (d) => (d.depth>0?0:that.horizonTextAttrs['font-size'] +
                        that.horizonTextAttrs['iconMargin'])+that.colorCellSize + that.colorCellMargin)
                    .on('end', resolve);

                const icony = that.cellAttrs['size']/2-that.horizonTextAttrs['font-size']/2+that.horizonTextAttrs['iconDy'];
                that.horizonTextinG.filter((d) => d.children.length>0)
                    .selectAll('image.class-zoom')
                    .attr('transform', (d) => `rotate(${d.expand?90:0} 
                        ${that.horizonTextAttrs['font-size']/2} ${icony+that.horizonTextAttrs['font-size']/2})`);

                that.horizonTextinG.selectAll('image.class-pin-icon')
                    .transition()
                    .duration(that.updateDuration)
                    .attr('x', (d) => (d.depth>0?0:that.horizonTextAttrs['font-size'] +
                        that.horizonTextAttrs['iconMargin'])+that.colorCellSize + that.colorCellMargin + d.textWidth)
                    .on('end', resolve);

                that.horizonTextinG.selectAll('image.class-zoom')
                    .transition()
                    .duration(that.updateDuration)
                    .attr('opacity', (d)=>d.depth===0?1:0)
                    .on('end', resolve);

                that.horizonTextinG.filter((d) => d.children.length>0)
                    .selectAll('path')
                    .attr('stroke', that.horizonTextAttrs['indent-line-stroke'])
                    .attr('stroke-width', that.horizonTextAttrs['indent-line-stroke-width'])
                    .transition()
                    .duration(that.updateDuration)
                    .attr('d', (d)=>{
                        // find expand child length
                        const stack = [d];
                        let expandlen = 0;
                        if (d.expand) {
                            while (stack.length > 0) {
                                const top = stack.pop();
                                for (const child of top.children) {
                                    if (child.children.length>0 && child.expand===true) {
                                        stack.push(child);
                                    }
                                    expandlen++;
                                }
                            }
                        }
                        const linelen = that.cellAttrs['size']*expandlen;
                        const x = that.horizonTextAttrs['font-size']/2;
                        return `M ${x} ${that.cellAttrs['size']} L ${x} ${that.cellAttrs['size']+linelen}`;
                    })
                    .on('end', resolve);

                that.horizonLegend
                    .transition()
                    .duration(that.updateDuration)
                    .attr('transform', `translate(-10,${that.matrixWidth/2}) rotate(270)`)
                    .on('end', resolve);

                that.verticalTextinG
                    .transition()
                    .duration(that.updateDuration)
                    .attr('transform', (d) => `translate(${d.depth*that.verticalTextAttrs['leftMargin']}, ${d.textPosition})`)
                    .on('end', resolve);

                that.verticalTextinG.select('text')
                    .transition()
                    .duration(that.updateDuration)
                    .attr('x', (d) => (d.depth>0?0:that.verticalTextAttrs['font-size'] +
                        that.verticalTextAttrs['iconMargin'])+that.colorCellSize + that.colorCellMargin)
                    .on('end', resolve);

                that.verticalTextinG.selectAll('image.class-zoom')
                    .transition()
                    .duration(that.updateDuration)
                    .attr('opacity', (d)=>d.depth===0?1:0)
                    .on('end', resolve);

                that.verticalLegend
                    .transition()
                    .duration(that.updateDuration)
                    .attr('transform', `translate(${that.maxHorizonTextWidth},${that.matrixWidth/2}) rotate(90)`)
                    .on('end', resolve);

                that.verticalTextinG.filter((d) => d.children.length>0)
                    .selectAll('image')
                    .attr('transform', (d) => `rotate(${d.expand?90:0} 
                        ${that.verticalTextAttrs['font-size']/2} ${icony+that.verticalTextAttrs['font-size']/2})`);

                that.verticalTextinG.filter((d) => d.children.length>0)
                    .selectAll('path')
                    .attr('stroke', that.verticalTextAttrs['indent-line-stroke'])
                    .attr('stroke-width', that.verticalTextAttrs['indent-line-stroke-width'])
                    .transition()
                    .duration(that.updateDuration)
                    .attr('d', (d)=>{
                        // find expand child length
                        const stack = [d];
                        let expandlen = 0;
                        if (d.expand) {
                            while (stack.length > 0) {
                                const top = stack.pop();
                                for (const child of top.children) {
                                    if (child.children.length>0 && child.expand===true) {
                                        stack.push(child);
                                    }
                                    expandlen++;
                                }
                            }
                        }
                        const linelen = that.cellAttrs['size']*expandlen;
                        const x = that.verticalTextAttrs['font-size']/2;
                        return `M ${x} ${that.cellAttrs['size']} L ${x} ${that.cellAttrs['size']+linelen}`;
                    })
                    .on('end', resolve);

                that.matrixCellsinG
                    .transition()
                    .duration(that.updateDuration)
                    // .delay(that.createDuration)
                    .attr('opacity', (d)=>(that.isHideCell(d)?0:1))
                    .attr('transform', (d) => `translate(${d.column*that.cellAttrs['size']}, 
                        ${d.row*that.cellAttrs['size']})`)
                    .on('end', resolve);

                that.matrixCellsinG.each(function(d) {
                    // eslint-disable-next-line no-invalid-this
                    d3.select(this).select('#empty-line')
                        .transition()
                        .duration(that.updateDuration)
                        .attr('opacity', (d)=>d.info.count===0&&that.matrixMode==='confusion'?1:0)
                        .on('end', resolve);
                    // eslint-disable-next-line no-invalid-this
                    d3.select(this).select('title')
                        .text((d)=>`count: ${d.info.count}`);
                });

                if (that.matrixMode==='confusion') {
                    // remove direction
                    that._remove_direction(that.matrixCellsinG, resolve);
                    // remove size comparison
                    that._remove_sizeComparison(that.matrixCellsinG, resolve);
                    // set normal vis
                    that._create_normal(that.matrixCellsinG, resolve);
                } else if (that.matrixMode==='direction') {
                    // remove normal
                    that._remove_normal(that.matrixCellsinG, resolve);
                    // remove size comparison
                    that._remove_sizeComparison(that.matrixCellsinG, resolve);
                    // set direction vis
                    that._create_direction(that.matrixCellsinG, resolve);
                } else if (that.matrixMode==='size') {
                    // remove normal
                    that._remove_normal(that.matrixCellsinG, resolve);
                    // remove direction
                    that._remove_direction(that.matrixCellsinG, resolve);
                    // set size comparison vis
                    that._create_sizeComparison(that.matrixCellsinG, resolve);
                }

                const divi = that.statisticsInfo==='quantity'?d3.sum(that.classStatistics):1;
                that.classStatinG.filter((d) => d.val > -1).each(function(d) {
                    // eslint-disable-next-line no-invalid-this
                    d3.select(this).select('.statBgRect')
                        .transition()
                        .duration(that.updateDuration)
                        .attr('y', (d)=>that.cellAttrs.size*d.row+that.cellAttrs.size-that.statAttrs.height)
                        .on('end', resolve);
                    // eslint-disable-next-line no-invalid-this
                    d3.select(this).select('.statRect')
                        .transition()
                        .duration(that.updateDuration)
                        .attr('width', (d)=>that.statAttrs.width*d.val / divi)
                        .attr('y', (d)=>that.cellAttrs.size*d.row+that.cellAttrs.size-that.statAttrs.height)
                        .on('end', resolve);
                    // eslint-disable-next-line no-invalid-this
                    d3.select(this).select('text')
                        .transition()
                        .duration(that.updateDuration)
                        .text(function(d) {
                            if (that.statisticsInfo !== 'quantity') return d.val.toFixed(3);
                            if (d.val < 1000) return String(d.val);
                            if (d.val < 1000000) return (d.val/1000).toFixed(0) + 'K';
                            return (d.val/1000000).toFixed(0) + 'M';
                        })
                        .attr('y', (d)=>that.cellAttrs.size*d.row+that.cellAttrs.size-that.statAttrs.height-3)
                        .on('end', resolve);
                });
                that.classStatinG.filter((d) => d.val === -1).select('text')
                    .transition()
                    .duration(that.updateDuration)
                    .text((d) => d.text)
                    .on('end', resolve);
            });
        },
        remove: async function() {
            const that = this;
            return new Promise((resolve, reject) => {
                that.horizonTextinG.exit()
                    .transition()
                    .duration(that.removeDuration)
                    .attr('opacity', 0)
                    .remove()
                    .on('end', resolve);

                that.verticalTextinG.exit()
                    .transition()
                    .duration(that.removeDuration)
                    .attr('opacity', 0)
                    .remove()
                    .on('end', resolve);

                that.matrixCellsinG.exit()
                    .transition()
                    .duration(that.removeDuration)
                    .attr('opacity', 0)
                    .remove()
                    .on('end', resolve);

                that.classStatinG.exit()
                    .transition()
                    .duration(that.removeDuration)
                    .attr('opacity', 0)
                    .remove()
                    .on('end', resolve);

                if ((that.horizonTextinG.exit().size() === 0) && (that.verticalTextinG.exit().size() === 0) &&
                    (that.matrixCellsinG.exit().size() === 0) && (that.classStatinG.exit().size() === 0)) {
                    resolve();
                }
            });
        },
        transform: async function() {
            const that = this;
            return new Promise((resolve, reject) => {
                // compute transform
                const svgRealWidth = that.$refs.svg.clientWidth;
                const svgRealHeight = that.$refs.svg.clientHeight;
                let shiftx = 0;
                let shifty = 0;
                let scale = Math.min(svgRealWidth/that.svgWidth/1.1, svgRealHeight/that.svgWidth/1.1);
                scale = Math.min(scale, 2);
                shiftx = (svgRealWidth-scale*that.svgWidth)/2;
                shifty = (svgRealHeight-scale*that.svgWidth)/2;
                that.mainG.transition()
                    .duration(that.transformDuration)
                    .attr('transform', `translate(${shiftx} ${shifty}) scale(${scale})`)
                    .on('end', resolve);
                that.horizonTextG.transition()
                    .duration(that.transformDuration)
                    .attr('transform', `translate(${that.leftCornerSize-that.maxHorizonTextWidth}, ${that.leftCornerSize+that.textMatrixMargin})`)
                    .on('end', resolve);
                that.verticalTextG.transition()
                    .duration(that.transformDuration)
                    .attr('transform', `translate(${that.leftCornerSize+that.textMatrixMargin}, ${that.leftCornerSize}) rotate(-90)`)
                    .on('end', resolve);
                that.matrixCellsG.transition()
                    .duration(that.transformDuration)
                    .attr('transform', `translate(${that.leftCornerSize+that.textMatrixMargin}, ${that.leftCornerSize+that.textMatrixMargin})`)
                    .on('end', resolve);
                that.statG.transition()
                    .duration(that.transformDuration)
                    .attr('transform', `translate(${that.leftCornerSize+that.textMatrixMargin+that.matrixWidth+20}, 
                        ${that.leftCornerSize+that.textMatrixMargin})`)
                    .on('end', resolve);
                that.legendG.transition()
                    .duration(that.transformDuration)
                    .attr('transform', `translate(${0},
                        ${that.leftCornerSize+that.textMatrixMargin+that.matrixWidth+5})`)
                    .attr('opacity', that.matrixMode==='confusion'?1:0)
                    .on('end', resolve);
            });
        },
        _remove_normal: function(g, resolve) {
            const that = this;
            g.each(function(d) {
                // eslint-disable-next-line no-invalid-this
                d3.select(this).select('rect')
                    .transition()
                    .duration(that.updateDuration)
                    .attr('fill', (d)=>d.info.count===0?'rgb(255,255,255)':that.getFillColor(d))
                    .attr('fill-opacity', 0)
                    .attr('opacity', 0)
                    .attr('stroke-width', '0px')
                    .on('end', resolve);
            });
        },
        _create_normal: function(g, resolve) {
            const that = this;
            g.each(function(d) {
                // eslint-disable-next-line no-invalid-this
                d3.select(this).select('rect')
                    .transition()
                    .duration(that.updateDuration)
                    .attr('fill', (d)=>d.info.count===0?'rgb(255,255,255)':that.getFillColor(d))
                    .attr('stroke', that.cellAttrs['stroke'])
                    .attr('stroke-width', that.cellAttrs['stroke-width'])
                    .attr('fill-opacity', 1)
                    .attr('opacity', 1)
                    .on('end', resolve);
            });
        },
        _remove_direction: function(g, resolve) {
            const that = this;
            g.selectAll('.dir-group')
                .transition()
                .duration(that.removeDuration)
                .attr('opacity', 0)
                .remove();
        },
        _create_direction: function(g, resolve) {
            const that = this;
            g.each(function(d) {
                // eslint-disable-next-line no-invalid-this
                d.hasDirectionElement = !d3.select(this)
                    .select('.dir-group')
                    .empty();
            });
            g.filter((d) => d.info.count === 0)
                .selectAll('.dir-group')
                .transition()
                .duration(that.removeDuration)
                .attr('opacity', 0)
                .remove();
            /*
            g.filter((d) => d.info.count>0 && !d.hasDirectionElement)
                .selectAll('polyline')
                .remove();
            */
            g.each(function(d) {
                if (d.info.count === 0) {
                    return;
                }
                // eslint-disable-next-line no-invalid-this
                let ge = d3.select(this);
                if (!d.hasDirectionElement) {
                    ge = ge.append('g')
                        .attr('class', 'dir-group')
                        .attr('opacity', 0);
                    ge.transition()
                        .duration(that.updateDuration)
                        .attr('opacity', 1);
                } else {
                    ge = ge.select('.dir-group');
                }

                if (!d.hasDirectionElement) {
                    ge.append('circle')
                        .attr('class', 'dir-circle-ctx')
                        .attr('id', `dir-ctxcircle`)
                        .attr('cx', that.cellAttrs['size']/2)
                        .attr('cy', that.cellAttrs['size']/2)
                        .attr('r', that.cellAttrs['size']/2)
                        .attr('fill', 'white');
                } else {
                    ge.select(`.dir-circle-ctx`)
                        .attr('cx', that.cellAttrs['size']/2)
                        .attr('cy', that.cellAttrs['size']/2)
                        .attr('r', that.cellAttrs['size']/2);
                }

                if (!d.hasDirectionElement) {
                    const circle = ge.append('circle')
                        .attr('class', 'dir-circle')
                        .attr('id', `dir-circle`)
                        .attr('cx', that.cellAttrs['size']/2)
                        .attr('cy', that.cellAttrs['size']/2)
                        .attr('r', d.info.direction===undefined||d.info.directionRatio[8]===0?0:
                            that.cellAttrs['size']*Math.max(1/36, 3/36*d.info.directionRatio[8]))
                        .attr('fill', that.cellAttrs['direction-color'])
                        .attr('transform', `translate(${that.cellAttrs['size']/2},${that.cellAttrs['size']/2})
                                            scale(${that.sizeScale(d)})
                                            translate(${-that.cellAttrs['size']/2},${-that.cellAttrs['size']/2})`);
                    circle
                        .transition()
                        .duration(that.updateDuration)
                        .attr('opacity', 1);

                    circle.on('click', function(e) {
                        if (that.matrixMode==='direction') {
                            const q = {
                                direction: [8],
                            };
                            that.$emit('clickCell', d, q);
                        }
                    })
                        .on('mouseover', function(e) {
                            if (that.isHideCell(d)) return;
                            // eslint-disable-next-line no-invalid-this
                            const cell = d3.select(this);
                            cell.select('rect').attr('stroke-width', '3px');
                            const labelTarget = [];
                            const predictTarget = [];
                            for (const name of d.rowNode.leafs) {
                                labelTarget.push(that.name2index[name]);
                            }
                            for (const name of d.colNode.leafs) {
                                predictTarget.push(that.name2index[name]);
                            }
                            that.$emit('hoverConfusion', labelTarget, predictTarget, 1+8);
                            ge.select(`#dir-circle`)
                                .attr('opacity', 1);
                            for (let j=0; j<8; j++) {
                                ge.selectAll(`.dir-${j}`)
                                    .attr('opacity', d.info.count===0||d.info.direction===undefined||d.info.direction[j]===0?0:0.5);
                            }
                        })
                        .on('mouseout', function(e) {
                            that.$emit('hoverConfusion', undefined);
                            ge.select(`#dir-circle`)
                                .attr('opacity', 1);
                            for (let j=0; j<8; j++) {
                                ge.selectAll(`.dir-${j}`)
                                    .attr('opacity', d.info.count===0||d.info.direction===undefined||d.info.direction[j]===0?0:1);
                            }
                        })
                        .attr('opacity', 1)
                        .on('end', resolve);
                    circle.append('title').text(`count: ${d.info.direction===undefined?0:d.info.direction[8]}`);
                } else {
                    const circle = ge.select(`#dir-circle`)
                        .attr('cx', that.cellAttrs['size']/2)
                        .attr('cy', that.cellAttrs['size']/2)
                        .attr('r', d.info.direction===undefined||d.info.directionRatio[8]===0?0:
                            that.cellAttrs['size']*Math.max(1/36, 3/36*d.info.directionRatio[8]));
                    circle.select('title').text(`count: ${d.info.direction===undefined?0:d.info.direction[8]}`);
                }
            });

            g.filter((d) => d.info.count>0).each(function(d) {
                // eslint-disable-next-line no-invalid-this
                const ge = d3.select(this).select('.dir-group');
                if (!d.hasDirectionElement) {
                    for (let i = 0; i < 8; ++i) {
                        const ele = ge.append('polyline')
                            .attr('class', 'dir-'+i)
                            .attr('id', `dir-${i}-0`)
                            .attr('points', `${that.cellAttrs['size']*14/36},${that.cellAttrs['size']/2}
                                ${d.info.direction===undefined?0:that.cellAttrs['size']*that.directionArrowScale(d.info.directionRatio[i])},
                                ${that.cellAttrs['size']/2}`)
                            .attr('fill', 'none')
                            .attr('stroke', that.cellAttrs['direction-color'])
                            .attr('stroke-width', 1)
                            .attr('transform', `translate(${that.cellAttrs['size']/2},${that.cellAttrs['size']/2})
                                                scale(${that.sizeScale(d)})
                                                translate(${-that.cellAttrs['size']/2},${-that.cellAttrs['size']/2})
                                                rotate(${i*45} ${that.cellAttrs['size']/2} ${that.cellAttrs['size']/2})`)
                            .attr('opacity', 0);
                        ele.on('click', function(e) {
                            if (that.matrixMode==='direction') {
                                const q = {
                                    direction: [i],
                                };
                                that.$emit('clickCell', d, q);
                            }
                        })
                            .on('mouseover', function(e) {
                                if (that.isHideCell(d)) return;
                                // eslint-disable-next-line no-invalid-this
                                const cell = d3.select(this);
                                cell.select('rect').attr('stroke-width', '3px');
                                const labelTarget = [];
                                const predictTarget = [];
                                for (const name of d.rowNode.leafs) {
                                    labelTarget.push(that.name2index[name]);
                                }
                                for (const name of d.colNode.leafs) {
                                    predictTarget.push(that.name2index[name]);
                                }
                                that.$emit('hoverConfusion', labelTarget, predictTarget, 1+i);
                                ge.select(`#dir-circle`)
                                    .attr('opacity', 0.5);
                                for (let j=0; j<8; j++) {
                                    ge.selectAll(`.dir-${j}`)
                                        .attr('opacity', d.info.count===0||d.info.direction===undefined||d.info.direction[j]===0?0:(j===i?1:0.5));
                                }
                            })
                            .on('mouseout', function(e) {
                                that.$emit('hoverConfusion', undefined);
                                ge.select(`#dir-circle`)
                                    .attr('opacity', 1);
                                for (let j=0; j<8; j++) {
                                    ge.selectAll(`.dir-${j}`)
                                        .attr('opacity', d.info.count===0||d.info.direction===undefined||d.info.direction[j]===0?0:1);
                                }
                            })
                            .attr('opacity', d.info.count===0||d.info.direction===undefined||d.info.direction[i]===0?0:1);
                        ele.append('title').text(`count: ${d.info.direction===undefined?0:d.info.direction[i]}\n`+
                            `ratio: ${d.info.direction===undefined?0:d.info.directionRatio[i]}`);
                        const posX = d.info.direction===undefined?0:that.cellAttrs['size']*that.directionArrowScale(d.info.directionRatio[i]);
                        const arrowLen = that.cellAttrs['size']/24;
                        const posXX = posX + arrowLen;
                        ge.append('polyline')
                            .attr('class', 'dir-'+i)
                            .attr('id', `dir-${i}-1`)
                            .attr('points', `${posXX},${that.cellAttrs['size']/2-arrowLen/2}
                                ${posX},${that.cellAttrs['size']/2}
                                ${posXX},${that.cellAttrs['size']/2+arrowLen/2}`)
                            .attr('fill', 'none')
                            .attr('stroke', that.cellAttrs['direction-color'])
                            .attr('stroke-width', 1)
                            .attr('transform', `translate(${that.cellAttrs['size']/2},${that.cellAttrs['size']/2})
                                                scale(${that.sizeScale(d)})
                                                translate(${-that.cellAttrs['size']/2},${-that.cellAttrs['size']/2})
                                                rotate(${i*45} ${that.cellAttrs['size']/2} ${that.cellAttrs['size']/2})`)
                            .attr('opacity', d.info.count===0||d.info.direction===undefined||d.info.direction[i]===0?0:1);
                    }
                } else {
                    for (let i = 0; i < 8; ++i) {
                        const ele = ge.select(`#dir-${i}-0`)
                            .attr('points', `${that.cellAttrs['size']*14/36},${that.cellAttrs['size']/2}
                                ${d.info.direction===undefined?0:that.cellAttrs['size']*that.directionArrowScale(d.info.directionRatio[i])},
                                ${that.cellAttrs['size']/2}`)
                            .attr('transform', `translate(${that.cellAttrs['size']/2},${that.cellAttrs['size']/2})
                                                scale(${that.sizeScale(d)})
                                                translate(${-that.cellAttrs['size']/2},${-that.cellAttrs['size']/2})
                                                rotate(${i*45} ${that.cellAttrs['size']/2} ${that.cellAttrs['size']/2})`)
                            .attr('opacity', d.info.count===0||d.info.direction===undefined||d.info.direction[i]===0?0:1);
                        ele.select('title').text(`count: ${d.info.direction===undefined?0:d.info.direction[i]}\n`+
                            `ratio: ${d.info.direction===undefined?0:d.info.directionRatio[i]}`);
                        const posX = d.info.direction===undefined?0:that.cellAttrs['size']*that.directionArrowScale(d.info.directionRatio[i]);
                        const arrowLen = that.cellAttrs['size']/24;
                        const posXX = posX + arrowLen;
                        ge.select(`#dir-${i}-1`)
                            .attr('points', `${posXX},${that.cellAttrs['size']/2-arrowLen/2}
                                ${posX},${that.cellAttrs['size']/2}
                                ${posXX},${that.cellAttrs['size']/2+arrowLen/2}`)
                            .attr('transform', `translate(${that.cellAttrs['size']/2},${that.cellAttrs['size']/2})
                                                scale(${that.sizeScale(d)})
                                                translate(${-that.cellAttrs['size']/2},${-that.cellAttrs['size']/2})
                                                rotate(${i*45} ${that.cellAttrs['size']/2} ${that.cellAttrs['size']/2})`)
                            .attr('opacity', d.info.count===0||d.info.direction===undefined||d.info.direction[i]===0?0:1);
                    }
                }
            });
        },
        _remove_sizeComparison: function(g, resolve) {
            const that = this;
            g.selectAll('.size-circle')
                .transition()
                .duration(that.updateDuration)
                .attr('opacity', 0)
                .remove()
                .on('end', resolve);
            g.selectAll('.dist')
                .transition()
                .duration(that.updateDuration)
                .attr('opacity', 0)
                .remove()
                .on('end', resolve);
        },
        _create_sizeComparison: function(g, resolve) {
            const that = this;
            g.each(function(d) {
                // eslint-disable-next-line no-invalid-this
                d.hasPieElement = !d3.select(this)
                    .select('.size-circle')
                    .empty();
            });
            g.filter((d) => d.info.count === 0 || (d.info.count>0&&d.info.sizeCmp!==undefined&&!d.hasPieElement))
                .selectAll('.size-circle')
                .transition()
                .duration(that.removeDuration)
                .attr('opacity', 0)
                .remove();

            for (let i = 0; i < 3; ++i) {
                g.filter((d) => d.info.count>0&&d.info.sizeCmp!==undefined).each(function(d) {
                    // eslint-disable-next-line no-invalid-this
                    const ge = d3.select(this);
                    if (!d.hasPieElement) {
                        const ele = ge.append('path')
                            .attr('class', 'size-circle')
                            .attr('id', `size-circle-${i}`)
                            .attr('transform', (d) => `translate(${that.cellAttrs.size/2} ${that.cellAttrs.size/2}) scale(${that.sizeScale(d)})`)
                            .attr('fill', that.cellAttrs['size-color'][i])
                            .attr('fill-opacity', d.info.sizeCmp[i]===0?0:1)
                            .attr('opacity', 0);

                        ele
                            .attr('d', d3.arc().innerRadius(0).outerRadius(that.getCircleRadius(d))
                                .startAngle(d.info.sizeCmpAngle[i]).endAngle(d.info.sizeCmpAngle[i+1])())
                            .on('click', function(e) {
                                if (that.matrixMode==='size') {
                                    const q = {
                                        size_comparison: [i],
                                    };
                                    that.$emit('clickCell', d, q);
                                }
                            })
                            .on('mouseover', function(e) {
                                if (that.isHideCell(d)) return;
                                // eslint-disable-next-line no-invalid-this
                                const cell = d3.select(this);
                                cell.select('rect').attr('stroke-width', '3px');
                                const labelTarget = [];
                                const predictTarget = [];
                                for (const name of d.rowNode.leafs) {
                                    labelTarget.push(that.name2index[name]);
                                }
                                for (const name of d.colNode.leafs) {
                                    predictTarget.push(that.name2index[name]);
                                }
                                that.$emit('hoverConfusion', labelTarget, predictTarget, 1+that.directionLen+i);
                                for (let j=0; j<3; j++) {
                                    ge.select(`#size-circle-${j}`).attr('opacity', j===i?1:0.5);
                                }
                            })
                            .on('mouseout', function(e) {
                                that.$emit('hoverConfusion', undefined);
                                for (let j=0; j<3; j++) {
                                    ge.select(`#size-circle-${j}`).attr('opacity', 1);
                                }
                            });

                        ele.transition()
                            .duration(that.updateDuration)
                            .attr('opacity', 1)
                            .on('end', resolve);
                        ele.append('title').text((d)=>`count: ${d.info.sizeCmp[i]}`);
                    } else {
                        const ele = ge.select(`#size-circle-${i}`)
                            .attr('transform', (d) => `translate(${that.cellAttrs.size/2} ${that.cellAttrs.size/2}) scale(${that.sizeScale(d)})`)
                            .attr('fill', that.cellAttrs['size-color'][i])
                            .attr('fill-opacity', d.info.sizeCmp[i]===0?0:1)
                            .transition()
                            .duration(that.updateDuration)
                            .attr('d', d3.arc().innerRadius(0).outerRadius(that.getCircleRadius(d))
                                .startAngle(d.info.sizeCmpAngle[i]).endAngle(d.info.sizeCmpAngle[i+1])());
                        ele.select('title').text(`count: ${d.info.sizeCmp[i]}`);
                    }
                });
            }
        },
        showClass: function(name) {
            const dfs = function(root) {
                if (root.name === name && root.children.length!==1) {
                    root.expand = true;
                    return true;
                }
                for (const child of root.children) {
                    if (dfs(child)) {
                        if (root.children.length>1) root.expand = true;
                        return true;
                    }
                }
                root.expand = false;
                return false;
            };
            for (const root of this.hierarchy) {
                dfs(root);
            }

            this.getDataAndRender();
        },
        getTwoCellConfusion: function(nodea, nodeb) {
            const infoMap = {
                'count': 0,
                'val': 0,
                'sizeCmp': [0, 0, 0],
            };
            if (nodea.virtual || nodeb.virtual) {
                return infoMap;
            }
            if (this.matrixMode==='direction') {
                infoMap['direction'] = Array(9).fill(0);
                infoMap['directionRatio'] = Array(9).fill(0);
            }
            for (const leafa of nodea.leafs) {
                for (const leafb of nodeb.leafs) {
                    infoMap.count += this.baseMatrix[0][this.name2index[leafa]][this.name2index[leafb]];
                    if (this.matrixMode==='direction') {
                        for (let i = 0; i < 9; ++i) {
                            infoMap.direction[i] += this.baseMatrix[this.baseMatrix.length-1][this.name2index[leafa]][this.name2index[leafb]][i];
                        }
                    }
                    infoMap.sizeCmp[1] += this.baseMatrix[this.baseMatrix.length-2][this.name2index[leafa]][this.name2index[leafb]][0];
                    infoMap.sizeCmp[2] += this.baseMatrix[this.baseMatrix.length-2][this.name2index[leafa]][this.name2index[leafb]][1];
                }
            }
            if (this.matrixMode==='direction') {
                const dirSum = d3.sum(infoMap.direction) - infoMap.direction[8];
                for (let i = 0; i < 8; ++i) {
                    if (infoMap.direction[i] > 0) {
                        infoMap.directionRatio[i] = 0.05;
                        if (infoMap.direction[i] > 30 && infoMap.direction[i]/dirSum > 0.3) {
                            infoMap.directionRatio[i] = Number((infoMap.direction[i]/dirSum).toFixed(3));
                        }
                    }
                }
                if (infoMap.direction[8] > 0) {
                    if (dirSum > 0) infoMap.directionRatio[8] = Math.min(1, infoMap.direction[8]/dirSum);
                    else infoMap.directionRatio[8] = 1;
                }
            }
            infoMap.sizeCmp[0] = infoMap.count - infoMap.sizeCmp[1] - infoMap.sizeCmp[2];
            if (infoMap.count > 0) {
                infoMap.sizeCmpAngle = [0];
                for (let i = 0; i < 3; ++i) {
                    infoMap.sizeCmpAngle.push(infoMap.sizeCmpAngle[i] + infoMap.sizeCmp[i]/infoMap.count * 2 * Math.PI);
                }
            }
            infoMap.val = infoMap.count;
            return infoMap;
        },
        drawLegend: function() {
            const that = this;
            // https://observablehq.com/@d3/color-legend
            const drawLegend = function({
                color,
                title,
                tickSize = 6,
                width = 320,
                height = 44 + tickSize,
                marginTop = 18,
                marginRight = 0,
                marginBottom = 16 + tickSize,
                marginLeft = 0,
                ticks = width / 64,
                tickFormat,
                tickValues,
            } = {}) {
                const ramp = function(color, n = 256) {
                    const canvas = that.drawLegend.canvas || (that.drawLegend.canvas = document.createElement('canvas'));
                    canvas.width = n;
                    canvas.height = 1;
                    const context = canvas.getContext('2d');
                    for (let i = 0; i < n; ++i) {
                        context.fillStyle = color(i / (n - 1));
                        context.fillRect(i, 0, 1, 1);
                    }
                    return canvas;
                };
                const tickAdjust = (g) => g.selectAll('.tick line').attr('y1', marginTop + marginBottom - height);
                let x;

                // Continuous
                if (color.interpolator) {
                    x = Object.assign(color.copy()
                        .interpolator(d3.interpolateRound(marginLeft, width - marginRight)),
                    {range() {
                        return [marginLeft, width - marginRight];
                    }});

                    that.legendG.append('image')
                        .attr('x', marginLeft)
                        .attr('y', marginTop)
                        .attr('width', width - marginLeft - marginRight)
                        .attr('height', height - marginTop - marginBottom)
                        .attr('preserveAspectRatio', 'none')
                        .attr('xlink:href', ramp(color.interpolator()).toDataURL());

                    // scaleSequentialQuantile doesn’t implement ticks or tickFormat.
                    if (!x.ticks) {
                        if (tickValues === undefined) {
                            const n = Math.round(ticks + 1);
                            tickValues = d3.range(n).map((i) => d3.quantile(color.domain(), i / (n - 1)));
                        }
                        if (typeof tickFormat !== 'function') {
                            tickFormat = d3.format(tickFormat === undefined ? ',f' : tickFormat);
                        }
                    }
                }
                that.legendG.append('g')
                    .attr('transform', `translate(0,${height - marginBottom})`)
                    .call(d3.axisBottom(x)
                        .ticks(ticks, typeof tickFormat === 'string' ? tickFormat : undefined)
                        .tickFormat(typeof tickFormat === 'function' ? tickFormat : undefined)
                        .tickSize(tickSize)
                        .tickValues(tickValues))
                    .call(tickAdjust)
                    .call((g) => g.select('.domain').remove())
                    .call((g) => g.append('text')
                        .attr('x', marginLeft)
                        .attr('y', marginTop + marginBottom - height - 6)
                        .attr('fill', 'currentColor')
                        .attr('text-anchor', 'start')
                        .attr('font-weight', 'bold')
                        .attr('class', 'title')
                        .text(title));
                that.legendG.attr('pointer-events', 'none');
                return that.legendG.node();
            };
            this.legendG.selectAll('*').remove();
            drawLegend(
                {
                    color: this.colorScaleDefault,
                    title: this.normalizationMode==='total'?'Number':'Probability',
                    width: this.legendWidth,
                    ticks: 6,
                },
            );
        },
        isHideCell: function(cell) {
            const isHideNode = function(node) {
                return node.expand===true && node.children.length>0;
            };
            return isHideNode(this.showNodes[cell.row]) || isHideNode(this.showNodes[cell.column]);
        },
        colorScaleCOCO: function(num) {
            const colorRange = [d3.rgb('rgb(232,243,250)'), d3.rgb('rgb(18,131,192)')];
            if (this.normalizationMode !== 'total') {
                const ratio2color = d3.scaleSequential([0, 1], colorRange).clamp(true);
                const v1 = 0.1;
                const v2 = 0.2;
                if (num <= v1) {
                    return d3.scaleSequential([0, v1], [ratio2color(0), ratio2color(0.3)]).clamp(true)(num);
                } else if (num <= v2) {
                    return d3.scaleSequential([v1, v2], [ratio2color(0.3), ratio2color(0.4)]).clamp(true)(num);
                } else {
                    return d3.scaleSequential([v2, 1], [ratio2color(0.4), ratio2color(1)]).clamp(true)(num);
                }
            } else {
                const ratio2color = d3.scaleSequential([0, 1], colorRange).clamp(true);
                const v1 = 5000;
                const v2 = 10000;
                if (num <= v1) {
                    return d3.scaleSequential([0, v1], [ratio2color(0), ratio2color(0.3)]).clamp(true)(num);
                } else if (num <= v2) {
                    return d3.scaleSequential([v1, v2], [ratio2color(0.3), ratio2color(0.7)]).clamp(true)(num);
                } else {
                    return d3.scaleSequential([v2, this.maxCellValue], [ratio2color(0.7), ratio2color(1)]).clamp(true)(num);
                }
            }
        },
        colorScaleiSAID: function(num) {
            const colorRange = [d3.rgb('rgb(232,243,250)'), d3.rgb('rgb(18,131,192)')];
            if (this.normalizationMode !== 'total') {
                const ratio2color = d3.scaleSequential([0, 1], colorRange).clamp(true);
                const v1 = 0.065;
                const v2 = 0.2;
                if (num <= v1) {
                    return d3.scaleSequential([0, v1], [ratio2color(0), ratio2color(0.1)]).clamp(true)(num);
                } else if (num <= v2) {
                    return d3.scaleSequential([v1, v2], [ratio2color(0.4), ratio2color(0.5)]).clamp(true)(num);
                } else {
                    return d3.scaleSequential([v2, 1], [ratio2color(0.6), ratio2color(1)]).clamp(true)(num);
                }
            } else {
                const ratio2color = d3.scaleSequential([0, 1], colorRange).clamp(true);
                const v1 = 5000;
                const v2 = 10000;
                if (num <= v1) {
                    return d3.scaleSequential([0, v1], [ratio2color(0), ratio2color(0.3)]).clamp(true)(num);
                } else if (num <= v2) {
                    return d3.scaleSequential([v1, v2], [ratio2color(0.3), ratio2color(0.7)]).clamp(true)(num);
                } else {
                    return d3.scaleSequential([v2, this.maxCellValue], [ratio2color(0.7), ratio2color(1)]).clamp(true)(num);
                }
            }
        },
        getFillColor: function(d) {
            let num;
            if (this.normalizationMode === 'total') num = d.info.count;
            else if (this.normalizationMode === 'row') num = d.info.count / this.rowSum[d.row];
            else num = d.info.count / this.columnSum[d.column];

            if (this.dataName === 'COCO') {
                return this.colorScaleCOCO(num);
            } else if (this.dataName === 'iSAID') {
                return this.colorScaleiSAID(num);
            } else return this.colorScaleDefault(num);
        },
        getCircleRadius: function(d) {
            const radius = this.cellAttrs['size']*4/12;
            return radius;
        },
        sizeScaleDefault: function(num) {
            if (num === 0) return 0;
            if (this.normalizationMode === 'total') return d3.scaleLinear([0, Math.sqrt(this.maxCellCount)], [0.2, 1])(Math.sqrt(num));
            else return d3.scaleLinear([0, 1], [0.2, 1])(Math.sqrt(num));
        },
        sizeScaleCOCO: function(num, d) {
            if (num === 0) return 0;
            if (this.normalizationMode === 'total') {
                if (num > 2000 || num === this.maxCellCount) return 1;
                if (num < 50) return 0.2;
                const maxVis = 1500;
                const minVis = 150;
                if (num > maxVis || d.row === d.column) return 0.9;
                if (this.matrixMode === 'direction') {
                    if (num < minVis) return 0.6;
                    else return d3.scaleLinear([Math.sqrt(minVis), Math.sqrt(maxVis)], [0.6, 0.9])(Math.sqrt(num));
                } else {
                    if (num < minVis) return d3.scaleLinear([Math.sqrt(50), Math.sqrt(minVis)], [0.35, 0.5])(Math.sqrt(num));
                    else return d3.scaleLinear([Math.sqrt(minVis), Math.sqrt(maxVis)], [0.5, 0.8])(Math.sqrt(num));
                }
            } else {
                const v1 = 0.1;
                const v2 = 0.2;
                if (num <= v1) {
                    return d3.scaleLinear([0, v1], [0.2, 0.6]).clamp(true)(num);
                } else if (num <= v2) {
                    return d3.scaleLinear([v1, v2], [0.6, 0.8]).clamp(true)(num);
                } else {
                    return d3.scaleLinear([v2, 1], [0.8, 1]).clamp(true)(num);
                }
            }
        },
        sizeScaleiSAID: function(num, d) {
            if (num === 0) return 0;
            if (this.normalizationMode === 'total') {
                if (num === this.maxCellCount || num > 50000) return 1;
                let scale = 0;
                if (num <= 2000) {
                    scale = d.column===d.row ? 0.2 : d3.scaleLinear([Math.sqrt(0), Math.sqrt(2000)], [0.2, 0.3])(Math.sqrt(num));
                } else if (num > 2000 && num <= 4800) {
                    scale = d3.scaleLinear([Math.sqrt(2000), Math.sqrt(4800)], [0.2, 0.4])(Math.sqrt(num));
                } else if (num > 4800 && num <= 12000) {
                    scale = d3.scaleLinear([Math.sqrt(4800), Math.sqrt(12000)], [0.6, 0.75])(Math.sqrt(num));
                } else if (num > 12000 && num <= 40000) {
                    scale = d3.scaleLinear([Math.sqrt(12000), Math.sqrt(40000)], [0.75, 0.9])(Math.sqrt(num));
                } else if (num > 40000 && num <= 50000) {
                    scale = 0.9;
                } else {
                    scale = 1;
                }
                return (d.column===d.row && scale<0.7) ? Math.min(scale*2, 0.7) : scale;
            } else {
                const v1 = 0.065;
                const v2 = 0.2;
                if (num <= v1) {
                    return d3.scaleLinear([0, v1], [0.2, 0.6]).clamp(true)(num);
                } else if (num <= v2) {
                    return d3.scaleLinear([v1, v2], [0.6, 0.7]).clamp(true)(num);
                } else {
                    return d3.scaleLinear([v2, 1], [0.7, 1]).clamp(true)(num);
                }
            }
        },
        sizeScale: function(d) {
            let num;
            if (this.normalizationMode === 'total') num = d.info.count;
            else if (this.normalizationMode === 'row') num = d.info.count / this.rowSum[d.row];
            else num = d.info.count / this.columnSum[d.column];

            if (this.dataName === 'COCO') {
                return this.sizeScaleCOCO(num, d);
            } else if (this.dataName === 'iSAID') {
                return this.sizeScaleiSAID(num, d);
            } else return this.sizeScaleDefault(num);
        },
        directionArrowScale: function(x) {
            if (x < 0.05 + 0.001) return 10/36;
            return Math.max(2/36, d3.scaleLinear([0.3, 1], [9/36, -1/2])(x));
        },
        updateColors: function(colors) {
            this.cellAttrs['size-color'] = colors;
            for (let i = 0; i < 3; ++i) {
                this.matrixCellsG.selectAll(`#size-circle-${i}`)
                    .attr('fill', colors[i]);
            }
        },
    },
};
</script>
