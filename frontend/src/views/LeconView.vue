<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MarkdownIt from 'markdown-it'
import texmath from 'markdown-it-texmath'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import { api } from '@/services/api'
import QuestionsLibres from '@/components/QuestionsLibres.vue'

const route = useRoute()
const router = useRouter()

const donnees = ref(null)
const erreur = ref('')
const chargement = ref(true)

// Markdown-it configuré avec rendu KaTeX pour les formules $...$ et $$...$$.
const md = new MarkdownIt({ html: false, linkify: true, breaks: false }).use(
  texmath,
  { engine: katex, delimiters: 'dollars' },
)

const contenuHtml = computed(() => {
  if (!donnees.value?.lecon?.contenu) return ''
  return md.render(donnees.value.lecon.contenu)
})

async function charger() {
  chargement.value = true
  try {
    const { data } = await api.get(`/eleve/thematiques/${route.params.id}/lecon/`)
    donnees.value = data
  } catch (e) {
    erreur.value =
      e.response?.status === 404
        ? 'Aucune leçon pour cette thématique.'
        : 'Impossible de charger la leçon.'
  } finally {
    chargement.value = false
  }
}

async function marquerLueEtPasserAuQCM() {
  try {
    await api.post(`/eleve/thematiques/${route.params.id}/lecon/marquer-lue/`)
  } catch {
    /* on continue même si le marquage rate */
  }
  router.push(`/thematique/${route.params.id}/qcm`)
}

function retour() {
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
          @click="retour"
        >
          ← Retour
        </button>
        <button
          v-if="donnees"
          type="button"
          class="bg-emerald-600 text-white text-sm px-3 py-1.5 rounded hover:bg-emerald-700"
          @click="marquerLueEtPasserAuQCM"
        >
          J'ai lu, passer au QCM →
        </button>
      </div>
    </header>

    <main class="max-w-3xl mx-auto px-6 py-8">
      <p v-if="chargement" class="text-slate-500">Chargement…</p>
      <p v-else-if="erreur" class="text-red-600">{{ erreur }}</p>

      <template v-else-if="donnees">
        <article class="bg-white rounded-lg shadow-sm border border-slate-200 p-8">
          <div class="mb-4">
            <span
              class="inline-block px-2 py-0.5 rounded text-xs font-medium text-white"
              :style="{ backgroundColor: donnees.thematique.matiere.couleur }"
            >
              {{ donnees.thematique.matiere.nom }}
            </span>
            <span class="text-sm text-slate-500 ml-2">
              Durée de lecture estimée : {{ donnees.lecon.duree_lecture_estimee }} min
            </span>
          </div>

          <div class="lecon-contenu" v-html="contenuHtml" />
        </article>

        <div class="mt-6">
          <QuestionsLibres :thematique-id="donnees.thematique.id" />
        </div>
      </template>
    </main>
  </div>
</template>

<style>
/* Styles de rendu pour le contenu Markdown de la leçon. Tailwind n'applique
   pas ses classes aux éléments générés dynamiquement par v-html, d'où ces
   règles CSS globales ciblées sur .lecon-contenu. */
.lecon-contenu h1 {
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: 1rem;
  color: #1e293b;
}
.lecon-contenu h2 {
  font-size: 1.35rem;
  font-weight: 600;
  margin-top: 1.75rem;
  margin-bottom: 0.75rem;
  color: #1e293b;
}
.lecon-contenu h3 {
  font-size: 1.1rem;
  font-weight: 600;
  margin-top: 1.25rem;
  margin-bottom: 0.5rem;
  color: #334155;
}
.lecon-contenu p {
  margin-bottom: 0.85rem;
  line-height: 1.65;
  color: #334155;
}
.lecon-contenu ul,
.lecon-contenu ol {
  padding-left: 1.5rem;
  margin-bottom: 0.85rem;
  color: #334155;
}
.lecon-contenu ul {
  list-style-type: disc;
}
.lecon-contenu ol {
  list-style-type: decimal;
}
.lecon-contenu li {
  margin-bottom: 0.35rem;
  line-height: 1.6;
}
.lecon-contenu blockquote {
  border-left: 4px solid #c7d2fe;
  background-color: #f1f5f9;
  padding: 0.6rem 1rem;
  margin: 1rem 0;
  color: #475569;
  font-style: italic;
}
.lecon-contenu strong {
  color: #1e293b;
  font-weight: 600;
}
.lecon-contenu code {
  background-color: #e2e8f0;
  padding: 0.1rem 0.35rem;
  border-radius: 0.25rem;
  font-size: 0.9em;
}
</style>
