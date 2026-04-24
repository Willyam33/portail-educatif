<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'

const router = useRouter()

const entrees = ref([])
const chargement = ref(true)
const erreur = ref('')

async function charger() {
  chargement.value = true
  erreur.value = ''
  try {
    const { data } = await api.get('/eleve/historique-thematiques/')
    entrees.value = data
  } catch {
    erreur.value = "Impossible de charger l'historique."
  } finally {
    chargement.value = false
  }
}

function formaterDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  })
}

function scorePourcent(e) {
  if (!e.qcm_termine || !e.total_questions) return null
  return Math.round((100 * e.score) / e.total_questions)
}

function ouvrirLecon(e) {
  router.push(`/thematique/${e.thematique_id}/lecon`)
}

function ouvrirQCM(e) {
  router.push(`/thematique/${e.thematique_id}/qcm`)
}

function retour() {
  router.push('/')
}

onMounted(charger)
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <header class="bg-white border-b border-slate-200 sticky top-0 z-10">
      <div class="max-w-4xl mx-auto px-6 py-3 flex items-center justify-between">
        <button
          type="button"
          class="text-sm text-slate-600 hover:text-slate-900"
          @click="retour"
        >
          ← Retour
        </button>
        <h1 class="text-lg font-semibold text-slate-800">Mon historique</h1>
        <span class="text-sm text-slate-400">{{ entrees.length }} thématique(s)</span>
      </div>
    </header>

    <main class="max-w-4xl mx-auto px-6 py-8 space-y-4">
      <p v-if="chargement" class="text-slate-500">Chargement…</p>
      <p v-else-if="erreur" class="text-red-600">{{ erreur }}</p>

      <p v-else-if="entrees.length === 0" class="text-slate-500">
        Ton historique est vide pour l'instant.
      </p>

      <article
        v-for="entree in entrees"
        v-else
        :key="entree.thematique_id"
        class="bg-white rounded-lg shadow-sm border border-slate-200 p-5"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span
                class="inline-block px-2 py-0.5 rounded text-xs font-medium text-white"
                :style="{ backgroundColor: entree.matiere.couleur }"
              >
                {{ entree.matiere.nom }}
              </span>
              <span class="text-xs text-slate-500">
                {{ formaterDate(entree.date) }}
              </span>
            </div>
            <h2 class="mt-1 text-lg font-semibold text-slate-800">
              {{ entree.titre }}
            </h2>
            <div class="mt-2 flex items-center gap-3 text-sm">
              <span
                v-if="entree.lecon_lue"
                class="inline-flex items-center gap-1 text-emerald-700"
              >
                ✓ Leçon lue
              </span>
              <span v-else class="text-slate-400">Leçon non lue</span>

              <span
                v-if="entree.qcm_termine"
                class="inline-flex items-center gap-1"
                :class="scorePourcent(entree) >= 50 ? 'text-emerald-700' : 'text-orange-600'"
              >
                QCM : {{ entree.score }}/{{ entree.total_questions }}
                ({{ scorePourcent(entree) }}%)
              </span>
              <span v-else class="text-slate-400">QCM non terminé</span>
            </div>
          </div>

          <div class="flex flex-col gap-2 shrink-0">
            <button
              type="button"
              class="text-sm text-indigo-600 hover:underline"
              @click="ouvrirLecon(entree)"
            >
              Revoir la leçon
            </button>
            <button
              v-if="entree.qcm_termine"
              type="button"
              class="text-sm text-emerald-600 hover:underline"
              @click="ouvrirQCM(entree)"
            >
              Refaire le QCM
            </button>
          </div>
        </div>
      </article>
    </main>
  </div>
</template>
