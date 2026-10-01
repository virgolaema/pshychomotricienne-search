#!/usr/bin/env python3
"""Ricerca settimanale offerte psychomotricien(ne) Ginevra/Vaud + lavori affini.

Uso:
  python search.py --dry-run        # stampa il report, non invia
  python search.py                  # invia via Gmail SMTP (variabili d'ambiente sotto)

Variabili d'ambiente per l'invio:
  GMAIL_USER          indirizzo Gmail mittente
  GMAIL_APP_PASSWORD  app password Google (16 caratteri, richiede 2FA)
  MAIL_TO             destinatari separati da virgola
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import smtplib
import sys
import urllib.parse
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import config

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) job-search-bot"}
STATE_FILE = Path(__file__).with_name("state.json")
TODAY = dt.date.today()
errors: list[str] = []


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def safe(name):
    def deco(fn):
        def wrap(*a, **k):
            try:
                return fn(*a, **k)
            except Exception as e:  # noqa: BLE001
                errors.append(f"{name}: {type(e).__name__}: {e}")
                return []
        return wrap
    return deco


# ---------------------------------------------------------------- sorgenti
def _jobcloud(host: str, query: str, location: str | None, max_pages: int = 3):
    """API pubblica JobCloud (jobup.ch / jobs.ch). Max 20 righe per pagina."""
    out = []
    for page in range(1, max_pages + 1):
        p = {"query": query, "rows": 20, "page": page}
        if location:
            p["location"] = location
        d = json.loads(get(f"https://www.{host}/api/v1/public/search?" + urllib.parse.urlencode(p)))
        for x in d.get("documents", []):
            grade = next((t for t in x.get("tags", []) if t.get("type") == "employment_grade"), None)
            rate = ""
            if grade:
                lo, hi = grade.get("value_min"), grade.get("value_max")
                rate = f"{lo}%" if lo == hi else f"{lo}-{hi}%"
            out.append({
                "id": x["job_id"],
                "title": x["title"],
                "company": x.get("company_name", ""),
                "place": x.get("place", ""),
                "rate": rate,
                "date": x.get("publication_date", "")[:10],
                "url": x["_links"]["detail_fr"]["href"],
                "source": host,
            })
        if page >= d.get("num_pages", 1):
            break
    return out


@safe("jobup.ch")
def jobup(query, location=None):
    return _jobcloud("jobup.ch", query, location)


@safe("jobs.ch")
def jobsch(query, location=None):
    return _jobcloud("jobs.ch", query, location)


@safe("HUG SmartRecruiters")
def hug(query):
    d = json.loads(get("https://api.smartrecruiters.com/v1/companies/HUG/postings?limit=100&q="
                       + urllib.parse.quote(query)))
    return [{
        "id": "hug-" + x["id"], "title": x["name"], "company": "HUG",
        "place": x.get("location", {}).get("city", ""), "rate": "",
        "date": x.get("releasedDate", "")[:10],
        "url": f"https://jobs.smartrecruiters.com/HUG/{x['id']}", "source": "HUG",
    } for x in d.get("content", [])]


@safe("AVOP")
def avop(pages=3):
    out = []
    for page in range(1, pages + 1):
        h = get("https://www.avop.ch/job_posts" + (f"/page/{page}" if page > 1 else ""))
        rows = re.findall(r'<div class="job-row">(.*?)(?=<div class="job-row">|</main>|$)', h, re.S)
        if not rows:
            break
        for r in rows:
            cell = lambda lab: clean((re.search(rf'data-label="{lab}">(.*?)</div>', r, re.S) or [None, ""])[1])
            m = re.search(r'href="/job_posts/(\d+)', r)
            if not m:
                continue
            out.append({
                "id": "avop-" + m.group(1), "title": cell("Title"), "company": cell("Institution"),
                "place": cell("Place"), "rate": cell("Rate"), "date": "",
                "deadline": cell("Application deadline"),
                "url": f"https://www.avop.ch/job_posts/{m.group(1)}", "source": "AVOP",
            })
    return out


@safe("Ville de Genève petite enfance")
def ville_ge():
    h = get("https://www.geneve.ch/demarches/offres-emploi-petite-enfance")
    out = []
    for href, alt in re.findall(r'<a href="(/document/[^"]+)"[^>]*?alt="([^"]+)"', h, re.S):
        alt = clean(alt)
        dl = re.search(r"D[ée]lai:\s*([\d.]+)", alt)
        out.append({
            "id": "vge-" + href.rsplit("/", 1)[-1], "title": re.sub(r"\s*\(D[ée]lai:.*\)", "", alt),
            "company": "Ville de Genève (petite enfance)", "place": "Genève", "rate": "",
            "date": "", "deadline": dl.group(1) if dl else "",
            "url": "https://www.geneve.ch" + href, "source": "geneve.ch",
        })
    return out


@safe("Etat de Genève")
def etat_ge():
    h = get("https://www.ge.ch/offres-emploi-etat-geneve/liste-offres")
    seen, out = set(), []
    for href, txt in re.findall(r'<a[^>]+href="([^"]*liste-offres/\d+)"[^>]*>(.*?)</a>', h, re.S):
        if href in seen:
            continue
        seen.add(href)
        out.append({
            "id": "ge-" + href.rsplit("/", 1)[-1], "title": clean(txt), "company": "Etat de Genève",
            "place": "Genève", "rate": "", "date": "",
            "url": urllib.parse.urljoin("https://www.ge.ch", href), "source": "ge.ch",
        })
    return out


@safe("educh.ch")
def educh_count():
    h = get("https://www.educh.ch/emploi/psychomotricien-ne-therapeute-en-psychomotricite-hes-m46.html")
    m = re.search(r"<title>[^<]*?(\d+)\s*offre", h) or re.search(r"(\d+)\s*postes? actifs", h)
    return [int(m.group(1))] if m else []


# ---------------------------------------------------------------- logica
def dedup(items):
    seen, out = set(), []
    for it in items:
        key = (it["title"].lower().strip(), it["company"].lower().strip())
        if it["id"] in seen or key in seen:
            continue
        seen.update({it["id"], key})
        out.append(it)
    return out


def age_days(it):
    try:
        return (TODAY - dt.date.fromisoformat(it["date"])).days
    except ValueError:
        return 0


def deadline_date(it):
    d = it.get("deadline", "")
    try:
        return dt.datetime.strptime(d, "%d.%m.%Y").date()
    except ValueError:
        return None


def collect():
    insts = avop() + ville_ge() + etat_ge()

    core = []
    for q in config.CORE_QUERIES:
        core += jobup(q) + jobsch(q) + hug(q)
    core += insts
    core = [i for i in core
            if config.CORE_TITLE_RE.search(i["title"])
            and not config.GERMAN_RE.search(i["title"])
            and i["id"] not in config.CLOSED_IDS]

    related = []
    for q in config.RELATED_QUERIES:
        for loc in config.LOCATIONS:
            related += jobup(q, loc)
    related += insts
    related = [i for i in related
               if config.RELATED_TITLE_RE.search(i["title"])
               and not config.RELATED_EXCLUDE_RE.search(i["title"])
               and not config.CORE_TITLE_RE.search(i["title"])
               and age_days(i) <= config.RELATED_MAX_AGE_DAYS]

    drop_expired = lambda L: [i for i in L if not (deadline_date(i) and deadline_date(i) < TODAY)]
    return drop_expired(dedup(core)), drop_expired(dedup(related))


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"core": {}, "related": {}}


def annotate(items, seen: dict):
    for it in items:
        it["status"] = "già nota" if it["id"] in seen else "NUOVA"
        dl = deadline_date(it)
        it["urgent"] = bool(dl and (dl - TODAY).days <= 7)
    return items


# ---------------------------------------------------------------- report
GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]


def row_html(it):
    meta = " · ".join(x for x in [it["company"], it["place"], it["rate"],
                                  f"pubbl. {it['date']}" if it["date"] else "",
                                  f"scad. {it['deadline']}" if it.get("deadline") else ""] if x)
    tag = f'<b style="color:#b00">URGENTE</b> ' if it.get("urgent") else ""
    st = f'<span style="color:#070">[{it["status"]}]</span>' if it["status"] == "NUOVA" else f'[{it["status"]}]'
    return (f'<li>{tag}{st} <a href="{html.escape(it["url"])}">{html.escape(it["title"])}</a>'
            f'<br><small>{html.escape(meta)} — {it["source"]}</small></li>')


def row_txt(it):
    meta = " | ".join(x for x in [it["company"], it["place"], it["rate"], it["date"],
                                  "scad. " + it["deadline"] if it.get("deadline") else ""] if x)
    return f"- {'URGENTE ' if it.get('urgent') else ''}[{it['status']}] {it['title']}\n  {meta}\n  {it['url']}"


def build_report(core, related, gone, educh_n):
    date_str = f"{GIORNI[TODAY.weekday()]} {TODAY:%d.%m.%Y}"
    subject = f"[Offerte lavoro] Psychomotricien Ginevra/Vaud — {date_str}"
    H, T = [f"<h2>Offerte psychomotricien(ne) — {date_str}</h2>"], [subject, ""]

    H.append("<h3>A. Psychomotricité (titolo contiene psychomotric*)</h3>")
    T.append("A. PSYCHOMOTRICITÉ")
    if core:
        H.append("<ul>" + "".join(row_html(i) for i in core) + "</ul>")
        T += [row_txt(i) for i in core]
    else:
        H.append("<p>Nessuna nuova offerta trovata questa settimana.</p>")
        T.append("Nessuna nuova offerta trovata questa settimana.")
    if gone:
        H.append("<p><b>Non più attive:</b> " + "; ".join(html.escape(g) for g in gone) + "</p>")
        T.append("Non più attive: " + "; ".join(gone))

    H.append(f"<h3>B. Lavori affini (Ginevra / Vaud, ultimi {config.RELATED_MAX_AGE_DAYS} giorni)</h3>"
             "<p><small>Educatrice dell'infanzia, ASE, educatrice specializzata, baby-sitting/nanny, "
             "parascolaire, ergoterapia, logopedia.</small></p>")
    T += ["", "B. LAVORI AFFINI"]
    if related:
        related.sort(key=lambda i: (i["status"] == "NUOVA", i["date"] or "0"), reverse=True)
        H.append("<ul>" + "".join(row_html(i) for i in related) + "</ul>")
        T += [row_txt(i) for i in related]
    else:
        H.append("<p>Nessuna offerta affine trovata.</p>")
        T.append("Nessuna offerta affine trovata.")

    srcs = ("jobup.ch, jobs.ch (API JobCloud), HUG SmartRecruiters, AVOP, Ville de Genève petite enfance, "
            f"Etat de Genève, educh.ch (pagina psychomotricité: {educh_n if educh_n is not None else '?'} offerte)")
    H.append(f"<h3>Fonti controllate</h3><p>{srcs}.</p>")
    T += ["", "Fonti: " + srcs]
    if errors:
        H.append("<p><b>Fonti non raggiungibili:</b><br>" + "<br>".join(html.escape(e) for e in errors) + "</p>")
        T += ["Fonti non raggiungibili:"] + errors
    rec = ("Da controllare a mano: bourse aux emplois di Psychomotricité Suisse (solo membri), "
           "CHUV (recrutement.chuv.ch), Etat de Vaud (offres-emploi.vd.ch), alert educh.ch "
           "(https://www.educh.ch/alerte-emploi/). Baby-sitting: babysits.ch, yoopies.ch, Croix-Rouge genevoise "
           "(cours baby-sitting + mise en relation).")
    H.append(f"<h3>Raccomandazioni</h3><p>{html.escape(rec)}</p>")
    T += ["", rec]
    return subject, "\n".join(H), "\n".join(T)


def send(subject, html_body, txt_body):
    user, pw = os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"]
    to = [a.strip() for a in os.environ["MAIL_TO"].split(",") if a.strip()]
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = subject, user, ", ".join(to)
    msg.attach(MIMEText(txt_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pw)
        s.sendmail(user, to, msg.as_string())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--html", help="salva anche il report HTML in questo file")
    a = ap.parse_args()

    state = load_state()
    core, related = collect()
    educh = educh_count()
    annotate(core, state["core"])
    annotate(related, state["related"])

    now_ids = {i["id"] for i in core}
    gone = [v["title"] + " — " + v["company"] for k, v in state["core"].items() if k not in now_ids]

    subject, h, t = build_report(core, related, gone, educh[0] if educh else None)
    if a.html:
        Path(a.html).write_text(h)
    if errors:
        print("Errori:", *errors, sep="\n  ", file=sys.stderr)
    if a.dry_run:
        print(t)
    else:
        send(subject, h, t)
        print("Email inviata:", subject)

    if a.dry_run:
        return
    iso = TODAY.isoformat()
    state["core"] = {i["id"]: {"title": i["title"], "company": i["company"],
                               "first_seen": state["core"].get(i["id"], {}).get("first_seen", iso)} for i in core}
    state["related"] = {i["id"]: state["related"].get(i["id"], iso) for i in related}
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
