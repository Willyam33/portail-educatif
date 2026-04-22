import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
  },
  {
    path: '/thematique/:id(\\d+)/lecon',
    name: 'lecon',
    component: () => import('@/views/LeconView.vue'),
  },
  {
    path: '/thematique/:id(\\d+)/qcm',
    name: 'qcm',
    component: () => import('@/views/QCMView.vue'),
  },
  {
    path: '/historique',
    name: 'historique',
    component: () => import('@/views/HistoriqueView.vue'),
  },
  {
    path: '/progression',
    name: 'progression',
    component: () => import('@/views/ProgressionView.vue'),
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    // Si déjà connecté, évite de rester sur la page de login
    if (to.name === 'login' && auth.estConnecte) return { name: 'dashboard' }
    return true
  }
  if (!auth.estConnecte) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
})
