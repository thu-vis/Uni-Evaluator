<template>
    <div class="legends-content">
        <svg id="legends-svg" width="100%" height="100%" ref="svg">
            <defs>
                <!-- arrowhead marker definition -->
                <marker id="arrow" viewBox="0 0 4 4" refX="2" refY="2"
                    markerWidth="3" markerHeight="3"
                    orient="auto-start-reverse">
                <path d="M 0 0 L 4 2 L 0 4 z" />
                </marker>
            </defs>
            <g id="main-g" transform="translate(0,0)">
                <g id="gt-pr-g"></g>
                <g id="size-bias-g"></g>
                <g id="pos-shift-g"></g>
            </g>
        </svg>
    </div>
</template>

<script>
import {mapGetters} from 'vuex';
import * as d3 from 'd3';
import Util from './Util.vue';
import GlobalVar from './GlovalVar.vue';
window.d3 = d3;

export default {
    name: 'Legends',
    mixins: [Util, GlobalVar],
    props: {
    },
    computed: {
        ...mapGetters(['labelnames']),
        svg: function() {
            return d3.select('#legends-svg');
        },
        mainG: function() {
            return this.svg.select('g#main-g');
        },
        prG: function() {
            return this.svg.select('g#gt-pr-g');
        },
        posG: function() {
            return this.svg.select('g#pos-shift-g');
        },
        sizeG: function() {
            return this.svg.select('g#size-bias-g');
        },
    },
    watch: {
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
            legendR: 70,
            sizeR: 45,
            imgWidth: 40,
            imgHeight: 40,
            legendSpace: 200,
            sizeColors: ['rgb(216,216,216)', 'rgb(255,142,146)', 'rgb(94,197,154)'],
            gtColor: 'rgb(27, 251, 254)',
            prColor: 'rgb(253, 6, 253)',
            sizeAngles: [0, 0.45 * 2 * Math.PI, 0.8 * 2 * Math.PI, 2 * Math.PI],
            posRatio: [0.7, 0.4, 0.5, 0.6, 0.35, 0.5, 0.9, 0.35],
            sizeText: [
                'predictions with precise position',
                'predictions larger than groundtruth',
                'predictions smaller than groundtruth',
            ],
            // fontFamily: 'Comic Sans MS',
            fontWeight: 'normal',
            fontSize: 16,
            posText1: 'predictions with precise position',
            posText2: 'predictions shifted in specific direction',
            lineColor: 'rgb(67,67,67)',
            directionColor: 'rgb(127,127,127)',
            boxWidth: 4,
            lineWidth: 1.5,
        };
    },
    methods: {
        render: async function() {
            const maxTextLength = this.getTextWidth('Predictions shifted in',
                `${this.fontWeight} ${this.fontSize}px Arial`);
            const sizeTranslate = 170;
            const posTranslate = sizeTranslate + 165;
            const smallerStart = 10;
            const largerStart = -55;
            const dirPreciseStart = this.legendR*0.8;
            const shiftStart = this.legendR*3/2+10;
            const imgStart = this.legendR * 2 + 10;
            const lineEnd = imgStart - 15;
            const imgHeight = this.imgHeight;
            const imgWidth = this.imgWidth;
            const textStart = imgStart + imgWidth + 15;
            const svgRealWidth = this.$refs.svg.clientWidth;
            const svgRealHeight = this.$refs.svg.clientHeight;
            const svgWidth = textStart + maxTextLength + (this.legendR - this.sizeR);
            const svgHeight = 15 + posTranslate + shiftStart + imgHeight/2;
            let path;
            // gt and pr
            this.prG.attr('transform', 'translate(75,5)');
            this.prG.append('svg:image')
                .attr('x', 0)
                .attr('y', 0)
                .attr('width', imgWidth)
                .attr('height', imgHeight)
                .attr('xlink:href', '/static/images/example.png');
            this.prG.append('rect')
                .attr('fill', 'none')
                .attr('stroke', this.gtColor)
                .attr('stroke-width', this.boxWidth)
                .attr('x', 0)
                .attr('y', 0)
                .attr('width', imgWidth)
                .attr('height', imgHeight);
            this.prG.append('rect')
                .attr('fill', 'none')
                .attr('stroke', this.prColor)
                .attr('stroke-width', this.boxWidth)
                .attr('x', 15)
                .attr('y', 30)
                .attr('width', imgWidth)
                .attr('height', imgHeight-20);
            this.prG.append('polyline')
                .attr('points', `${imgWidth+5},${imgHeight/2-10}
                    ${textStart-85},${imgHeight/2-10}`)
                .attr('fill', 'none')
                .attr('stroke', this.lineColor)
                .attr('stroke-width', this.lineWidth);
            this.prG.append('polyline')
                .attr('points', `${imgWidth+20},${imgHeight-5}
                    ${textStart-85},${imgHeight-5}`)
                .attr('fill', 'none')
                .attr('stroke', this.lineColor)
                .attr('stroke-width', this.lineWidth);
            this.prG.append('text')
                .text('Ground truth')
                .attr('x', textStart-75)
                .attr('y', imgHeight/2-5)
                .attr('font-size', this.fontSize)
                .attr('font-weight', this.fontWeight);
            this.prG.append('text')
                .text('Prediction')
                .attr('x', textStart-75)
                .attr('y', imgHeight)
                .attr('font-size', this.fontSize)
                .attr('font-weight', this.fontWeight);
            // size legend
            // circle
            this.sizeG.attr('transform', `translate(0, ${sizeTranslate})`);
            for (let i = 0; i < 3; ++i) {
                this.sizeG.append('path')
                    .attr('class', 'size-circle')
                    .attr('transform', `translate(${this.legendR} ${this.legendR})`)
                    .attr('fill', this.sizeColors[i])
                    .attr('d', d3.arc().innerRadius(0).outerRadius(this.sizeR)
                        .startAngle(this.sizeAngles[i]).endAngle(this.sizeAngles[i+1])());
            }
            // smaller
            // this.sizeG.append('polyline')
            //     .attr('points', `${this.legendR*0.9},${this.legendR*0.66}
            //         ${this.legendR},${smallerStart}
            //         ${lineEnd},${smallerStart}`)
            //     .attr('fill', 'none')
            //     .attr('stroke', this.lineColor)
            //     .attr('stroke-width', this.lineWidth);
            path = d3.path();
            path.moveTo(this.legendR*0.8, this.legendR*0.66);
            path.quadraticCurveTo(this.legendR*0.8, smallerStart, lineEnd, smallerStart);
            this.sizeG.append('path')
                .attr('d', path.toString())
                .style('fill', 'none')
                .style('stroke', this.lineColor)
                .style('stroke-width', this.lineWidth);
            this.sizeG.append('svg:image')
                .attr('x', imgStart)
                .attr('y', smallerStart-imgHeight/2)
                .attr('width', imgWidth)
                .attr('height', imgHeight)
                .attr('xlink:href', '/static/images/example.png');
            this.sizeG.append('rect')
                .attr('fill', 'none')
                .attr('stroke', this.gtColor)
                .attr('stroke-width', this.boxWidth)
                .attr('x', imgStart)
                .attr('y', smallerStart-imgHeight/2)
                .attr('width', imgWidth)
                .attr('height', imgHeight);
            this.sizeG.append('rect')
                .attr('fill', 'none')
                .attr('stroke', this.prColor)
                .attr('stroke-width', this.boxWidth)
                .attr('x', imgStart+10)
                .attr('y', smallerStart-imgHeight/2+5)
                .attr('width', imgWidth-15)
                .attr('height', imgHeight-10);
            this.sizeG.append('text')
                .text('Predictions smaller')
                .attr('y', smallerStart-5)
                .attr('x', textStart)
                .attr('font-size', this.fontSize)
                .attr('font-weight', this.fontWeight);
            this.sizeG.append('text')
                .text('than ground truth')
                .attr('y', smallerStart+11)
                .attr('x', textStart)
                .attr('font-size', this.fontSize)
                .attr('font-weight', this.fontWeight);
            // larger
            // this.sizeG.append('polyline')
            //     .attr('points', `${this.legendR*0.6},${this.legendR*1.2}
            //         ${this.legendR},${largerStart}
            //         ${lineEnd},${largerStart}`)
            //     .attr('fill', 'none')
            //     .attr('stroke', this.lineColor)
            //     .attr('stroke-width', this.lineWidth);
            path = d3.path();
            path.moveTo(this.legendR*0.6, this.legendR*1.2);
            path.quadraticCurveTo(this.legendR*0.6, largerStart, lineEnd, largerStart);
            this.sizeG.append('path')
                .attr('d', path.toString())
                .style('fill', 'none')
                .style('stroke', this.lineColor)
                .style('stroke-width', this.lineWidth);
            this.sizeG.append('svg:image')
                .attr('x', imgStart)
                .attr('y', largerStart-imgHeight/2)
                .attr('width', imgWidth)
                .attr('height', imgHeight)
                .attr('xlink:href', '/static/images/example.png');
            this.sizeG.append('rect')
                .attr('fill', 'none')
                .attr('stroke', this.gtColor)
                .attr('stroke-width', this.boxWidth)
                .attr('x', imgStart)
                .attr('y', largerStart-imgHeight/2)
                .attr('width', imgWidth)
                .attr('height', imgHeight);
            this.sizeG.append('rect')
                .attr('fill', 'none')
                .attr('stroke', this.prColor)
                .attr('stroke-width', this.boxWidth)
                .attr('x', imgStart-10)
                .attr('y', largerStart-imgHeight/2+2)
                .attr('width', imgWidth+15)
                .attr('height', imgHeight+10);
            this.sizeG.append('text')
                .text('Predictions larger')
                .attr('y', largerStart-5)
                .attr('x', textStart)
                .attr('font-size', this.fontSize)
                .attr('font-weight', this.fontWeight);
            this.sizeG.append('text')
                .text('than ground truth')
                .attr('y', largerStart+11)
                .attr('x', textStart)
                .attr('font-size', this.fontSize)
                .attr('font-weight', this.fontWeight);
            // precise
            this.sizeG.append('polyline')
                .attr('points', `${this.legendR*1.2},${this.legendR}
                    ${lineEnd},${this.legendR}`)
                .attr('fill', 'none')
                .attr('stroke', this.lineColor)
                .attr('stroke-width', this.lineWidth);
            this.sizeG.append('svg:image')
                .attr('x', imgStart)
                .attr('y', this.legendR-imgHeight/2)
                .attr('width', imgWidth)
                .attr('height', imgHeight)
                .attr('xlink:href', '/static/images/example.png');
            this.sizeG.append('rect')
                .attr('fill', 'none')
                .attr('stroke', this.gtColor)
                .attr('stroke-width', this.boxWidth)
                .attr('x', imgStart)
                .attr('y', this.legendR-imgHeight/2)
                .attr('width', imgWidth)
                .attr('height', imgHeight);
            this.sizeG.append('rect')
                .attr('fill', 'none')
                .attr('stroke', this.prColor)
                .attr('stroke-width', this.boxWidth)
                .attr('x', imgStart+2)
                .attr('y', this.legendR-imgHeight/2-2)
                .attr('width', imgWidth)
                .attr('height', imgHeight);
            this.sizeG.append('text')
                .text('Predictions with')
                .attr('y', this.legendR-5)
                .attr('x', textStart)
                .attr('font-size', this.fontSize)
                .attr('font-weight', this.fontWeight);
            this.sizeG.append('text')
                .text('precise sizes')
                .attr('y', this.legendR+11)
                .attr('x', textStart)
                .attr('font-size', this.fontSize)
                .attr('font-weight', this.fontWeight);
            // quantity
            let quantityStart = this.legendR+this.sizeR-5;
            const quantityLen = 20;
            this.sizeG.append('polyline')
                .attr('points', `${this.legendR-this.sizeR-1},${quantityStart}
                    ${this.legendR-this.sizeR-1},${quantityStart+quantityLen}`);
            this.sizeG.append('polyline')
                .attr('points', `${this.legendR+this.sizeR+1},${quantityStart}
                    ${this.legendR+this.sizeR+1},${quantityStart+quantityLen}`);

            this.sizeG.append('polyline')
                .attr('points', `${this.legendR * 3 /4},${quantityStart+quantityLen/2}
                                ${this.legendR-this.sizeR}, ${quantityStart+quantityLen/2}`);
            this.sizeG.append('polyline')
                .attr('points', `${this.legendR-this.sizeR+5}, ${quantityStart+quantityLen/2-5}
                    ${this.legendR-this.sizeR}, ${quantityStart+quantityLen/2}
                    ${this.legendR-this.sizeR+5}, ${quantityStart+quantityLen/2+5}`);
            this.sizeG.append('polyline')
                .attr('points', `${this.legendR * 5 /4},${quantityStart+quantityLen/2}
                                ${this.legendR+this.sizeR}, ${quantityStart+quantityLen/2}`);
            this.sizeG.append('polyline')
                .attr('points', `${this.legendR+this.sizeR-5}, ${quantityStart+quantityLen/2-5}
                    ${this.legendR+this.sizeR}, ${quantityStart+quantityLen/2}
                    ${this.legendR+this.sizeR-5}, ${quantityStart+quantityLen/2+5}`);
            this.sizeG.selectAll('polyline')
                .attr('fill', 'none')
                .attr('stroke', this.lineColor)
                .attr('stroke-width', this.lineWidth);

            // this.sizeG.append('polyline')
            //     .attr('points', `${this.legendR}, ${quantityStart+quantityLen/2+5}
            //         ${this.legendR+25}, ${quantityStart+quantityLen+25}
            //         ${lineEnd}, ${quantityStart+quantityLen+25}`)
            //     .attr('fill', 'none')
            //     .attr('stroke', this.lineColor)
            //     .attr('stroke-width', this.lineWidth);
            path = d3.path();
            path.moveTo(this.legendR, quantityStart + quantityLen / 2 + 5);
            path.quadraticCurveTo(this.legendR, quantityStart + quantityLen + 30, lineEnd, quantityStart + quantityLen + 30);
            this.sizeG.append('path')
                .attr('d', path.toString())
                .style('fill', 'none')
                .style('stroke', this.lineColor)
                .style('stroke-width', this.lineWidth);

            this.sizeG.append('text')
                .text('Numbers of samples')
                .attr('y', quantityStart+quantityLen+30 + 5)
                .attr('x', imgStart)
                .attr('font-size', this.fontSize)
                .attr('font-weight', this.fontWeight);


            this.posG.attr('transform', `translate(0, ${posTranslate})`);
            // quantity
            quantityStart = 40;
            // vertical lines
            this.posG.append('polyline')
                .attr('points', `${this.legendR-this.sizeR-1},${quantityStart}
                    ${this.legendR-this.sizeR-1},${quantityStart+quantityLen}`);
            this.posG.append('polyline')
                .attr('points', `${this.legendR-this.legendR/6-1},${quantityStart}
                    ${this.legendR-this.legendR/6-1},${quantityStart+quantityLen}`);
            this.posG.append('polyline')
                .attr('points', `${this.legendR+this.legendR/6+1},${quantityStart}
                    ${this.legendR+this.legendR/6+1},${quantityStart+quantityLen}`);

            // 2 arrows on the left
            this.posG.append('polyline')
                .attr('points', `${this.legendR * 14 /30+2},${quantityStart+quantityLen/2}
                                ${this.legendR-this.sizeR}, ${quantityStart+quantityLen/2}`);
            this.posG.append('polyline')
                .attr('points', `${this.legendR-this.sizeR+5}, ${quantityStart+quantityLen/2-5}
                    ${this.legendR-this.sizeR}, ${quantityStart+quantityLen/2}
                    ${this.legendR-this.sizeR+5}, ${quantityStart+quantityLen/2+5}`);
            this.posG.append('polyline')
                .attr('points', `${this.legendR * 20 /30},${quantityStart+quantityLen/2}
                                ${this.legendR-this.legendR/6-1}, ${quantityStart+quantityLen/2}`);
            this.posG.append('polyline')
                .attr('points', `${this.legendR-this.legendR/6-1-5}, ${quantityStart+quantityLen/2-5}
                    ${this.legendR-this.legendR/6-1}, ${quantityStart+quantityLen/2}
                    ${this.legendR-this.legendR/6-1-5}, ${quantityStart+quantityLen/2+5}`);

            // 2 arrows on the right
            this.posG.append('polyline')
                .attr('points', `${this.legendR -4},${quantityStart+quantityLen/2}
                                ${this.legendR-this.legendR/6-1}, ${quantityStart+quantityLen/2}`);
            this.posG.append('polyline')
                .attr('points', `${this.legendR-this.legendR/6-1+5}, ${quantityStart+quantityLen/2-5}
                    ${this.legendR-this.legendR/6-1}, ${quantityStart+quantityLen/2}
                    ${this.legendR-this.legendR/6-1+5}, ${quantityStart+quantityLen/2+5}`);
            this.posG.append('polyline')
                .attr('points', `${this.legendR +4},${quantityStart+quantityLen/2}
                                ${this.legendR+this.legendR/6+1}, ${quantityStart+quantityLen/2}`);
            this.posG.append('polyline')
                .attr('points', `${this.legendR+this.legendR/6+1-5}, ${quantityStart+quantityLen/2-5}
                    ${this.legendR+this.legendR/6+1}, ${quantityStart+quantityLen/2}
                    ${this.legendR+this.legendR/6+1-5}, ${quantityStart+quantityLen/2+5}`);
            this.posG.selectAll('polyline')
                .attr('fill', 'none')
                .attr('stroke', this.lineColor)
                .attr('stroke-width', this.lineWidth);
            // this.posG.append('polyline')
            //     .attr('points', `${this.legendR}, ${quantityStart+quantityLen/2-5}
            //         ${this.legendR+25}, ${quantityStart-25}`)
            //     .attr('fill', 'none')
            //     .attr('stroke', this.lineColor)
            //     .attr('stroke-width', this.lineWidth);
            path = d3.path();
            path.moveTo(this.legendR, quantityStart + quantityLen / 2 - 10);
            path.quadraticCurveTo(this.legendR, quantityStart - 45, lineEnd, quantityStart - 45);
            this.posG.append('path')
                .attr('d', path.toString())
                .style('fill', 'none')
                .style('stroke', this.lineColor)
                .style('stroke-width', this.lineWidth);
            path = d3.path();
            path.moveTo(this.legendR * 17 / 30 +2, quantityStart + quantityLen / 2 - 10);
            path.quadraticCurveTo(this.legendR * 17 / 30 +2, quantityStart - 45, lineEnd, quantityStart - 45);
            this.posG.append('path')
                .attr('d', path.toString())
                .style('fill', 'none')
                .style('stroke', this.lineColor)
                .style('stroke-width', this.lineWidth);
            // directions
            this.posG.append('circle')
                .attr('cx', this.legendR)
                .attr('cy', this.legendR)
                .attr('r', this.legendR / 6)
                .attr('fill', this.directionColor);
            for (let i = 0; i < 8; ++i) {
                if (i >= 1 && i <= 3) continue;
                this.posG.append('polyline')
                    .attr('class', 'dir-'+i)
                    .attr('stroke-width', this.lineWidth)
                    .attr('points', `${this.legendR * 0.8},${this.legendR}
                                    ${(1-this.posRatio[i]) * this.legendR}, ${this.legendR}`);
                this.posG.append('polyline')
                    .attr('class', 'dir-'+i)
                    .attr('points', `${(1-this.posRatio[i]) * this.legendR+6}, ${this.legendR-3}
                        ${(1-this.posRatio[i]) * this.legendR}, ${this.legendR}
                        ${(1-this.posRatio[i]) * this.legendR+6}, ${this.legendR+3}`)
                    .attr('stroke-width', 1);
                this.posG.selectAll('.dir-'+i)
                    .attr('fill', 'none')
                    .attr('stroke', this.directionColor)
                    // .attr('marker-end', 'url(#arrow)')
                    .attr('transform', `rotate(${i*45} ${this.legendR} ${this.legendR})`);
            }
            // precise
            // this.posG.append('polyline')
            //     .attr('points', `${this.legendR},${this.legendR}
            //         ${this.legendR+30},${dirPreciseStart}
            //         ${lineEnd},${dirPreciseStart}`)
            //     .attr('fill', 'none')
            //     .attr('stroke', this.lineColor)
            //     .attr('stroke-width', this.lineWidth);
            path = d3.path();
            path.moveTo(this.legendR, this.legendR);
            path.quadraticCurveTo(this.legendR+30, dirPreciseStart, lineEnd, dirPreciseStart);
            this.posG.append('path')
                .attr('d', path.toString())
                .style('fill', 'none')
                .style('stroke', this.lineColor)
                .style('stroke-width', this.lineWidth);
            this.posG.append('svg:image')
                .attr('x', imgStart)
                .attr('y', dirPreciseStart-imgHeight/2)
                .attr('width', imgWidth)
                .attr('height', imgHeight)
                .attr('xlink:href', '/static/images/example.png');
            this.posG.append('rect')
                .attr('fill', 'none')
                .attr('stroke', this.gtColor)
                .attr('stroke-width', this.boxWidth)
                .attr('x', imgStart)
                .attr('y', dirPreciseStart-imgHeight/2)
                .attr('width', imgWidth)
                .attr('height', imgHeight);
            this.posG.append('rect')
                .attr('fill', 'none')
                .attr('stroke', this.prColor)
                .attr('stroke-width', this.boxWidth)
                .attr('x', imgStart+2)
                .attr('y', dirPreciseStart-imgHeight/2-2)
                .attr('width', imgWidth)
                .attr('height', imgHeight);
            this.posG.append('text')
                .text('Predictions with')
                .attr('y', dirPreciseStart-5)
                .attr('x', textStart)
                .attr('font-size', this.fontSize)
                .attr('font-weight', this.fontWeight);
            this.posG.append('text')
                .text('precise positions')
                .attr('y', dirPreciseStart+11)
                .attr('x', textStart)
                .attr('font-size', this.fontSize)
                .attr('font-weight', this.fontWeight);
            // shifted
            // this.posG.append('polyline')
            //     .attr('points', `${this.legendR+5},${this.legendR*3/2+10}
            //         ${this.legendR+30},${shiftStart}
            //         ${lineEnd},${shiftStart}`)
            //     .attr('fill', 'none')
            //     .attr('stroke', this.lineColor)
            //     .attr('stroke-width', this.lineWidth);
            path = d3.path();
            path.moveTo(this.legendR+5, this.legendR*1.5);
            path.quadraticCurveTo(this.legendR+30, shiftStart, lineEnd, shiftStart);
            this.posG.append('path')
                .attr('d', path.toString())
                .style('fill', 'none')
                .style('stroke', this.lineColor)
                .style('stroke-width', this.lineWidth);
            this.posG.append('svg:image')
                .attr('x', imgStart)
                .attr('y', shiftStart-imgHeight/2)
                .attr('width', imgWidth)
                .attr('height', imgHeight)
                .attr('xlink:href', '/static/images/example.png');
            this.posG.append('rect')
                .attr('fill', 'none')
                .attr('stroke', this.gtColor)
                .attr('stroke-width', this.boxWidth)
                .attr('x', imgStart)
                .attr('y', shiftStart-imgHeight/2)
                .attr('width', imgWidth)
                .attr('height', imgHeight);
            this.posG.append('rect')
                .attr('fill', 'none')
                .attr('stroke', this.prColor)
                .attr('stroke-width', this.boxWidth)
                .attr('x', imgStart+2)
                .attr('y', shiftStart-imgHeight/2+15)
                .attr('width', imgWidth-4)
                .attr('height', imgHeight);
            this.posG.append('text')
                .text('Predictions shifted in')
                .attr('y', shiftStart-5)
                .attr('x', textStart)
                .attr('font-size', this.fontSize)
                .attr('font-weight', this.fontWeight);
            this.posG.append('text')
                .text('a specific direction')
                .attr('y', shiftStart+11)
                .attr('x', textStart)
                .attr('font-size', this.fontSize)
                .attr('font-weight', this.fontWeight);

            // transform
            const scalew = (svgRealWidth+20) / svgWidth;
            const scaleh = (svgRealHeight+20) / svgHeight;
            const scale = Math.min(scalew, scaleh);
            const shifty = (svgRealHeight - svgHeight * scale) / 2;
            const shiftx = (svgRealWidth - svgWidth * scale) / 2;
            this.mainG.attr('transform', `translate(${shiftx+2}, ${shifty}) scale(${scale})`);
        },
    },
    mounted: function() {
        this.render();
    },
};
</script>
<style scoped>
.legends-content {
    height: 100%;
    border: 1px solid #c1c1c1;
    border-radius: 5px;
}
</style>
