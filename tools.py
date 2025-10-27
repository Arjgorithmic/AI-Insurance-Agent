import sqlite3
from datetime import datetime, timedelta
from langchain_core.tools import tool

DB_PATH = "insurance_policies.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS policies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        policy_name TEXT,
        provider TEXT,
        start_date TEXT,
        end_date TEXT,
        premium REAL,
        details TEXT
    )
    """)
    conn.commit()
    conn.close()

@tool
def add_policy(policy_name: str, provider: str, start_date: str, end_date: str, premium: float, details: str = "") -> str:
    """Add a new insurance policy to the local SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO policies (policy_name, provider, start_date, end_date, premium, details) VALUES (?, ?, ?, ?, ?, ?)",
            (policy_name, provider, start_date, end_date, premium, details)
        )
        conn.commit()
        conn.close()
        return f"Policy '{policy_name}' added successfully."
    except Exception as e:
        return f"Error adding policy: {str(e)}"

@tool
def view_policies() -> str:
    """Return a formatted list of all insurance policies in the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, policy_name, provider, start_date, end_date, premium FROM policies")
        rows = c.fetchall()
        conn.close()
        if not rows:
            return "No policies found."
        formatted = ""
        for row in rows:
            id_, name, provider, start, end, premium = row
            formatted += f"**{name}** ({provider})\n"
            formatted += f"- Premium: ₹{premium:,.2f}\n"
            if start and end:
                formatted += f"- Valid: {start} → {end}\n"
            formatted += "\n"
        return formatted
    except Exception as e:
        return f"Error viewing policies: {str(e)}"

@tool
def check_renewals(days_ahead: int = 30) -> str:
    """Return policies that will expire within the next `days_ahead` days."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT policy_name, provider, end_date FROM policies")
        rows = c.fetchall()
        conn.close()
        if not rows:
            return "No policies found."
        now = datetime.now()
        upcoming = []
        for name, provider, end_date in rows:
            try:
                end = datetime.strptime(end_date, "%Y-%m-%d")
            except Exception:
                continue
            if now <= end <= now + timedelta(days=days_ahead):
                remaining = (end - now).days
                upcoming.append(f"{name} ({provider}) - renews in {remaining} days on {end_date}")
        if not upcoming:
            return f"No renewals in the next {days_ahead} days."
        return "Upcoming renewals:\n" + "\n".join(upcoming)
    except Exception as e:
        return f"Error checking renewals: {str(e)}"

TOOLS = [add_policy, view_policies, check_renewals]
init_db()
