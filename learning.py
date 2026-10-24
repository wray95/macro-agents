"""Auditable feedback-based adaptation; no model fine-tuning or automatic truth claims."""
import sqlite3
from memory import connect

DOMAINS = ('general', 'crypto', 'stocks', 'content', 'game')

def domain_for(question):
    q = question.lower()
    for domain, words in [('crypto', ('crypto','bitcoin','token','blockchain')),('stocks', ('stock','equity','share price','market research')),('content', ('reel','video','facebook','channel','publish')),('game', ('game','card battler','arena'))]:
        if any(word in q for word in words): return domain
    return 'general'

def record(role, domain, score, note, path):
    if domain not in DOMAINS or not isinstance(score, int) or not 1 <= score <= 5 or not role or len(note) > 1000:
        raise ValueError('Provide a valid role, domain, score 1-5 and note <= 1000 characters')
    with connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, role TEXT NOT NULL, domain TEXT NOT NULL, score INTEGER NOT NULL, note TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        return db.execute('INSERT INTO feedback(role,domain,score,note) VALUES (?,?,?,?)',(role,domain,score,note)).lastrowid

def report(domain, path):
    if domain not in DOMAINS: raise ValueError('Unknown domain')
    with connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY, role TEXT NOT NULL, domain TEXT NOT NULL, score INTEGER NOT NULL, note TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        return db.execute('SELECT role, count(*), round(avg(score),2) FROM feedback WHERE domain=? GROUP BY role ORDER BY avg(score) DESC, count(*) DESC',(domain,)).fetchall()

def guidance(domain, path):
    rows = report(domain, path)
    if not rows: return ''
    return 'User feedback in '+domain+' (small-sample subjective ratings, not verified accuracy): '+', '.join(f'{r}: {avg}/5 ({n} ratings)' for r,n,avg in rows)+'. Challenge claims using evidence, not popularity.'
