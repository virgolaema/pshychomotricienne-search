# psychomotricienne-search

Ricerca settimanale di offerte **psychomotricien(ne) / psychomotricité** a Ginevra, Vaud e dintorni,
più una sezione di **lavori affini** (éducatrice de l'enfance, ASE, educatrice specializzata,
baby-sitting/nanny, parascolaire, ergoterapia, logopedia). Il report arriva via email da Gmail
ogni lunedì mattina tramite GitHub Actions.

## Fonti
| Fonte | Metodo |
|---|---|
| jobup.ch, jobs.ch | API pubblica JobCloud (`/api/v1/public/search`) |
| HUG | API SmartRecruiters (fonte autorevole per gli annunci HUG) |
| AVOP (istituzioni sociali vaudesi) | HTML `avop.ch/job_posts` |
| Ville de Genève, petite enfance | HTML `geneve.ch/demarches/offres-emploi-petite-enfance` |
| Etat de Genève | HTML `ge.ch/offres-emploi-etat-geneve/liste-offres` |
| educh.ch | conteggio offerte pagina psychomotricité |

Non coperte (SPA/login): CHUV, portale Etat de Vaud, bourse Psychomotricité Suisse. Gli annunci
Etat de Vaud compaiono comunque su jobup.

## Setup (una volta)
1. Su Google: attiva la verifica in due passaggi e crea una **app password**
   (https://myaccount.google.com/apppasswords).
2. Nel repo: *Settings → Secrets and variables → Actions → New repository secret*:
   - `GMAIL_USER` — es. `villa.emanuele.97@gmail.com`
   - `GMAIL_APP_PASSWORD` — la app password (16 caratteri, senza spazi)
   - `MAIL_TO` — es. `sara.germinario@outlook.it` (più indirizzi separati da virgola)
3. *Actions → Ricerca settimanale psychomotricien → Run workflow* (spunta `dry_run` per una prova
   senza invio; il report è negli artifact del run).

## Uso locale
```bash
python search.py --dry-run --html report.html   # nessun invio, stato non salvato
GMAIL_USER=... GMAIL_APP_PASSWORD=... MAIL_TO=... python search.py
```

## Configurazione
Tutto in `config.py`: keyword, regex sul titolo, località per i lavori affini
(`LOCATIONS`), età massima degli annunci affini, id di annunci chiusi da ignorare.

`state.json` (aggiornato dal workflow) tiene traccia delle offerte già segnalate: il report le
marca `NUOVA` / `già nota`, e segnala una volta le offerte psychomotricité sparite come
"non più attive".
