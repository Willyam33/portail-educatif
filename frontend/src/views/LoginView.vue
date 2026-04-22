<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const username = ref('')
const password = ref('')
const erreur = ref('')
const chargement = ref(false)
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

async function seConnecter() {
  erreur.value = ''
  chargement.value = true
  try {
    await auth.connecter(username.value, password.value)
    const redirection = route.query.redirect
    if (redirection) {
      router.push(redirection)
    } else if (auth.estParent || auth.estAdmin) {
      router.push({ name: 'parent' })
    } else {
      router.push({ name: 'accueil' })
    }
  } catch (e) {
    if (e.response?.status === 401) {
      erreur.value = 'Identifiants incorrects.'
    } else {
      erreur.value = "Impossible de se connecter. Réessaie dans un instant."
    }
  } finally {
    chargement.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-slate-50 px-4">
    <form
      class="w-full max-w-sm bg-white rounded-lg shadow-md p-8 space-y-5"
      @submit.prevent="seConnecter"
    >
      <div>
        <h1 class="text-2xl font-semibold text-slate-800">Portail éducatif</h1>
        <p class="text-sm text-slate-500 mt-1">Connecte-toi pour commencer ta journée.</p>
      </div>

      <div class="space-y-3">
        <label class="block">
          <span class="text-sm font-medium text-slate-700">Identifiant</span>
          <input
            v-model="username"
            type="text"
            autocomplete="username"
            required
            class="mt-1 w-full rounded border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </label>

        <label class="block">
          <span class="text-sm font-medium text-slate-700">Mot de passe</span>
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
            required
            class="mt-1 w-full rounded border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </label>
      </div>

      <p v-if="erreur" class="text-sm text-red-600">{{ erreur }}</p>

      <button
        type="submit"
        :disabled="chargement"
        class="w-full bg-indigo-600 text-white font-medium py-2 rounded hover:bg-indigo-700 disabled:opacity-60"
      >
        {{ chargement ? 'Connexion…' : 'Se connecter' }}
      </button>
    </form>
  </div>
</template>
