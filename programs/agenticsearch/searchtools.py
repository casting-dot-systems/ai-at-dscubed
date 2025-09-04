# searchtools.py 

from __future__ import annotations
import os
import re
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --- LLM  ------------------------------------------------------------

# pip install -U google-generativeai
import google.generativeai as genai


# --- Config ------------------------------------------------------------------

# DB lives next to this file as "discord_mock.db"
DB_PATH = Path(__file__).parent / "discord_mock.db"

# When True, we only allow SELECTs via execute_sql (safer for demos)
READ_ONLY = True


# --- Helpers -----------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"SQLite database not found at {DB_PATH}. "
            "Run setup_mock_db.py first."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    return conn


def _rows_to_dicts(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(r) for r in rows]


def _clean_sql(sql: str) -> str:
    return sql.strip().rstrip(";") + ";"


# --- Public API used by your agent -------------------------------------------

def get_tables() -> Dict[str, Any]:
    """List user tables in the SQLite database."""
    try:
        with _connect() as conn:
            cur = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name;
                """
            )
            tables = [r["name"] for r in cur.fetchall()]
        return {"ok": True, "tables": tables}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_schema(table_name: str) -> Dict[str, Any]:
    """Return column schema for a table using PRAGMA table_info."""
    try:
        if not table_name:
            return {"ok": False, "error": "table_name is required"}
        with _connect() as conn:
            cur = conn.execute(f"PRAGMA table_info({table_name});")
            cols = [
                {
                    "cid": r["cid"],
                    "name": r["name"],
                    "type": r["type"],
                    "notnull": bool(r["notnull"]),
                    "default": r["dflt_value"],
                    "pk": bool(r["pk"]),
                }
                for r in cur.fetchall()
            ]
        if not cols:
            return {"ok": False, "error": f"Table '{table_name}' not found."}
        return {"ok": True, "table": table_name, "columns": cols}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def execute_sql(query: str, params: Optional[Tuple[Any, ...]] = None) -> Dict[str, Any]:
    """Run a SQL query and return rows + column names.
       By default we only allow SELECTs (safe demos)."""
    try:
        if not query or not query.strip():
            return {"ok": False, "error": "Query is empty."}

        sql = _clean_sql(query)

        if READ_ONLY:
            # quick safety check (allow SELECT or CTE starting with WITH)
            first = re.split(r"\s+", sql.strip(), maxsplit=1)[0].upper()
            if first != "SELECT" and not sql.upper().startswith("WITH "):
                return {"ok": False, "error": "Only SELECT queries are allowed in demo mode."}
            # reject multiple statements in one call
            if ";" in sql.strip()[:-1]:
                return {"ok": False, "error": "Multiple statements are not allowed."}

        with _connect() as conn:
            cur = conn.execute(sql, params or ())
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
        return {"ok": True, "columns": cols, "rows": _rows_to_dicts(rows)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def generate_sql(natural_query: str) -> Dict[str, Any]:
    """
    Small heuristic to turn a plain request into SQL for the mock schema.
    Matches YOUR SQLite schema from setup_mock_db.py:

      users(user_id INTEGER PK, username TEXT, join_date DATE)
      channels(channel_id INTEGER PK, channel_name TEXT)
      messages(message_id INTEGER PK, user_id, channel_id, content TEXT, timestamp DATE)

    This is only a fallback; with Gemini wired in, the agent will usually plan
    with llm_call → decide tool → (maybe) call this helper when asked.
    """
    try:
        if not natural_query:
            return {"ok": False, "error": "natural_query is empty."}

        q = natural_query.lower()

        # If the user already gave SQL, just return it.
        if re.search(r"\bselect\b", q):
            return {"ok": True, "sql": _clean_sql(natural_query)}

        # List tables
        if "table" in q and ("list" in q or "what" in q or "which" in q):
            return {
                "ok": True,
                "sql": (
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
                ),
            }

        # Schemas
        if "schema" in q and "user" in q:
            return {"ok": True, "sql": "PRAGMA table_info(users);"}
        if "schema" in q and "channel" in q:
            return {"ok": True, "sql": "PRAGMA table_info(channels);"}
        if "schema" in q and "message" in q:
            return {"ok": True, "sql": "PRAGMA table_info(messages);"}

        # Basic selects that match your column names
        if "user" in q:
            return {"ok": True, "sql": "SELECT user_id, username, join_date FROM users ORDER BY user_id LIMIT 100;"}

        if "channel" in q:
            return {"ok": True, "sql": "SELECT channel_id, channel_name FROM channels ORDER BY channel_id LIMIT 100;"}

        if "message" in q:
            # recent messages
            return {
                "ok": True,
                "sql": (
                    "SELECT message_id, user_id, channel_id, content, timestamp "
                    "FROM messages ORDER BY timestamp DESC LIMIT 100;"
                ),
            }

        # Fallback: list tables
        return {
            "ok": True,
            "sql": (
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
            ),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def healthcheck() -> Dict[str, Any]:
    """Quick check the DB is reachable."""
    try:
        with _connect() as conn:
            conn.execute("SELECT 1;").fetchone()
        return {"ok": True, "db_path": str(DB_PATH)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# --- Tools wrapper class (what agent imports) --------------------------------

class Tools:
    """
    Wrap functions so agent code can call:
      tools.get_tables(), tools.get_schema(...),
      tools.generate_sql(...), tools.execute_sql(...), tools.llm_call(prompt).
    Also provides get_available_tools() for the planner.
    """

    # ========= Basic tool calls =========
    def get_tables(self) -> Dict[str, Any]:
        return get_tables()

    def get_schema(self, table_name: str) -> Dict[str, Any]:
        return get_schema(table_name)

    def execute_sql(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> Dict[str, Any]:
        return execute_sql(query, params)

    def generate_sql(self, query: str) -> Dict[str, Any]:
        return generate_sql(query)

    def healthcheck(self) -> Dict[str, Any]:
        return healthcheck()

    def get_available_tools(self) -> List[str]:
        # Keep as a simple list of strings (your agent expects a list)
        return [
            "get_tables",
            "get_schema",
            "generate_sql",
            "execute_sql",
            "ask_clarification",
            "stop_thinking",
        ]

    # ========= Real LLM call  =========
    # Returns a STRING containing JSON because your agent does: json.loads(response)
    def llm_call(self, prompt: str) -> str:
        """
        Calls Gemini 2.5 Flash. Expects to return ONLY a JSON string when the
        agent is planning actions, OR a short 'Yes'/'No' when the sufficiency
        gate asks for that.

        Environment:
          - Set GEMINI_API_KEY in your shell before running:
              PowerShell:  $env:GEMINI_API_KEY="YOUR_KEY"
              bash/zsh:    export GEMINI_API_KEY="YOUR_KEY"
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            # Return a JSON that tells the agent to ask for setup
            return json.dumps({
                "action": "ask_clarification",
                "args": {"message": "GEMINI_API_KEY is not set. Please configure your API key."},
                "reason": "missing API key"
            })

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        # Make outputs deterministic
        generation_config = {
            "temperature": 0.0,
            "top_p": 0.0,
            "top_k": 1,
        }

        # Two possible modes:
        # 1) Planner prompt (we must return ONLY JSON with action/args/reason).
        # 2) Sufficiency gate prompt (expects 'Yes' or 'No').
        #
        # *** FIX: looser detection ***
        is_planner = "return only valid json" in prompt.lower()

        if is_planner:
            res = model.generate_content(
                ["You must return ONLY JSON with keys: action, args, reason. No extra text.", prompt],
                generation_config=generation_config,
            )
            text = (res.text or "").strip()

            # Try parse as JSON directly
            try:
                obj = json.loads(text)
            except Exception:
                # Try to find a JSON object in any extra text
                m = re.search(r"\{.*\}", text, flags=re.DOTALL)
                if not m:
                    return json.dumps({
                        "action": "ask_clarification",
                        "args": {"message": "I could not produce strict JSON. Please rephrase."},
                        "reason": "formatting safeguard"
                    })
                candidate = m.group(0)
                try:
                    obj = json.loads(candidate)
                except Exception:
                    return json.dumps({
                        "action": "ask_clarification",
                        "args": {"message": "I could not produce strict JSON. Please rephrase."},
                        "reason": "formatting safeguard"
                    })

            # Schema check: must be a dict with action/args/reason
            if not isinstance(obj, dict) or not {"action", "args", "reason"} <= set(obj.keys()):
                return json.dumps({
                    "action": "ask_clarification",
                    "args": {"message": "Planner must return {action,args,reason} JSON only."},
                    "reason": "schema check failed"
                })

            return json.dumps(obj)

        else:
            # Sufficiency gate (expects 'Yes' or 'No')
            res = model.generate_content(
                ["Answer ONLY with Yes or No.", prompt],
                generation_config=generation_config,
            )
            text = (res.text or "").strip()
            if not text:
                return "No"
            return "Yes" if text.lower().startswith("y") else "No"
