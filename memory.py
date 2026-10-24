"""Explicit, shared local memory for all deliberation roles."""
import re
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DEFAULT_PATH = Path.home() / ".macro-agents" / "memory.sqlite3"


@contextmanager
def connect(path=DEFAULT_PATH):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, text TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    try:
        with db:
            yield db
    finally:
        db.close()


def add(text, path=DEFAULT_PATH):
    text = text.strip()
    if not text or len(text) > 4000:
        raise ValueError("Memory must contain 1-4000 characters")
    with connect(path) as db:
        return db.execute("INSERT INTO memories(text) VALUES (?)", (text,)).lastrowid


def list_all(path=DEFAULT_PATH):
    with connect(path) as db:
        return db.execute("SELECT id, text, created_at FROM memories ORDER BY id DESC").fetchall()


def forget(memory_id, path=DEFAULT_PATH):
    with connect(path) as db:
        return db.execute("DELETE FROM memories WHERE id = ?", (memory_id,)).rowcount > 0


def relevant(question, path=DEFAULT_PATH, limit=8, max_chars=3000):
    """Simple transparent lexical ranking, not embeddings or semantic retrieval."""
    words = set(re.findall(r"[\w]{3,}", question.lower()))
    scored = []
    for mid, text, _ in list_all(path):
        terms = set(re.findall(r"[\w]{3,}", text.lower()))
        score = len(words & terms)
        if score:
            scored.append((score, mid, text))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    selected = []
    remaining = max_chars
    for _, mid, text in scored:
        entry = f"[{mid}] {text}"
        if len(entry) <= remaining and len(selected) < limit:
            selected.append(entry)
            remaining -= len(entry)
    return "\n".join(selected)
