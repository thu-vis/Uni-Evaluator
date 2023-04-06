<template>
  <div id="app">
    <svg width="0" height="0">
        <defs id="texture">
            <pattern v-for="(texture, i) in textures" v-html="texture" :key="i">
            </pattern>
        </defs>
    </svg>
    <router-view></router-view>
  </div>
</template>

<script>
/* eslint-disable max-len */
import DataView from './components/DataView.vue';
import Vue from 'vue';
import VueRouter from 'vue-router';
import {Menu, MenuItem} from 'element-ui';
import Util from './components/Util.vue';

Vue.use(Menu);
Vue.use(MenuItem);
Vue.use(VueRouter);

const router = new VueRouter({
    routes: [
        {path: '/dataview', component: DataView},
    ],
});

// main vue component
export default {
    name: 'App',
    mixins: [Util],
    data: function() {
        return {
            activeRoute: '/dataview',
            textures: [],
            colorsscope: {'hue_scope': [0, 360], 'lumi_scope': [35, 95]},
        };
    },
    mounted: function() {
        const store = this.$store;
        this.matrixDataPost(store.getters.URL_GET_METADATA)
            .then(function(response) {
                store.commit('setMetadata', response.data);
                console.log('meta data', response.data);
            });
        if (this.$route.path === '/') {
            this.$router.push('/dataview');
            this.activeRoute = '/dataview';
        } else {
            this.activeRoute = this.$route.path;
        }
    },
    methods: {
    },
    router: router,
};
</script>

<style>
html, body, #app {
  margin: 0;
  width: 100%;
  height: 99.8%;
}

#app {
  font-family: Arial, sans-serif;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

#navigation {
  width: 100%;
  height: 50px;
  display: flex;
  align-items: center;
  background: rgb(54, 54, 54);
}

#navi-title {
  color: rgb(255, 255, 255);
  font-weight: 900;
  font-size: 40px;
  margin: 0 50px 0 20px;
  float: left;
}

.router-link {
  text-decoration: none;
}

.toolbar-title {
  height: 18px;
  font-size: 15px;
  font-family: "Roboto", "Helvetica", "Arial", sans-serif;
  font-weight: 600;
  background: rgb(238, 238, 238);
  color: rgb(120, 120, 120);
  border-radius: 5px;
  padding-left: 10px;
  flex-shrink: 0;
}
</style>
