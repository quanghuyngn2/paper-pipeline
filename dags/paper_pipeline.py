"""Airflow DAG for the research paper pipeline."""
from datetime import timedelta
from pathlib import Path

from airflow.sdk import DAG, task
from pendulum import datetime

from pipeline.config import OUTPUT_DIR, PAPERS_DIR
from pipeline.outputs import (
    get_processed_filenames,
    notify_discord as send_discord_notification,
    render_html,
    save_paper,
)
from pipeline.pdf_llm import extract_metadata, pdf_to_markdown


def _project_path(path: Path) -> Path:
    """Resolve relative paths against the repository root, not Airflow's cwd."""
    project_root = Path(__file__).resolve().parent.parent
    return path if path.is_absolute() else project_root / path


with DAG(
    dag_id="paper_pipeline",
    description="Process new research PDFs with a local LLM",
    schedule="0 8 * * *",
    start_date=datetime(2026, 11, 1, tz="Europe/Brussels"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=2)},
    tags=["research", "assignment3"],
) as dag:

    @task
    def detect_new_pdfs() -> list[str]:
        folder = _project_path(PAPERS_DIR)
        if not folder.is_dir():
            raise FileNotFoundError(f"PDF folder does not exist: {folder}")
        processed = get_processed_filenames()
        return [str(p) for p in sorted(folder.glob("*.pdf")) if p.name not in processed]

    @task
    def convert_pdf(pdf_path: str) -> dict:
        return {"pdf_path": pdf_path, "markdown": pdf_to_markdown(pdf_path)}

    @task
    def analyze_llm(paper: dict) -> dict:
        return {
            "filename": Path(paper["pdf_path"]).name,
            "metadata": extract_metadata(paper["markdown"]),
        }

    @task
    def store_sqlite(paper: dict) -> dict:
        save_paper(paper["filename"], paper["metadata"])
        return paper

    @task
    def generate_html(papers: list[dict]) -> None:
        if papers:
            render_html(str(_project_path(OUTPUT_DIR) / "index.html"))

    @task
    def notify_discord(paper: dict) -> None:
        send_discord_notification(paper["filename"], paper["metadata"])

    detected = detect_new_pdfs()
    converted = convert_pdf.expand(pdf_path=detected)
    analyzed = analyze_llm.expand(paper=converted)
    stored = store_sqlite.expand(paper=analyzed)
    html = generate_html(stored)
    notification = notify_discord.expand(paper=stored)

    stored >> [html, notification]

