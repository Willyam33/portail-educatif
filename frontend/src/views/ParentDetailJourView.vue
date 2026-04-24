<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/services/api'

const route = useRoute()

const donnees = ref(null)
const erreur = ref('')
const chargement = ref(true)

const eleveId = computed(() => route.params.eleveId)
const date = computed(() => route.params.date)

function formaterHeure(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

function formaterSecondes(s) {
  if (!s) return ''
  const minutes = Math.floor(s / 60)
  const secondes = s % 60
  if (minutes === 0) return `${secondes}s`
  return `${minutes} min ${secondes.toString().padStart(2, '0')}s`
}

async function charger() {
  chargement.value = true
  erreur.value = ''
  try {
    const { data } = await api.get(
      `/parent/suivi/${eleveId.value}/jour/${date.value}/`,
    )
    donnees.value = data
  } catch (e) {
    if (e.response?.status === 400) {
      erreur.value = 'Format de date invalide.'
    } else if (e.response?.status === 403) {
      erreur.value = "Cet élève n'est pas rattaché à votre famille."
    } else {
      erreur.value = 'Impossible de charger la journée.'
    }
  } finally {
    chargement.value = false
  }
}

onMounted(charger)
watch([eleveId, date], charger)
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
          Journée du {{ date }}
        </h1>
      </div>
    </header>

    <main class="max-w-4xl mx-auto px-4 py-6 sm:px-6 sm:py-8 space-y-6">
      <p v-if="chargement" class="text-slate-500">Chargement…</p>
      <p v-else-if="erreur" class="text-red-600">{{ erreur }}</p>
      <p
        v-else-if="donnees && donnees.activites.length === 0"
        class="text-slate-600"
      >
        Pas d'activité enregistrée ce jour-là.
      </p>

      <template v-else-if="donnees">
        <article
          v-for="entree in donnees.activites"
          :key="entree.thematique.id"
          class="bg-white rounded-lg shadow-sm border border-slate-200 p-5 sm:p-6 space-y-3"
        >
          <header class="flex items-start justify-between gap-4">
            <div>
              <span
                class="inline-block px-2 py-0.5 rounded text-xs font-medium text-white"
                :style="{ backgroundColor: entree.thematique.matiere.couleur }"
              >
                {{ entree.thematique.matiere.nom }}
              </span>
              <h2 class="mt-1 text-lg font-semibold text-slate-800">
                {{ entree.thematique.titre }}
              </h2>
            </div>
          </header>

          <div class="grid gap-3 sm:grid-cols-2 text-sm">
            <div v-if="entree.lecture" class="border border-slate-100 rounded p-3">
              <p class="font-medium text-slate-700">Leçon lue</p>
              <p class="text-slate-500">
                à {{ formaterHeure(entree.lecture.date_fin_lecture) }}
                <span v-if="entree.lecture.temps_passe_secondes">
                  — durée : {{ formaterSecondes(entree.lecture.temps_passe_secondes) }}
                </span>
              </p>
            </div>
            <div v-else class="border border-dashed border-slate-200 rounded p-3 text-slate-400">
              Leçon non lue ce jour-là
            </div>

            <div v-if="entree.tentative" class="border border-slate-100 rounded p-3">
              <p class="font-medium text-slate-700">QCM terminé</p>
              <p class="text-slate-500">
                Score : {{ entree.tentative.score }} / {{ entree.tentative.total_questions }}
                ({{
                  entree.tentative.total_questions
                    ? Math.round(
                        (100 * entree.tentative.score) / entree.tentative.total_questions,
                      )
                    : 0
                }}%)
                — à {{ formaterHeure(entree.tentative.date_fin) }}
              </p>
            </div>
            <div v-else class="border border-dashed border-slate-200 rounded p-3 text-slate-400">
              QCM non passé ce jour-là
            </div>
          </div>

          <div v-if="entree.questions.length" class="pt-2">
            <p class="font-medium text-slate-700 mb-2">
              Questions posées à l'IA ({{ entree.questions.length }})
            </p>
            <ul class="space-y-2">
              <li
                v-for="q in entree.questions"
                :key="q.id"
                class="border-l-4 border-indigo-200 pl-3"
              >
                <p class="text-slate-800">« {{ q.question }} »</p>
                <p class="text-xs text-slate-400 mt-0.5">
                  {{ formaterHeure(q.date) }}
                </p>
              </li>
            </ul>
          </div>
        </article>
      </template>
    </main>
  </div>
</template>
