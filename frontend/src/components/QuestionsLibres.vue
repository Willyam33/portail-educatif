<script setup>
import { computed, onMounted, ref } from 'vue'
import MarkdownIt from 'markdown-it'
import texmath from 'markdown-it-texmath'
import katex from 'katex'
import { api } from '@/services/api'

const props = defineProps({
  thematiqueId: { type: [Number, String], required: true },
})

const md = new MarkdownIt({ html: false, linkify: true, breaks: true }).use(
  texmath,
  { engine: katex, delimiters: 'dollars' },
)

const questions = ref([])
const nbRestantes = ref(null)
const maxParJour = ref(null)
const chargement = ref(true)
const envoiEnCours = ref(false)
const erreur = ref('')
const nouvelleQuestion = ref('')

const limiteAtteinte = computed(() => nbRestantes.value === 0)

async function charger() {
  chargement.value = true
  erreur.value = ''
  try {
    const { data } = await api.get(
      `/eleve/thematiques/${props.thematiqueId}/questions-libres/`,
    )
    questions.value = data.questions
    nbRestantes.value = data.nb_restantes_aujourdhui
    maxParJour.value = data.max_par_jour
  } catch {
    erreur.value = "Impossible de charger l'historique des questions."
  } finally {
    chargement.value = false
  }
}

async function envoyer() {
  const texte = nouvelleQuestion.value.trim()
  if (!texte || envoiEnCours.value) return
  envoiEnCours.value = true
  erreur.value = ''
  try {
    const { data } = await api.post(
      `/eleve/thematiques/${props.thematiqueId}/questions-libres/`,
      { question: texte },
    )
    questions.value = [...questions.value, data.question]
    nbRestantes.value = data.nb_restantes_aujourdhui
    nouvelleQuestion.value = ''
  } catch (e) {
    if (e.response?.status === 429) {
      erreur.value = e.response.data.detail
      nbRestantes.value = 0
    } else if (e.response?.data?.detail) {
      erreur.value = e.response.data.detail
    } else {
      erreur.value = "Une erreur est survenue, réessaie plus tard."
    }
  } finally {
    envoiEnCours.value = false
  }
}

function rendre(texte) {
  return md.render(texte || '')
}

onMounted(charger)
</script>

<template>
  <section class="bg-white rounded-lg shadow-sm border border-slate-200 p-6 space-y-4">
    <div class="flex items-baseline justify-between">
      <h3 class="text-lg font-semibold text-slate-800">Poser une question à l'IA</h3>
      <span v-if="maxParJour !== null" class="text-xs text-slate-500">
        {{ nbRestantes }} / {{ maxParJour }} questions restantes aujourd'hui
      </span>
    </div>

    <p v-if="chargement" class="text-sm text-slate-500">Chargement…</p>

    <div v-else class="space-y-4">
      <div v-if="questions.length > 0" class="space-y-3">
        <div
          v-for="q in questions"
          :key="q.id"
          class="border border-slate-200 rounded-lg p-3 bg-slate-50"
        >
          <p class="text-sm font-medium text-slate-700">
            <span class="text-indigo-600">Toi :</span> {{ q.question }}
          </p>
          <div
            class="mt-2 text-sm text-slate-700 reponse-ia"
            v-html="rendre(q.reponse)"
          />
        </div>
      </div>
      <p v-else class="text-sm text-slate-500 italic">
        Pas encore de question sur cette leçon. Lance-toi !
      </p>

      <form class="space-y-2" @submit.prevent="envoyer">
        <textarea
          v-model="nouvelleQuestion"
          rows="3"
          maxlength="1000"
          :disabled="limiteAtteinte || envoiEnCours"
          placeholder="Tape ta question ici (par ex. : peux-tu me redonner un exemple concret ?)"
          class="w-full border border-slate-300 rounded p-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-100"
        />
        <div class="flex items-center justify-between">
          <p v-if="erreur" class="text-sm text-red-600">{{ erreur }}</p>
          <p v-else class="text-xs text-slate-400">
            L'IA s'appuie sur la leçon ci-dessus pour te répondre.
          </p>
          <button
            type="submit"
            :disabled="limiteAtteinte || envoiEnCours || !nouvelleQuestion.trim()"
            class="bg-indigo-600 text-white text-sm px-4 py-2 rounded hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ envoiEnCours ? 'Envoi…' : 'Envoyer' }}
          </button>
        </div>
      </form>
    </div>
  </section>
</template>

<style scoped>
.reponse-ia :deep(p) {
  margin-bottom: 0.5rem;
  line-height: 1.55;
}
.reponse-ia :deep(strong) {
  color: #1e293b;
  font-weight: 600;
}
.reponse-ia :deep(ul),
.reponse-ia :deep(ol) {
  padding-left: 1.25rem;
  margin-bottom: 0.5rem;
}
.reponse-ia :deep(ul) {
  list-style-type: disc;
}
.reponse-ia :deep(ol) {
  list-style-type: decimal;
}
.reponse-ia :deep(code) {
  background-color: #e2e8f0;
  padding: 0.05rem 0.25rem;
  border-radius: 0.25rem;
  font-size: 0.9em;
}
</style>
