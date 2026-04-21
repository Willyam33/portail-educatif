// Store Pinia pour l'authentification JWT.
//
// - Stocke `access` et `refresh` dans localStorage pour survivre au rechargement.
// - Installe un intercepteur axios qui rafraîchit automatiquement l'access
//   token en cas de 401, puis rejoue la requête originale.
// - Si le refresh échoue, on déconnecte l'utilisateur (état propre).

import { defineStore } from 'pinia'
import { api, definirJetonAcces } from '@/services/api'

const CLE_ACCESS = 'portail.access'
const CLE_REFRESH = 'portail.refresh'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    access: localStorage.getItem(CLE_ACCESS) || null,
    refresh: localStorage.getItem(CLE_REFRESH) || null,
    utilisateur: null,
    pret: false, // true dès que /me/ a été appelé (ou qu'on sait qu'on est déconnecté)
  }),

  getters: {
    estConnecte: (state) => !!state.access,
    estEleve: (state) => state.utilisateur?.role === 'eleve',
  },

  actions: {
    _persister() {
      if (this.access) localStorage.setItem(CLE_ACCESS, this.access)
      else localStorage.removeItem(CLE_ACCESS)
      if (this.refresh) localStorage.setItem(CLE_REFRESH, this.refresh)
      else localStorage.removeItem(CLE_REFRESH)
      definirJetonAcces(this.access)
    },

    async connecter(username, password) {
      const { data } = await api.post('/auth/login/', { username, password })
      this.access = data.access
      this.refresh = data.refresh
      this._persister()
      await this.chargerMoi()
    },

    async chargerMoi() {
      if (!this.access) {
        this.pret = true
        return
      }
      try {
        const { data } = await api.get('/auth/me/')
        this.utilisateur = data
      } catch {
        this.deconnecterLocal()
      } finally {
        this.pret = true
      }
    },

    async deconnecter() {
      const refresh = this.refresh
      this.deconnecterLocal()
      if (refresh) {
        // best-effort : on blackliste côté serveur mais on n'échoue pas si ça rate
        try {
          await api.post('/auth/logout/', { refresh })
        } catch {
          /* ignore */
        }
      }
    },

    deconnecterLocal() {
      this.access = null
      this.refresh = null
      this.utilisateur = null
      this._persister()
    },

    async rafraichir() {
      if (!this.refresh) throw new Error('Pas de refresh token')
      const { data } = await api.post('/auth/refresh/', { refresh: this.refresh })
      this.access = data.access
      if (data.refresh) this.refresh = data.refresh
      this._persister()
      return this.access
    },
  },
})

// --- Intercepteurs axios ----------------------------------------------------

let rafraichissementEnCours = null

export function installerInterceptors(store) {
  // 1) Injecte le jeton d'accès sur chaque requête (au cas où il a été mis à
  //    jour après la création du client).
  api.interceptors.request.use((config) => {
    if (store.access) {
      config.headers.Authorization = `Bearer ${store.access}`
    }
    return config
  })

  // 2) Sur 401, tente un refresh puis rejoue la requête.
  api.interceptors.response.use(
    (response) => response,
    async (error) => {
      const original = error.config
      const estAuthUrl =
        original?.url?.includes('/auth/login/') ||
        original?.url?.includes('/auth/refresh/')

      if (
        error.response?.status === 401 &&
        !original?._rejoue &&
        !estAuthUrl &&
        store.refresh
      ) {
        original._rejoue = true
        try {
          rafraichissementEnCours = rafraichissementEnCours || store.rafraichir()
          const newAccess = await rafraichissementEnCours
          rafraichissementEnCours = null
          original.headers.Authorization = `Bearer ${newAccess}`
          return api(original)
        } catch (e) {
          rafraichissementEnCours = null
          store.deconnecterLocal()
          throw e
        }
      }
      throw error
    },
  )

  // Initialise l'en-tête Authorization avec le jeton persistant.
  definirJetonAcces(store.access)
}
