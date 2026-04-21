<script setup>
import { ref, onMounted } from 'vue'
import { api } from '@/services/api.js'

const etatBackend = ref(null)
const erreur = ref(null)

onMounted(async () => {
  try {
    const { data } = await api.get('/ping/')
    etatBackend.value = data
  } catch (e) {
    erreur.value = e.message
  }
})
</script>

<template>
  <main class="mx-auto max-w-2xl px-6 py-12">
    <h1 class="text-3xl font-bold text-gray-900">Portail éducatif</h1>
    <p class="mt-2 text-gray-600">
      Socle technique initialisé. Cette page vérifie la communication avec le back-end.
    </p>

    <section class="mt-8 rounded-lg border bg-white p-6 shadow-sm">
      <h2 class="text-lg font-semibold text-gray-900">État du back-end</h2>

      <div v-if="etatBackend" class="mt-3 text-sm">
        <p>
          <span class="font-medium">Statut :</span>
          <span class="ml-1 inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-green-800">
            {{ etatBackend.statut }}
          </span>
        </p>
        <p><span class="font-medium">Service :</span> {{ etatBackend.service }}</p>
        <p><span class="font-medium">Version :</span> {{ etatBackend.version }}</p>
      </div>

      <div v-else-if="erreur" class="mt-3 rounded bg-red-50 p-3 text-sm text-red-800">
        Impossible de joindre le back-end : {{ erreur }}
      </div>

      <div v-else class="mt-3 text-sm text-gray-500">Chargement…</div>
    </section>
  </main>
</template>
