"""Configurazione della ricerca. Modifica qui keyword e filtri."""
import re

# Termini principali (sezione A del report)
CORE_QUERIES = ["psychomotricien", "psychomotricienne", "psychomotricité"]
CORE_TITLE_RE = re.compile(r"psychomotric", re.I)

# Lavori affini (sezione B): infanzia, educazione, sostegno, baby-sitting
RELATED_QUERIES = [
    "éducatrice de l'enfance", "éducateur de l'enfance", "assistant socio-éducatif",
    "éducateur spécialisé", "éducatrice sociale", "enseignant spécialisé",
    "baby-sitter", "nanny", "garde d'enfants", "maman de jour", "accueillante familiale",
    "parascolaire", "auxiliaire de l'enfance", "ergothérapeute", "logopédiste",
    "accompagnant handicap", "aide en crèche",
]
RELATED_TITLE_RE = re.compile(
    r"(é|e)ducat(eur|rice)|socio[- ]?(é|e)ducati|\bASE\b|enfance|cr(è|e)che|garderie|"
    r"nanny|nounou|baby[- ]?sit|garde d'enfant|maman de jour|accueillant|parascolaire|"
    r"enseignant[e·.-]* sp(é|e)cialis|ergoth(é|e)rap|logop(é|e)d|psychomotric|"
    r"p(é|e)dagog|animat(eur|rice)|accompagnant",
    re.I,
)
# Esclusioni nel titolo (rumore tipico)
RELATED_EXCLUDE_RE = re.compile(r"\bEMS\b|stagiaire|apprenti|directeur|directrice|chef|responsable de secteur|infirmi|secr(é|e)taire|comptable", re.I)

# Località: Ginevra + Vaud (jobup interpreta il parametro location)
LOCATIONS = ["Genève", "Nyon"]  # aggiungi "Lausanne" per allargare

# Località in Svizzera tedesca da scartare (annunci Psychomotoriktherapeut)
GERMAN_RE = re.compile(r"Psychomotorik|Therapeut", re.I)

# Massima età (giorni) per i lavori affini
RELATED_MAX_AGE_DAYS = 21

# Annunci chiusi/scaduti da non segnalare più (id jobup/jobs.ch)
CLOSED_IDS = {
    "2700f864-cd9d-4b6d-a218-d1643fd367ad",  # Etat de Vaud, Responsable d'équipe, Puidoux (scad. 30.09.2026)
    "c4ec1d38-b561-4c04-9399-5c720747abd2",  # Croix-Rouge fribourgeoise 20% (scad. 27.09.2026)
    "7323763a-f185-4554-87d7-da219b52c239",
}
