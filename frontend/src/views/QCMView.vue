<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/services/api'
import TexteRiche from '@/components/TexteRiche.vue'

const route = useRoute()
const router = useRouter()

const donnees = ref(null)
const erreur = ref('')
const chargement = ref(true)

// Index de la question affichée actuellement.
const indexCourant = ref(0)

// Pour chaque question_id : { proposition_choisie_id, correcte, explication_generale, propositions[] }
const corrections = ref({})
// Pendant l'envoi pour éviter les doubles clics.
const envoiEnCours = ref(false)
// Score final (après /terminer/).
const scoreFinal = ref(null)

const questionCourante = computed(() => donnees.value?.questions?.[indexCourant.value])
const nbQuestions = computed(() => donnees.value?.questions?.length || 0)
const correctionCourante = computed(() =>
  questionCourante.value ? corrections.value[questionCourante.value.id] : null,
)
const toutesRepondues = computed(() =>
  donnees.value?.questions?.every((q) => corrections.value[q.id]),
)

async function charger() {
  chargement.value = true
  try {
    const { data } = await api.get(`/eleve/thematiques/${route.params.id}/qcm/`)
    donnees.value = data
    // Réhydrate les réponses déjà données pour une reprise de session.
    if (data.reponses_deja_donnees) {
      for (const [qid, info] of Object.entries(data.reponses_deja_donnees)) {
        // On ne connait pas l'explication à ce stade : on la rechargera au clic suivant.
        // Pour une UX propre, on marque la question répondue sans détails.
        corrections.value[qid] = {
          proposition_choisie_id: info.proposition_choisie_id,
          correcte: info.correcte,
          propositions: [],
          explication_generale: '',
          partielle: true,
        }
      }
    }
  } catch {
    erreur.value = 'Impossible de charger le QCM.'
  } finally {
    chargement.value = false
  }
}

async function repondre(proposition) {
  if (envoiEnCours.value || correctionCourante.value) return
  envoiEnCours.value = true
  try {
    const { data } = await api.post(
      `/eleve/tentatives/${donnees.value.tentative_id}/repondre/`,
      {
        question_id: questionCourante.value.id,
        proposition_choisie_id: proposition.id,
      },
    )
    corrections.value[questionCourante.value.id] = { ...data, partielle: false }
  } catch {
    erreur.value = "Impossible d'envoyer la réponse."
  } finally {
    envoiEnCours.value = false
  }
}

function suivante() {
  if (indexCourant.value < nbQuestions.value - 1) {
    indexCourant.value += 1
  }
}

function precedente() {
  if (indexCourant.value > 0) {
    indexCourant.value -= 1
  }
}

async function terminer() {
  try {
    const { data } = await api.post(
      `/eleve/tentatives/${donnees.value.tentative_id}/terminer/`,
    )
    scoreFinal.value = data
  } catch {
    erreur.value = 'Impossible de terminer le QCM.'
  }
}

function estChoisie(propId) {
  return correctionCourante.value?.proposition_choisie_id === propId
}

function classeProp(prop) {
  const corr = correctionCourante.value
  if (!corr) return 'border-slate-300 hover:border-indigo-500 hover:bg-indigo-50'
  if (corr.partielle) {
    // Pas de détails : seule la proposition choisie est colorée
    if (estChoisie(prop.id)) {
      return corr.correcte
        ? 'border-emerald-500 bg-emerald-50'
        : 'border-red-500 bg-red-50'
    }
    return 'border-slate-200 opacity-60'
  }
  // Correction complète : on colore toutes les propositions
  const infosProp = corr.propositions.find((p) => p.id === prop.id)
  if (infosProp?.est_correcte) return 'border-emerald-500 bg-emerald-50'
  if (estChoisie(prop.id)) return 'border-red-500 bg-red-50'
  return 'border-slate-200 opacity-60'
}

function classeIndicateur(index) {
  const q = donnees.value.questions[index]
  const corr = corrections.value[q.id]
  if (!corr) return 'bg-slate-200 text-slate-600'
  return corr.correcte ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'
}

function revenirAuDashboard() {
  router.push('/')
}

onMounted(charger)
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <header class="bg-white border-b border-slate-200 sticky top-0 z-10">
      <div class="max-w-3xl mx-auto px-6 py-3 flex items-center justify-between">
        <button
          type="button"
          class="text-sm text-slate-600 hover:text-slate-900"
          @click="revenirAuDashboard"
        >
          ← Retour
        </button>
        <div v-if="donnees && !scoreFinal" class="flex items-center gap-1.5">
          <span
            v-for="(q, i) in donnees.questions"
            :key="q.id"
            class="inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-semibold cursor-pointer"
            :class="[
              classeIndicateur(i),
              i === indexCourant ? 'ring-2 ring-offset-1 ring-indigo-500' : '',
            ]"
            @click="indexCourant = i"
          >
            {{ i + 1 }}
          </span>
        </div>
      </div>
    </header>

    <main class="max-w-3xl mx-auto px-6 py-8">
      <p v-if="chargement" class="text-slate-500">Chargement…</p>
      <p v-else-if="erreur" class="text-red-600">{{ erreur }}</p>

      <!-- Écran de résultat -->
      <section
        v-else-if="scoreFinal"
        class="bg-white rounded-lg shadow-sm border border-slate-200 p-8 text-center space-y-4"
      >
        <h2 class="text-3xl font-semibold text-slate-800">QCM terminé !</h2>
        <p class="text-5xl font-bold text-indigo-600">
          {{ scoreFinal.score }} / {{ scoreFinal.total_questions }}
        </p>
        <p class="text-slate-600">
          {{
            scoreFinal.score === scoreFinal.total_questions
              ? 'Bravo, tout juste !'
              : scoreFinal.score >= scoreFinal.total_questions / 2
                ? 'Bon travail, continue comme ça.'
                : 'Pas de panique, relis la leçon et réessaie.'
          }}
        </p>
        <button
          type="button"
          class="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
          @click="revenirAuDashboard"
        >
          Retour au tableau de bord
        </button>
      </section>

      <!-- Écran de question -->
      <section
        v-else-if="questionCourante"
        class="bg-white rounded-lg shadow-sm border border-slate-200 p-8 space-y-5"
      >
        <p class="text-sm text-slate-500">
          Question {{ indexCourant + 1 }} / {{ nbQuestions }}
        </p>
        <h2 class="text-xl font-semibold text-slate-800">
          <TexteRiche :texte="questionCourante.enonce" inline />
        </h2>

        <div class="space-y-3">
          <button
            v-for="prop in questionCourante.propositions"
            :key="prop.id"
            type="button"
            :disabled="!!correctionCourante || envoiEnCours"
            class="w-full text-left border-2 rounded-lg px-4 py-3 transition disabled:cursor-default"
            :class="classeProp(prop)"
            @click="repondre(prop)"
          >
            <span class="font-medium">
              <TexteRiche :texte="prop.texte" inline />
            </span>
            <p
              v-if="correctionCourante && !correctionCourante.partielle"
              class="mt-1 text-sm text-slate-600"
            >
              <TexteRiche
                :texte="correctionCourante.propositions.find((p) => p.id === prop.id)?.explication || ''"
                inline
              />
            </p>
          </button>
        </div>

        <div
          v-if="correctionCourante && !correctionCourante.partielle"
          class="bg-slate-50 border border-slate-200 rounded p-4 text-sm text-slate-700"
        >
          <strong>Explication :</strong>
          <TexteRiche :texte="correctionCourante.explication_generale" inline />
        </div>

        <div class="flex justify-between pt-2">
          <button
            type="button"
            :disabled="indexCourant === 0"
            class="text-sm text-slate-600 disabled:opacity-40"
            @click="precedente"
          >
            ← Précédente
          </button>
          <button
            v-if="indexCourant < nbQuestions - 1"
            type="button"
            :disabled="!correctionCourante"
            class="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 disabled:opacity-40"
            @click="suivante"
          >
            Suivante →
          </button>
          <button
            v-else
            type="button"
            :disabled="!toutesRepondues"
            class="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700 disabled:opacity-40"
            @click="terminer"
          >
            Terminer le QCM
          </button>
        </div>
      </section>
    </main>
  </div>
</template>
