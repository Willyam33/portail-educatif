<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/services/api'

const route = useRoute()

const questions = ref([])
const erreur = ref('')
const chargement = ref(true)

const eleveId = computed(() => route.params.eleveId)

function formaterDate(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

async function charger() {
  chargement.value = true
  erreur.value = ''
  try {
    const { data } = await api.get(
      `/parent/suivi/${eleveId.value}/questions-libres/`,
    )
    questions.value = data
  } catch (e) {
    if (e.response?.status === 403) {
      erreur.value = "Cet élève n'est pas rattaché à votre famille."
    } else {
      erreur.value = "Impossible de charger les questions."
    }
  } finally {
    chargement.value = false
  }
}

onMounted(charger)
watch(eleveId, charger)
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <header class="bg-white border-b border-slate-200">
      <div class="max-w-4xl mx-auto px-4 py-3 sm:px-6 sm:py-4">
        <router-link
          :to="{ name: 'parent-suivi', params: { eleveId } }"
          class="text-sm text-slate-500 hover:text-slate-800"
        >
          ← Retour au suivi
        </router-link>
        <h1 class="text-lg sm:text-xl font-semibold text-slate-800 mt-1">
          Questions posées à l'IA
        </h1>
      </div>
    </header>

    <main class="max-w-4xl mx-auto px-4 py-6 sm:px-6 sm:py-8 space-y-4">
      <p v-if="chargement" class="text-slate-500">Chargement…</p>
      <p v-else-if="erreur" class="text-red-600">{{ erreur }}</p>
      <p v-else-if="questions.length === 0" class="text-slate-600">
        Aucune question posée à ce jour.
      </p>

      <article
        v-for="q in questions"
        :key="q.id"
        class="bg-white rounded-lg shadow-sm border border-slate-200 p-5 space-y-3"
      >
        <header class="flex items-start justify-between gap-4">
          <div>
            <span
              v-if="q.thematique"
              class="inline-block px-2 py-0.5 rounded text-xs font-medium text-white"
              :style="{ backgroundColor: q.thematique.matiere.couleur }"
            >
              {{ q.thematique.matiere.nom }}
            </span>
            <p v-if="q.thematique" class="text-sm text-slate-600 mt-1">
              {{ q.thematique.titre }}
            </p>
          </div>
          <p class="text-xs text-slate-400 whitespace-nowrap">
            {{ formaterDate(q.date) }}
          </p>
        </header>

        <div>
          <p class="text-xs uppercase tracking-wide text-slate-400 mb-1">Question</p>
          <p class="text-slate-800">{{ q.question }}</p>
        </div>

        <div>
          <p class="text-xs uppercase tracking-wide text-slate-400 mb-1">Réponse</p>
          <p class="text-slate-700 whitespace-pre-line">{{ q.reponse }}</p>
        </div>
      </article>
    </main>
  </div>
</template>
