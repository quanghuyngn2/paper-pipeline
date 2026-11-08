"""Partie C : SQLite, page HTML et notification Discord."""

import json
import logging
import os
import sqlite3
from pathlib import Path

import requests

try:  # optionnel : charge le fichier .env s'il existe
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# SQLite
# --------------------------------------------------------------------------
def _db_path() -> Path:
    """Chemin de la base (relatif à la racine du projet si non absolu)."""
    path = Path(os.environ.get("DB_PATH", "data/papers.db"))
    return path if path.is_absolute() else PROJECT_ROOT / path


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS papers (
            filename TEXT PRIMARY KEY,
            title    TEXT NOT NULL,
            summary  TEXT NOT NULL,
            keywords TEXT NOT NULL,   -- liste JSON
            category TEXT NOT NULL
        )
        """
    )
    return conn


def get_processed_filenames() -> set[str]:
    """Noms de fichiers déjà présents en base (pour détecter les nouveaux PDF)."""
    with _connect() as conn:
        rows = conn.execute("SELECT filename FROM papers").fetchall()
    return {row["filename"] for row in rows}


def save_paper(filename: str, meta: dict) -> None:
    """Enregistre (ou met à jour) un papier. Idempotent : pas de doublon."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO papers (filename, title, summary, keywords, category)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(filename) DO UPDATE SET
                title    = excluded.title,
                summary  = excluded.summary,
                keywords = excluded.keywords,
                category = excluded.category
            """,
            (
                filename,
                meta["title"],
                meta["summary"],
                json.dumps(meta["keywords"], ensure_ascii=False),
                meta["category"],
            ),
        )
    log.info("Paper saved: %s", filename)


# --------------------------------------------------------------------------
# Page HTML statique
# --------------------------------------------------------------------------
_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Research Library</title>
<style>
  :root { --bg:#fafafa; --fg:#1d1d1f; --muted:#6b6b70; --card:#fff;
          --border:#dcdce0; --accent:#2f6fed; --chip:#eaf0fe; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#16171a; --fg:#ececee; --muted:#9a9aa2; --card:#202226;
            --border:#34363c; --accent:#7aa2ff; --chip:#27304a; }
  }
  body { font-family: system-ui, sans-serif; background:var(--bg); color:var(--fg);
         max-width:900px; margin:0 auto; padding:24px 16px; }
  h1 { margin-bottom:4px; }
  .sub { color:var(--muted); margin-bottom:20px; }
  .controls { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:20px; }
  input, select { padding:8px 10px; border:1px solid var(--border); border-radius:6px;
                  background:var(--card); color:var(--fg); font-size:1rem; }
  input { flex:1; min-width:200px; }
  .card { background:var(--card); border:1px solid var(--border); border-radius:8px;
          padding:14px 16px; margin-bottom:12px; }
  .card h2 { margin:0 0 4px; font-size:1.1rem; }
  .meta { color:var(--muted); font-size:.85rem; margin-bottom:8px; }
  .cat { color:var(--accent); font-weight:600; }
  .chip { display:inline-block; background:var(--chip); border-radius:12px;
          padding:2px 9px; margin:2px 4px 0 0; font-size:.8rem; }
  .empty { color:var(--muted); text-align:center; padding:30px 0; }
</style>
</head>
<body>
<h1>Research Library</h1>
<div class="sub" id="count"></div>
<div class="controls">
  <input id="q" type="search" placeholder="Search title, summary, keywords…">
  <select id="cat"><option value="">All categories</option></select>
</div>
<div id="list"></div>

<script>
const PAPERS = __PAPERS_JSON__;

const q = document.getElementById("q");
const cat = document.getElementById("cat");
const list = document.getElementById("list");
const count = document.getElementById("count");

[...new Set(PAPERS.map(p => p.category))].sort().forEach(c => {
  const o = document.createElement("option");
  o.value = c; o.textContent = c;
  cat.appendChild(o);
});

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function render() {
  const term = q.value.trim().toLowerCase();
  const wanted = cat.value;
  const shown = PAPERS.filter(p => {
    if (wanted && p.category !== wanted) return false;
    if (!term) return true;
    const hay = [p.title, p.summary, p.filename, p.category, ...p.keywords]
      .join(" ").toLowerCase();
    return hay.includes(term);
  });
  count.textContent = shown.length + " / " + PAPERS.length + " papers";
  list.replaceChildren();
  if (!shown.length) { list.appendChild(el("div", "empty", "No paper found.")); return; }
  shown.forEach(p => {
    const card = el("div", "card");
    card.appendChild(el("h2", "", p.title));
    const meta = el("div", "meta");
    meta.appendChild(el("span", "cat", p.category));
    meta.appendChild(document.createTextNode(" · " + p.filename));
    card.appendChild(meta);
    card.appendChild(el("p", "", p.summary));
    p.keywords.forEach(k => card.appendChild(el("span", "chip", k)));
    list.appendChild(card);
  });
}

q.addEventListener("input", render);
cat.addEventListener("change", render);
render();
</script>
</body>
</html>
"""


def render_html(output_path: str) -> None:
    """Régénère la page index.html à partir de toute la table SQLite."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT filename, title, summary, keywords, category "
            "FROM papers ORDER BY title COLLATE NOCASE"
        ).fetchall()

    papers = []
    for r in rows:
        try:
            keywords = json.loads(r["keywords"])
        except json.JSONDecodeError:
            keywords = []
        papers.append(
            {
                "filename": r["filename"],
                "title": r["title"],
                "summary": r["summary"],
                "keywords": keywords,
                "category": r["category"],
            }
        )

    # "</" échappé pour que le JSON ne puisse jamais fermer la balise <script>.
    # Le rendu côté navigateur utilise textContent -> pas d'injection HTML.
    data = json.dumps(papers, ensure_ascii=False).replace("</", "<\\/")
    html = _HTML_TEMPLATE.replace("__PAPERS_JSON__", data)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")  # écriture atomique (Drive sync)
    tmp.write_text(html, encoding="utf-8")
    tmp.replace(out)
    log.info("HTML written: %s (%d papers)", out, len(papers))


# --------------------------------------------------------------------------
# Discord
# --------------------------------------------------------------------------
def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def notify_discord(filename: str, meta: dict) -> None:
    """Envoie un message Discord pour un papier nouvellement traité."""
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        log.warning("DISCORD_WEBHOOK_URL not set: notification skipped.")
        return

    keywords = ", ".join(meta.get("keywords", []))
    content = (
        f"📄 **New paper processed:** {_truncate(meta['title'], 200)}\n"
        f"**File:** `{filename}`\n"
        f"**Category:** {meta['category']}\n"
        f"**Keywords:** {_truncate(keywords, 300)}\n"
        f"**Summary:** {_truncate(meta['summary'], 900)}"
    )
    response = requests.post(url, json={"content": content[:2000]}, timeout=10)
    response.raise_for_status()  # fait échouer la tâche -> retry Airflow
    log.info("Discord notification sent for %s", filename)
