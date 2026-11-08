
from datetime import timedelta

from airflow.sdk import DAG, task
from pendulum import datetime


with DAG(
    dag_id="paper_pipeline",
    description="Research papers processing workflow",
    schedule="0 8 * * *",
    start_date=datetime(2026, 11, 1, tz="Europe/Brussels"),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 1,
        "retry_delay": timedelta(minutes=2),
    },
    tags=["research", "assignment3"],
) as dag:

    @task
    def detect_new_pdfs():
        print("TEST: Detect new PDF files")

    @task
    def convert_pdf():
        print("TEST: Convert PDF to Markdown")

    @task
    def analyze_llm():
        print("TEST: Extract metadata using local LLM")

    @task
    def store_sqlite():
        print("TEST: Save metadata to SQLite")

    @task
    def generate_html():
        print("TEST: Regenerate HTML index")

    @task
    def notify_discord():
        print("TEST: Send Discord notification")

    detected = detect_new_pdfs()
    converted = convert_pdf()
    analyzed = analyze_llm()
    stored = store_sqlite()
    html = generate_html()
    notification = notify_discord()

    detected >> converted >> analyzed >> stored
    stored >> [html, notification]
