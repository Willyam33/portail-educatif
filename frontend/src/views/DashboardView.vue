<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const thematique = ref(null)
const progression = ref(null)
const erreur = ref('')
const chargement = ref(true)

async function charger() {
  chargement.value = true
  erreur.value = ''
  try {
    const [reponseThematique, reponseProg] = await Promise.all([
      api.get('/eleve/thematique-du-jour/'),
      api.get('/eleve/progression/'),
    ])
    thematique.value = reponseThematique.data
    progression.value = reponseProg.data
  } catch (e) {
    if (e.response?.status === 404) {
      erreur.value = "Aucune thématique n'est disponible pour l'instant."
    } else {
      erreur.value = 'Impossible de charger le tableau de bord.'
    }
  } finally {
    chargement.value = false
  }
}

function commencerLecon() {
  router.push(`/thematique/${thematique.value.id}/lecon`)
}

function lancerQCM() {
  router.push(`/thematique/${thematique.value.id}/qcm`)
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
      <div class="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
        <div>
          <h1 class="text-xl font-semibold text-slate-800">Bonjour, {{ auth.utilisateur?.first_name || auth.utilisateur?.username }}</h1>
          <p class="text-sm text-slate-500">Portail éducatif — 3<sup>e</sup></p>
        </div>
        <button
          type="button"
          class="text-sm text-slate-600 hover:text-slate-900 underline"
          @click="deconnexion"
        >
          Se déconnecter
        </button>
      </div>
    </header>

    <main class="max-w-4xl mx-auto px-6 py-8 space-y-6">
      <p v-if="chargement" class="text-slate-500">Chargement…</p>
      <p v-else-if="erreur" class="text-red-600">{{ erreur }}</p>

      <section
        v-else-if="thematique"
        class="bg-white rounded-lg shadow-sm border border-slate-200 p-6 space-y-4"
      >
        <div class="flex items-start justify-between">
          <div>
            <span
              class="inline-block px-2 py-0.5 rounded text-xs font-medium text-white"
              :style="{ backgroundColor: thematique.matiere.couleur }"
            >
              {{ thematique.matiere.nom }}
            </span>
            <h2 class="mt-2 text-2xl font-semibold text-slate-800">
              {{ thematique.titre }}
            </h2>
            <p class="text-sm text-slate-500 mt-1">
              Jour {{ thematique.jour_courant }} / 180
            </p>
          </div>
        </div>

        <p v-if="thematique.objectifs_apprentissage" class="text-slate-700 whitespace-pre-line">
          {{ thematique.objectifs_apprentissage }}
        </p>

        <div class="flex gap-3 pt-2">
          <button
            type="button"
            :disabled="!thematique.lecon_disponible"
            class="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            @click="commencerLecon"
          >
            {{ thematique.lecon_disponible ? 'Lire la leçon' : 'Leçon en préparation' }}
          </button>
          <button
            type="button"
            :disabled="!thematique.qcm_disponible"
            class="bg-emerald-600 text-white px-4 py-2 rounded hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
            @click="lancerQCM"
          >
            {{ thematique.qcm_disponible ? 'Passer le QCM' : 'QCM en préparation' }}
          </button>
        </div>
      </section>

      <section
        v-if="progression"
        class="bg-white rounded-lg shadow-sm border border-slate-200 p-6"
      >
        <h3 class="text-lg font-semibold text-slate-800 mb-3">Ma progression</h3>
        <div class="grid grid-cols-3 gap-4 text-center">
          <div>
            <p class="text-2xl font-semibold text-slate-800">{{ progression.lecons_lues }}</p>
            <p class="text-xs text-slate-500">leçons lues</p>
          </div>
          <div>
            <p class="text-2xl font-semibold text-slate-800">{{ progression.qcm_termines }}</p>
            <p class="text-xs text-slate-500">QCM terminés</p>
          </div>
          <div>
            <p class="text-2xl font-semibold text-slate-800">
              {{ progression.score_moyen_pourcent !== null ? progression.score_moyen_pourcent + '%' : '—' }}
            </p>
            <p class="text-xs text-slate-500">score moyen</p>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>
