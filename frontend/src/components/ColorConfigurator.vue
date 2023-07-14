<template>
    <el-dialog
        title="Configure color"
        :visible.sync="colorSelectVisible"
        width="30%"
        @opened="render">
        <svg id="example-svg" style="width: 100%;">
            <g id="example-main-g">
                <g id="example-gt-pr-g"></g>
                <g id="example-size-bias-g"></g>
                <!-- <g id="example-pos-shift-g"></g> -->
            </g>
        </svg>
        <el-color-picker v-model="sizeColors[0]" style="position: absolute; top: 40%; left: 35%;"
            @active-change="(d)=>updateColors(d, 0)"></el-color-picker>
        <el-color-picker v-model="sizeColors[1]" style="position: absolute; top: 57%; left: 13%;"
            @active-change="(d)=>updateColors(d, 1)"></el-color-picker>
        <el-color-picker v-model="sizeColors[2]" style="position: absolute; top: 23%; left: 13%;"
            @active-change="(d)=>updateColors(d, 2)"></el-color-picker>
        <el-color-picker v-model="gtColor" style="position: absolute; top: 23%; left: 55%;"
            @active-change="(d)=>updateColors(d, 3)"></el-color-picker>
        <el-color-picker v-model="prColor" style="position: absolute; top: 50%; left: 82%;"
            @active-change="(d)=>updateColors(d, 4)"></el-color-picker>
        <span slot="footer" class="dialog-footer">
            <el-button @click="getDefaultColors">Get default</el-button>
            <el-button @click="colorSelectVisible = false">Cancel</el-button>
            <el-button type="primary" @click="saveColors">Save</el-button>
        </span>
    </el-dialog>
</template>

<script>
import {mapGetters} from 'vuex';
import * as d3 from 'd3';
import Util from './Util.vue';
import GlobalVar from './GlovalVar.vue';
window.d3 = d3;


import Vue from 'vue';
import {Dialog, ColorPicker} from 'element-ui';
import lang from 'element-ui/lib/locale/lang/en';
import locale from 'element-ui/lib/locale';


Vue.use(Dialog);
Vue.use(ColorPicker);

locale.use(lang);

export default {
    name: 'ColorConfigurator',
    mixins: [Util, GlobalVar],
    props: {
    },
    computed: {
        ...mapGetters(['labelnames']),
    },
    watch: {
    },
    data() {
        return {
            colorSelectVisible: false,
            sizeColors: ['rgb(216,216,216)', 'rgb(250,188,5)', 'rgb(124,198,39)'],
            gtColor: 'rgb(27, 251, 254)',
            prColor: 'rgb(253, 6, 253)',
            sizeAngles: [0, 0.45 * 2 * Math.PI, 0.8 * 2 * Math.PI, 2 * Math.PI],
            boxWidth: 4,
            legendR: 60,
            sizeR: 45,
            rectH: 60,
        };
    },
    methods: {
        render: async function() {
            const that = this;
            if (d3.select('g#example-size-bias-g').selectAll('path').size() === 0) {
                d3.select('g#example-size-bias-g').attr('transform', `translate(55, 12)`);
                for (let i = 0; i < 3; ++i) {
                    d3.select('g#example-size-bias-g').append('path')
                        .attr('class', 'size-circle')
                        .attr('id', `size-circle-${i}`)
                        .attr('transform', `translate(${that.legendR+12} ${that.legendR})`)
                        .attr('fill', that.sizeColors[i])
                        .attr('d', d3.arc().innerRadius(0).outerRadius(that.sizeR)
                            .startAngle(that.sizeAngles[i]).endAngle(that.sizeAngles[i+1])());
                }
            }
            if (d3.select('g#example-gt-pr-g').selectAll('rect').size() === 0) {
                d3.select('g#example-gt-pr-g').append('rect')
                    .attr('fill', 'none')
                    .attr('id', 'gt-rect')
                    .attr('stroke', this.gtColor)
                    .attr('stroke-width', this.boxWidth)
                    .attr('x', '65%')
                    .attr('y', '20%')
                    .attr('width', this.rectH)
                    .attr('height', this.rectH);
                d3.select('g#example-gt-pr-g').append('rect')
                    .attr('fill', 'none')
                    .attr('id', 'pr-rect')
                    .attr('stroke', this.prColor)
                    .attr('stroke-width', this.boxWidth)
                    .attr('x', '70%')
                    .attr('y', '45%')
                    .attr('width', this.rectH)
                    .attr('height', this.rectH-20);
            }
        },
        saveColors: function() {
            this.colorSelectVisible = false;
            console.log(this.sizeColors, this.gtColor, this.prColor);
            this.$emit('saveColors', this.sizeColors, this.gtColor, this.prColor);
        },
        getDefaultColors: function() {
            this.sizeColors = ['rgb(216,216,216)', 'rgb(250,188,5)', 'rgb(124,198,39)'];
            this.gtColor = 'rgb(27, 251, 254)';
            this.prColor = 'rgb(253, 6, 253)';
            for (let i = 0; i < 3; ++i) {
                d3.select('g#example-size-bias-g').select(`#size-circle-${i}`)
                    .attr('fill', this.sizeColors[i]);
            }
            d3.select('g#example-gt-pr-g').select('#pr-rect').attr('stroke', this.prColor);
            d3.select('g#example-gt-pr-g').select('#gt-rect').attr('stroke', this.gtColor);
        },
        showDialog: function() {
            this.colorSelectVisible = true;
            this.render();
        },
        updateColors: function(color, id) {
            if (id < 3) {
                d3.select('g#example-size-bias-g').select(`#size-circle-${id}`)
                    .attr('fill', color);
            } else if (id === 3) {
                d3.select('g#example-gt-pr-g').select('#gt-rect').attr('stroke', color);
            } else if (id === 4) {
                d3.select('g#example-gt-pr-g').select('#pr-rect').attr('stroke', color);
            }
        },
    },
    mounted: function() {
        this.render();
    },
};
</script>
<style scoped>

</style>
