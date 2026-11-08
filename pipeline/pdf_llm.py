"""Partie B : PDF -> Markdown et extraction des métadonnées par le LLM local."""
import pymupdf4llm
import pymupdf
import json 
from openai import OpenAI
from pipeline.config import OLLAMA_BASE_URL, OLLAMA_MODEL

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

SYSTEM_PROMPT = f"""You extract metadata from research papers.
Answer only with a JSON object with the keys title, summary, keywords and category.
The summary has 2 or 3 sentences, keywords is a list of 3 to 6 keywords,
and category is a short, general research field (1 to 3 words), for example Data Engineering."""

SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "category": {"type": "string"},},
    "required": ["title", "summary", "keywords", "category"],
}


def pdf_to_markdown(pdf_path: str, maxPages: int= 3) -> str:
    with pymupdf.open(pdf_path) as doc:
        pages = list(range(min(maxPages,doc.page_count)))
    markdown = pymupdf4llm.to_markdown(pdf_path,pages=pages)
    if len(markdown.strip()) < 300:
        raise ValueError(f"Not enough text extracted from {pdf_path}")
    return markdown

def _ask_llm(markdown: str) -> str:
    """Envoie l'article au LLM et renvoie sa réponse brute (du texte)."""
    response = client.chat.completions.create(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": markdown},
        ],
        response_format={"type": "json_schema", "json_schema": {"name": "paper", "schema": SCHEMA}},
        temperature=0,
    )
    return response.choices[0].message.content


def _is_valid(meta) -> bool:
    """Vérifie que les quatre champs existent et ont le bon type."""
    return (
        isinstance(meta, dict)
        and isinstance(meta.get("title"), str)
        and isinstance(meta.get("summary"), str)
        and isinstance(meta.get("keywords"), list)
        and isinstance(meta.get("category"), str)
    )


def extract_metadata(markdown: str) -> dict:
    for _ in range(2):  # premier essai + un retry
        try:
            meta = json.loads(_ask_llm(markdown))  # texte JSON -> dictionnaire Python
            if _is_valid(meta):
                return meta  # tout est bon : on s'arrête là
        except json.JSONDecodeError:
            pass  # JSON illisible : on passe à l'essai suivant
    raise ValueError("The LLM did not return valid JSON after 2 attempts")


if __name__ == "__main__":
    import sys

    chemin = sys.argv[1]
    texte = pdf_to_markdown(chemin)
    print(f"{len(texte)} caractères extraits")
    meta = extract_metadata(texte)
    print(json.dumps(meta, indent=2, ensure_ascii=False))