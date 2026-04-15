import { createRouter, createWebHistory } from 'vue-router'
import Home from './views/Home.vue'
import PageView from './views/PageView.vue'
import CategoryView from './views/CategoryView.vue'
import GraphView from './views/GraphView.vue'
import ChatView from './views/ChatView.vue'

const routes = [
  { path: '/', component: Home },
  { path: '/page/:category/:slug', component: PageView },
  { path: '/category/:type', component: CategoryView },
  { path: '/graph', component: GraphView },
  { path: '/chat', component: ChatView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})
