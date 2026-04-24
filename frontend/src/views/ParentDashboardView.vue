<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const enfants = ref([])
const erreur = ref('')
const chargement = ref(true)

async function charger() {
  chargement.value = true
  erreur.value = ''
  try {
    const { data } = await api.get('/parent/enfants/')
    enfants.value = data
  } catch {
    erreur.value = 'Impossible de charger la liste des enfants.'
  } finally {
    chargement.value = false
  }
}

function ouvrirSuivi(eleveId) {
  router.push({ name: 'parent-suivi', params: { eleveId } })
}

async function deconnexion() {
  await auth.deconnecter()
  router.push('/login')
}

onMounted(charger)
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <header class="bg-white border-b border-slate-200">
      <div class="max-w-4xl mx-auto px-4 py-3 sm:px-6 sm:py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-0">
        <div>
          <h1 class="text-lg sm:text-xl font-semibold text-slate-800">
            Espace parent — {{ auth.utilisateur?.first_name || auth.utilisateur?.username }}
          </h1>
          <p class="text-xs sm:text-sm text-slate-500">Suivi de mes enfants</p>
        </div>
        <button
          type="button"
          class="text-sm text-slate-600 hover:text-slate-900 underline self-start sm:self-auto"
          @click="deconnexion"
        >
          Se déconnecter
        </button>
      </div>
    </header>

    <main class="max-w-4xl mx-auto px-4 py-6 sm:px-6 sm:py-8 space-y-6">
      <p v-if="chargement" class="text-slate-500">Chargement…</p>
      <p v-else-if="erreur" class="text-red-600">{{ erreur }}</p>
      <p v-else-if="enfants.length === 0" class="text-slate-600">
        Aucun enfant n'est rattaché à votre compte pour l'instant.
      </p>

      <section v-else class="grid gap-4 sm:grid-cols-2">
        <button
          v-for="enfant in enfants"
          :key="enfant.id"
          type="button"
          class="text-left bg-white rounded-lg shadow-sm border border-slate-200 p-5 hover:border-indigo-400 hover:shadow transition"
          @click="ouvrirSuivi(enfant.id)"
        >
          <p class="text-lg font-semibold text-slate-800">
            {{ enfant.first_name || enfant.username }}
            <span v-if="enfant.last_name" class="text-slate-500 font-normal">{{ enfant.last_name }}</span>
          </p>
          <p class="text-sm text-slate-500 mt-1">
            Niveau : {{ enfant.niveau_scolaire || '—' }}
          </p>
          <p class="text-xs text-indigo-600 mt-3">Voir le suivi →</p>
        </button>
      </section>
    </main>
  </div>
</template>
