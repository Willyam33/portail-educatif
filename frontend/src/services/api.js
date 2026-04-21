import axios from 'axios'

// Client HTTP utilisé pour toutes les requêtes vers le back-end Django.
// En développement, Vite proxyfie /api vers http://127.0.0.1:8001 (voir vite.config.js).
export const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

export function definirJetonAcces(jeton) {
  if (jeton) {
    api.defaults.headers.common.Authorization = `Bearer ${jeton}`
  } else {
    delete api.defaults.headers.common.Authorization
  }
}
