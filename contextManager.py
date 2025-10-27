import sqlite3
from typing import List

DB_PATH = "insurance_policies.db"

def extract_keywords(user_input: str) -> List[str]:
    tokens = [w.lower().strip(".,!?()[]{}:;\"'") for w in user_input.split() if len(w) > 3]
    unique = []
    for t in tokens:
        if t not in unique:
            unique.append(t)
    return unique[:10]

def fetch_relevant_policies(user_input: str, limit: int = 3) -> str:
    """Return up to `limit` relevant policies based on keyword matching."""
    try:
        keywords = extract_keywords(user_input)
        if not keywords:
            return "No relevant keywords found."
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        clauses = []
        params = []
        for k in keywords:
            clauses.append("(policy_name LIKE ? OR provider LIKE ? OR details LIKE ?)")
            params.extend([f"%{k}%", f"%{k}%", f"%{k}%"])
        where = " OR ".join(clauses)
        query = f"SELECT policy_name, provider, details, end_date FROM policies WHERE {where} LIMIT {limit}"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        if not rows:
            return "No related policies found."
        formatted = "\n".join([
            f"- {r[0]} ({r[1]}): { (r[2] or '')[:300].replace('\\n',' ') }... [Ends: {r[3]}]"
            for r in rows
        ])
        return "Related policies from database:\n" + formatted
    except Exception as e:
        return f"Context fetch error: {str(e)}"
