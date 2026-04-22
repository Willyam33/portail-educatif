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
    name: 'accueil',
    component: () => import('@/views/DashboardView.vue'),
    meta: { roles: ['eleve'] },
  },
  {
    path: '/thematique/:id(\\d+)/lecon',
    name: 'lecon',
    component: () => import('@/views/LeconView.vue'),
    meta: { roles: ['eleve'] },
  },
  {
    path: '/thematique/:id(\\d+)/qcm',
    name: 'qcm',
    component: () => import('@/views/QCMView.vue'),
    meta: { roles: ['eleve'] },
  },
  {
    path: '/historique',
    name: 'historique',
    component: () => import('@/views/HistoriqueView.vue'),
    meta: { roles: ['eleve'] },
  },
  {
    path: '/progression',
    name: 'progression',
    component: () => import('@/views/ProgressionView.vue'),
    meta: { roles: ['eleve'] },
  },
  {
    path: '/parent',
    name: 'parent',
    component: () => import('@/views/ParentDashboardView.vue'),
    meta: { roles: ['parent', 'administrateur'] },
  },
  {
    path: '/parent/suivi/:eleveId(\\d+)',
    name: 'parent-suivi',
    component: () => import('@/views/ParentSuiviView.vue'),
    meta: { roles: ['parent', 'administrateur'] },
  },
  {
    path: '/parent/suivi/:eleveId(\\d+)/jour/:date',
    name: 'parent-detail-jour',
    component: () => import('@/views/ParentDetailJourView.vue'),
    meta: { roles: ['parent', 'administrateur'] },
  },
  {
    path: '/parent/suivi/:eleveId(\\d+)/questions',
    name: 'parent-questions',
    component: () => import('@/views/ParentQuestionsView.vue'),
    meta: { roles: ['parent', 'administrateur'] },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

function accueilParRole(auth) {
  if (auth.estParent || auth.estAdmin) return { name: 'parent' }
  return { name: 'accueil' }
}

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta.public) {
    if (to.name === 'login' && auth.estConnecte && auth.utilisateur) {
      return accueilParRole(auth)
    }
    return true
  }

  if (!auth.estConnecte) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // Si on arrive sur une route à rôle mais que /me/ n'a pas encore été chargé,
  // on laisse passer ; le guard sera rejoué une fois le store prêt.
  if (!auth.utilisateur) return true

  const rolesAutorises = to.meta.roles
  if (rolesAutorises && !rolesAutorises.includes(auth.utilisateur.role)) {
    return accueilParRole(auth)
  }

  return true
})
