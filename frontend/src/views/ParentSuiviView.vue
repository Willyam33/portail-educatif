<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/services/api'

const route = useRoute()
const router = useRouter()

const suivi = ref(null)
const erreur = ref('')
const chargement = ref(true)

const dateChoisie = ref(new Date().toISOString().slice(0, 10))

const eleveId = computed(() => route.params.eleveId)

async function charger() {
  chargement.value = true
  erreur.value = ''
  try {
    const { data } = await api.get(`/parent/suivi/${eleveId.value}/`)
    suivi.value = data
  } catch (e) {
    if (e.response?.status === 403) {
      erreur.value = "Cet élève n'est pas rattaché à votre famille."
    } else if (e.response?.status === 404) {
      erreur.value = "Élève introuvable."
    } else {
      erreur.value = 'Impossible de charger le suivi.'
    }
  } finally {
    chargement.value = false
  }
}

function ouvrirJour() {
  router.push({
    name: 'parent-detail-jour',
    params: { eleveId: eleveId.value, date: dateChoisie.value },
  })
}

function ouvrirQuestions() {
  router.push({
    name: 'parent-questions',
    params: { eleveId: eleveId.value },
  })
}

onMounted(charger)
watch(eleveId, charger)
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <header class="bg-white border-b border-slate-200">
      <div class="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
        <div>
          <router-link :to="{ name: 'parent' }" class="text-sm text-slate-500 hover:text-slate-800">
            ← Tous les enfants
          </router-link>
          <h1 v-if="suivi" class="text-xl font-semibold text-slate-800 mt-1">
            Suivi de {{ suivi.eleve.first_name || suivi.eleve.username }}
          </h1>
        </div>
      </div>
    </header>

    <main class="max-w-4xl mx-auto px-6 py-8 space-y-6">
      <p v-if="chargement" class="text-slate-500">Chargement…</p>
      <p v-else-if="erreur" class="text-red-600">{{ erreur }}</p>

      <template v-else-if="suivi">
        <section class="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
          <h2 class="text-lg font-semibold text-slate-800 mb-3">Vue d'ensemble</h2>
          <div class="grid grid-cols-4 gap-4 text-center">
            <div>
              <p class="text-2xl font-semibold text-slate-800">{{ suivi.lecons_lues }}</p>
              <p class="text-xs text-slate-500">leçons lues</p>
            </div>
            <div>
              <p class="text-2xl font-semibold text-slate-800">{{ suivi.qcm_termines }}</p>
              <p class="text-xs text-slate-500">QCM terminés</p>
            </div>
            <div>
              <p class="text-2xl font-semibold text-slate-800">
                {{
                  suivi.score_moyen_pourcent !== null
                    ? suivi.score_moyen_pourcent + '%'
                    : '—'
                }}
              </p>
              <p class="text-xs text-slate-500">score moyen</p>
            </div>
            <div>
              <p class="text-2xl font-semibold text-slate-800">{{ suivi.nb_questions_libres }}</p>
              <p class="text-xs text-slate-500">questions posées</p>
            </div>
          </div>
        </section>

        <section class="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
          <h2 class="text-lg font-semibold text-slate-800 mb-4">Par matière</h2>
          <div class="space-y-3">
            <div
              v-for="stats in suivi.par_matiere"
              :key="stats.matiere.id"
              class="flex items-center justify-between border-b border-slate-100 pb-2 last:border-0 last:pb-0"
            >
              <div class="flex items-center gap-3">
                <span
                  class="inline-block w-3 h-3 rounded-full"
                  :style="{ backgroundColor: stats.matiere.couleur }"
                ></span>
                <span class="text-slate-700">{{ stats.matiere.nom }}</span>
              </div>
              <div class="text-sm text-slate-500 flex gap-4">
                <span>{{ stats.lecons_lues }} leçon(s)</span>
                <span>{{ stats.qcm_termines }} QCM</span>
                <span class="font-medium text-slate-700 w-14 text-right">
                  {{
                    stats.score_moyen_pourcent !== null
                      ? stats.score_moyen_pourcent + '%'
                      : '—'
                  }}
                </span>
              </div>
            </div>
          </div>
        </section>

        <section class="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
          <h2 class="text-lg font-semibold text-slate-800 mb-3">Zoom sur une journée</h2>
          <div class="flex flex-wrap items-center gap-3">
            <input
              v-model="dateChoisie"
              type="date"
              class="rounded border border-slate-300 px-3 py-2"
            />
            <button
              type="button"
              class="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
              @click="ouvrirJour"
            >
              Voir cette journée
            </button>
          </div>
        </section>

        <section class="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
          <h2 class="text-lg font-semibold text-slate-800 mb-2">Questions libres</h2>
          <p class="text-sm text-slate-600 mb-3">
            {{ suivi.nb_questions_libres }} question(s) posée(s) à l'IA.
          </p>
          <button
            type="button"
            class="bg-slate-800 text-white px-4 py-2 rounded hover:bg-slate-900"
            @click="ouvrirQuestions"
          >
            Consulter l'historique complet
          </button>
        </section>
      </template>
    </main>
  </div>
</template>
