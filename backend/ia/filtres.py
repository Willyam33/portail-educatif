"""
Filtrage des questions libres avant envoi à l'API Anthropic (voir specs §6.1).

Logique volontairement simple : détection par mot-clé (accent / casse ignorés,
frontières de mots quand c'est pertinent). Le but est d'intercepter l'essentiel
sans prétendre à une modération exhaustive — l'IA elle-même reprend la main en
aval via son prompt système.
"""

from __future__ import annotations

import re
import unicodedata


# Mots-clés interdits, classés par catégorie pour faciliter la maintenance.
# On cherche ces motifs en sous-chaîne dans le texte normalisé.
_MOTS_CLES_INTERDITS = [
    # Violence / auto-agression
    "suicide", "me tuer", "se tuer", "me pendre", "me suicider",
    "automutilation", "me mutiler", "m'automutiler", "me faire du mal",
    "attentat", "arme a feu", "fabriquer une bombe",
    # Drogues
    "cocaine", "heroine", "crack meth", "methamphetamine", "ecstasy", "lsd",
    "mdma", "crystal meth", "acheter de la drogue", "ou trouver de la drogue",
    "dose mortelle", "doser la",
    # Sexualité hors programme
    "pornographie", "porno", "pornographique",
    # Conduites à risque
    "pro ana", "pro-ana", "pro mia", "pro-mia",
    "regime drastique", "jeuner plusieurs jours", "vomir apres avoir mange",
    # Contournement / prompt injection
    "ignore tes instructions", "ignore les instructions", "ignore ton prompt",
    "oublie tes instructions", "oublie le prompt",
    "comporte-toi comme", "comporte toi comme", "fais semblant d'etre",
    "ton vrai role", "ton role reel", "tu es en realite",
    "developer mode", "mode developpeur", "jailbreak",
]


def _normaliser(texte: str) -> str:
    """Minuscule + suppression des accents, pour matcher sans se soucier de la casse."""
    sans_accents = unicodedata.normalize("NFKD", texte)
    sans_accents = "".join(c for c in sans_accents if not unicodedata.combining(c))
    return sans_accents.lower()


def contient_mot_clef_interdit(question: str) -> bool:
    """Retourne True si la question contient un mot-clé interdit."""
    if not question:
        return False
    normalise = _normaliser(question)
    # On collapse les espaces multiples pour limiter les tentatives de contournement triviales.
    normalise = re.sub(r"\s+", " ", normalise)
    return any(mot in normalise for mot in _MOTS_CLES_INTERDITS)
