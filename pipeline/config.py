import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

PAPERS_DIR = Path(os.getenv("PAPERS_DIR", "papers")).expanduser()
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output")).expanduser()
DB_PATH = ROOT / os.getenv("DB_PATH", "data/papers.db")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
