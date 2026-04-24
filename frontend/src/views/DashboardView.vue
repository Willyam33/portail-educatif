<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const thematique = ref(null)
const progression = ref(null)
const matieres = ref([])
const matiereOuverteId = ref(null)
const erreur = ref('')
const chargement = ref(true)

const dateAujourdhui = computed(() =>
  new Date().toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }),
)

const joursAvantBrevet = computed(() => {
  const aujourdhui = new Date()
  aujourdhui.setHours(0, 0, 0, 0)
  let brevet = new Date(aujourdhui.getFullYear(), 5, 26)
  if (brevet < aujourdhui) {
    brevet = new Date(aujourdhui.getFullYear() + 1, 5, 26)
  }
  return Math.round((brevet - aujourdhui) / 86_400_000)
})

const totalLecons = computed(() =>
  matieres.value.reduce(
    (sum, item) => sum + item.thematiques.filter((t) => t.lecon_disponible).length,
    0,
  ),
)

const totalQCM = computed(() =>
  matieres.value.reduce(
    (sum, item) => sum + item.thematiques.filter((t) => t.qcm_disponible).length,
    0,
  ),
)

async function charger() {
  chargement.value = true
  erreur.value = ''
  try {
    const [reponseThematique, reponseProg, reponseMatieres] = await Promise.all([
      api.get('/eleve/thematique-du-jour/').catch(() => ({ data: null })),
      api.get('/eleve/progression/'),
      api.get('/eleve/matieres/'),
    ])
    thematique.value = reponseThematique.data
    progression.value = reponseProg.data
    matieres.value = reponseMatieres.data
  } catch {
    erreur.value = 'Impossible de charger le tableau de bord.'
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

function basculerMatiere(matiereId) {
  matiereOuverteId.value = matiereOuverteId.value === matiereId ? null : matiereId
}

function ouvrirThematique(t) {
  if (t.lecon_disponible) {
    router.push(`/thematique/${t.id}/lecon`)
  } else if (t.qcm_disponible) {
    router.push(`/thematique/${t.id}/qcm`)
  }
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
        <nav class="flex items-center gap-4 text-sm">
          <router-link to="/historique" class="text-slate-600 hover:text-slate-900">
            Historique
          </router-link>
          <router-link to="/progression" class="text-slate-600 hover:text-slate-900">
            Progression
          </router-link>
          <button
            type="button"
            class="text-slate-600 hover:text-slate-900 underline"
            @click="deconnexion"
          >
            Se déconnecter
          </button>
        </nav>
      </div>
    </header>

    <main class="max-w-4xl mx-auto px-6 py-8 space-y-6">
      <p v-if="chargement" class="text-slate-500">Chargement…</p>
      <p v-else-if="erreur" class="text-red-600">{{ erreur }}</p>

      <template v-else>
        <section
          v-if="thematique"
          class="bg-white rounded-lg shadow-sm border border-slate-200 p-6 space-y-4"
        >
          <div class="flex items-baseline justify-between border-b border-slate-100 pb-3">
            <p class="text-sm text-slate-500">Suggestion du {{ dateAujourdhui }}</p>
            <p class="text-sm font-medium text-indigo-700">
              Brevet des collèges — J-{{ joursAvantBrevet }}
            </p>
          </div>
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
              <p class="text-2xl font-semibold text-slate-800">
                {{ progression.lecons_lues }} / {{ totalLecons }}
              </p>
              <p class="text-xs text-slate-500">leçons lues</p>
            </div>
            <div>
              <p class="text-2xl font-semibold text-slate-800">
                {{ progression.qcm_termines }} / {{ totalQCM }}
              </p>
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

        <section
          v-if="matieres.length"
          class="bg-white rounded-lg shadow-sm border border-slate-200 p-6"
        >
          <h3 class="text-lg font-semibold text-slate-800 mb-4">Explorer par matière</h3>
          <div class="space-y-2">
            <div
              v-for="item in matieres"
              :key="item.matiere.id"
              class="border border-slate-200 rounded-lg overflow-hidden"
            >
              <button
                type="button"
                class="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50"
                @click="basculerMatiere(item.matiere.id)"
              >
                <div class="flex items-center gap-3">
                  <span
                    class="inline-block w-3 h-3 rounded-full"
                    :style="{ backgroundColor: item.matiere.couleur }"
                  />
                  <span class="font-medium text-slate-800">{{ item.matiere.nom }}</span>
                  <span class="text-xs text-slate-500">
                    {{ item.thematiques.filter((t) => t.lecon_disponible).length }} /
                    {{ item.thematiques.length }} leçon(s) disponible(s)
                  </span>
                </div>
                <span class="text-slate-400 text-sm">
                  {{ matiereOuverteId === item.matiere.id ? '▾' : '▸' }}
                </span>
              </button>

              <ul
                v-if="matiereOuverteId === item.matiere.id"
                class="border-t border-slate-200 divide-y divide-slate-100"
              >
                <li
                  v-for="t in item.thematiques"
                  :key="t.id"
                  class="px-4 py-2.5 flex items-center justify-between hover:bg-slate-50"
                  :class="{
                    'cursor-pointer': t.lecon_disponible || t.qcm_disponible,
                    'opacity-60': !t.lecon_disponible && !t.qcm_disponible,
                  }"
                  @click="ouvrirThematique(t)"
                >
                  <div class="flex items-center gap-3 min-w-0">
                    <span class="text-xs text-slate-400 w-7 shrink-0">#{{ t.numero_dans_matiere }}</span>
                    <span class="text-sm text-slate-700 truncate">{{ t.titre }}</span>
                  </div>
                  <div class="flex items-center gap-2 shrink-0 text-xs">
                    <span v-if="t.qcm_termine" class="px-2 py-0.5 rounded bg-emerald-100 text-emerald-700">
                      QCM terminé
                    </span>
                    <span v-else-if="t.lecon_lue" class="px-2 py-0.5 rounded bg-indigo-100 text-indigo-700">
                      Leçon lue
                    </span>
                    <span v-else-if="t.lecon_disponible" class="px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                      Disponible
                    </span>
                    <span v-else class="px-2 py-0.5 rounded bg-slate-50 text-slate-400">
                      À venir
                    </span>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>
