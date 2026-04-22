<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import texmath from 'markdown-it-texmath'
import katex from 'katex'
import 'katex/dist/katex.min.css'

const props = defineProps({
  texte: { type: String, default: '' },
  // `inline` désactive le rendu bloc (<p>) pour rester dans le flux d'un bouton
  // ou d'un titre. Idéal pour une proposition ou un énoncé court.
  inline: { type: Boolean, default: false },
})

const md = new MarkdownIt({ html: false, linkify: false, breaks: false }).use(
  texmath,
  { engine: katex, delimiters: 'dollars' },
)

const contenuHtml = computed(() => {
  if (!props.texte) return ''
  return props.inline ? md.renderInline(props.texte) : md.render(props.texte)
})
</script>

<template>
  <span v-if="inline" v-html="contenuHtml" />
  <div v-else v-html="contenuHtml" />
</template>
