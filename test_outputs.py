"""Test de la partie C sans Airflow.

Usage (depuis la racine du projet) :
    python test_outputs.py
Définir DISCORD_WEBHOOK_URL dans .env pour tester aussi Discord.
"""

import os
import tempfile
from pathlib import Path

tmp = Path(tempfile.mkdtemp())
os.environ["DB_PATH"] = str(tmp / "test.db")  # base jetable, pas la vraie

from pipeline import outputs  # noqa: E402

FAKE = {
    "a.pdf": {"title": "Airflow in Practice", "summary": "How to orchestrate DAGs.",
              "keywords": ["airflow", "dag"], "category": "Data Engineering"},
    "b.pdf": {"title": "RAG <script>alert(1)</script>", "summary": "Retrieval & LLMs.",
              "keywords": ["rag", "llm"], "category": "LLMs"},
    "c.pdf": {"title": "Fairness in ML", "summary": "Bias \"audits\".",
              "keywords": ["fairness"], "category": "Responsible AI"},
}

assert outputs.get_processed_filenames() == set()

for name, meta in FAKE.items():
    outputs.save_paper(name, meta)
outputs.save_paper("a.pdf", FAKE["a.pdf"])  # idempotence : pas de doublon

assert outputs.get_processed_filenames() == set(FAKE), "mauvais contenu en base"

html_path = tmp / "output" / "index.html"
outputs.render_html(str(html_path))
assert html_path.exists()
assert "</script><script>alert" not in html_path.read_text(encoding="utf-8")
print(f"HTML généré : {html_path}  (ouvre-le dans un navigateur)")

outputs.notify_discord("a.pdf", FAKE["a.pdf"])
print("OK")