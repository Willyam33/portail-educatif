import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import { router } from './router'
import { useAuthStore, installerInterceptors } from '@/stores/auth'
import './assets/main.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)

// Les intercepteurs axios doivent être installés AVANT le premier appel API :
// - injection automatique du jeton d'accès
// - refresh automatique sur 401
const auth = useAuthStore()
installerInterceptors(auth)

app.use(router)

// On attend d'avoir tenté le chargement de /me/ avant de monter l'application
// pour que le router guard dispose de l'état authentifié au premier rendu.
auth.chargerMoi().finally(() => {
  app.mount('#app')
})
