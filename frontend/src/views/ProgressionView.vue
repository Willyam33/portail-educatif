<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'

const router = useRouter()

const global = ref(null)
const detail = ref([])
const chargement = ref(true)
const erreur = ref('')

async function charger() {
  chargement.value = true
  erreur.value = ''
  try {
    const [repGlobal, repDetail] = await Promise.all([
      api.get('/eleve/progression/'),
      api.get('/eleve/progression/detail/'),
    ])
    global.value = repGlobal.data
    detail.value = repDetail.data.par_matiere
  } catch {
    erreur.value = 'Impossible de charger la progression.'
  } finally {
    chargement.value = false
  }
}

function retour() {
  router.push('/')
}

onMounted(charger)
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <header class="bg-white border-b border-slate-200 sticky top-0 z-10">
      <div class="max-w-4xl mx-auto px-4 py-3 sm:px-6 flex items-center justify-between gap-3">
        <button
          type="button"
          class="text-sm text-slate-600 hover:text-slate-900 shrink-0"
          @click="retour"
        >
          ← Retour
        </button>
        <h1 class="text-base sm:text-lg font-semibold text-slate-800 truncate">Ma progression</h1>
        <span class="shrink-0 w-12" />
      </div>
    </header>

    <main class="max-w-4xl mx-auto px-4 py-6 sm:px-6 sm:py-8 space-y-6">
      <p v-if="chargement" class="text-slate-500">Chargement…</p>
      <p v-else-if="erreur" class="text-red-600">{{ erreur }}</p>

      <template v-else>
        <section
          v-if="global"
          class="bg-white rounded-lg shadow-sm border border-slate-200 p-5 sm:p-6"
        >
          <h2 class="text-base font-semibold text-slate-800 mb-3">Vue d'ensemble</h2>
          <div class="grid grid-cols-3 gap-2 sm:gap-4 text-center">
            <div>
              <p class="text-2xl sm:text-3xl font-semibold text-slate-800">{{ global.lecons_lues }}</p>
              <p class="text-xs text-slate-500 mt-1">leçons lues</p>
            </div>
            <div>
              <p class="text-2xl sm:text-3xl font-semibold text-slate-800">{{ global.qcm_termines }}</p>
              <p class="text-xs text-slate-500 mt-1">QCM terminés</p>
            </div>
            <div>
              <p class="text-2xl sm:text-3xl font-semibold text-slate-800">
                {{ global.score_moyen_pourcent !== null ? global.score_moyen_pourcent + '%' : '—' }}
              </p>
              <p class="text-xs text-slate-500 mt-1">score moyen</p>
            </div>
          </div>
        </section>

        <section class="bg-white rounded-lg shadow-sm border border-slate-200 p-5 sm:p-6">
          <h2 class="text-base font-semibold text-slate-800 mb-4">Par matière</h2>
          <div class="space-y-3">
            <div
              v-for="ligne in detail"
              :key="ligne.matiere.code"
              class="border border-slate-200 rounded-lg p-4"
            >
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center gap-2">
                  <span
                    class="inline-block w-3 h-3 rounded-full"
                    :style="{ backgroundColor: ligne.matiere.couleur }"
                  />
                  <span class="font-medium text-slate-800">{{ ligne.matiere.nom }}</span>
                </div>
                <span
                  class="text-sm font-semibold"
                  :class="[
                    ligne.score_moyen_pourcent === null
                      ? 'text-slate-400'
                      : ligne.score_moyen_pourcent >= 50
                        ? 'text-emerald-700'
                        : 'text-orange-600',
                  ]"
                >
                  {{ ligne.score_moyen_pourcent !== null ? ligne.score_moyen_pourcent + '%' : '—' }}
                </span>
              </div>
              <div class="flex flex-wrap gap-x-4 sm:gap-x-6 gap-y-1 text-xs text-slate-500">
                <span>{{ ligne.lecons_lues }} leçon{{ ligne.lecons_lues > 1 ? 's' : '' }} lue{{ ligne.lecons_lues > 1 ? 's' : '' }}</span>
                <span>{{ ligne.qcm_termines }} QCM terminé{{ ligne.qcm_termines > 1 ? 's' : '' }}</span>
              </div>
              <div
                v-if="ligne.score_moyen_pourcent !== null"
                class="mt-2 h-2 bg-slate-100 rounded-full overflow-hidden"
              >
                <div
                  class="h-full"
                  :style="{
                    width: ligne.score_moyen_pourcent + '%',
                    backgroundColor: ligne.matiere.couleur,
                  }"
                />
              </div>
            </div>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>
