# searchtools.py
import os
import json
from typing import List, Dict, Any, Optional

import psycopg2
import psycopg2.extras


class Tools:
    """
    Small toolkit for the agent:
      - PostgreSQL metadata & query execution
      - Lightweight, mock LLM router that returns {action, args, reason} JSON
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        # Prefer env vars, allow explicit overrides
        host = host or os.getenv("PGHOST", "localhost")
        port = int(port or os.getenv("PGPORT", "5432"))
        database = database or os.getenv("PGDATABASE", "postgres")
        user = user or os.getenv("PGUSER", "postgres")
        password = password or os.getenv("PGPASSWORD", "")

        self._conn = None
        try:
            self._conn = psycopg2.connect(
                host=host, port=port, dbname=database, user=user, password=password
            )
            self._conn.autocommit = True
        except Exception as e:
            # Do not crash on import—allow the app to run without DB
            self._conn = None
            self._last_connect_error = str(e)

        self._available_tools = [
            {"name": "get_tables", "description": "List all database tables"},
            {"name": "get_schema", "description": "Get schema for a given table (args: table_name:str)"},
            {"name": "generate_sql", "description": "Generate SQL from natural language (args: query:str)"},
            {"name": "execute_sql", "description": "Run a SQL query (args: sql:str OR query:str)"},
            {"name": "stop_thinking", "description": "Stop the current reasoning loop"},
            {"name": "ask_clarification", "description": "Ask the user to clarify the request (args: message:str)"},
        ]

    # -------------------- DB helpers --------------------

    def _require_conn(self):
        if not self._conn:
            raise RuntimeError(
                "Database connection is not available. "
                "Set PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD or pass params explicitly."
                + (f" Last connect error: {getattr(self, '_last_connect_error', '')}" or "")
            )

    def get_tables(self) -> List[str]:
        """Return list of public schema tables."""
        self._require_conn()
        with self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
                """
            )
            return [row["table_name"] for row in cur.fetchall()]

    def get_schema(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Return schema for a specific table or all public tables (may be large)."""
        self._require_conn()
        with self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            if table_name:
                cur.execute(
                    """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema='public' AND table_name = %s
                    ORDER BY ordinal_position;
                    """,
                    (table_name,),
                )
                cols = [dict(row) for row in cur.fetchall()]
                return {table_name: cols}
            else:
                # Build schema for all public tables
                schema_dict: Dict[str, Any] = {}
                for tbl in self.get_tables():
                    schema_dict.update(self.get_schema(tbl))
                return schema_dict

    def generate_sql(self, query: str) -> str:
        """
        Naive NL->SQL placeholder.
        Replace with a real LLM or template as needed.
        """
        q = (query or "").lower()
        if "users" in q and ("all" in q or "list" in q or "find" in q):
            return "SELECT * FROM public.users LIMIT 100;"
        if "orders" in q and ("all" in q or "list" in q or "find" in q):
            return "SELECT * FROM public.orders LIMIT 100;"
        if "tables" in q:
            # Helpful fallback: return a query that lists tables
            return (
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' ORDER BY table_name;"
            )
        # Very safe default
        return "SELECT NOW() AS server_time;"

    def execute_sql(self, sql: str) -> List[Dict[str, Any]]:
        """Execute SQL and return rows as list[dict]; handle 'no rows' gracefully."""
        self._require_conn()
        with self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql)
            try:
                rows = cur.fetchall()
                return [dict(r) for r in rows]
            except psycopg2.ProgrammingError:
                # e.g., DDL or commands without result sets
                return [{"message": "Query executed successfully but returned no rows"}]

    def search_database(self, query: str) -> List[Dict[str, Any]]:
        """One-shot: generate SQL and execute it."""
        sql = self.generate_sql(query)
        return self.execute_sql(sql)

    def close(self) -> None:
        """Close the DB connection if open."""
        try:
            if self._conn:
                self._conn.close()
        except Exception:
            pass
        self._conn = None

    # -------------------- Tool registry / validation --------------------

    def get_available_tools(self) -> List[Dict[str, str]]:
        return self._available_tools

    def validate_tool(self, tool_name: str) -> bool:
        return any(t["name"] == tool_name for t in self._available_tools)

    # -------------------- Mock LLM router --------------------

    def llm_call(self, prompt: str) -> str:
        """
        Extremely simple heuristic to return a valid JSON decision:
        { "action": <tool>, "args": {...}, "reason": "..." }

        This lets you run the demo without a real LLM.
        Swap this out with an actual LLM API when ready.
        """
        text = (prompt or "").lower()

        # Try to infer a target table name when asking for schema
        table_name = None
        # crude extraction after "schema for/of <name>"
        for key in ["schema for", "schema of"]:
            if key in text:
                after = text.split(key, 1)[1].strip()
                # take first token that looks like a word
                table_name = after.split()[0].strip(" .,:;\"'`()[]{}")
                break
        if not table_name:
            # also catch "schema for the users table"
            for key in ["users", "orders"]:
                if f"{key} table" in text or f"table {key}" in text:
                    table_name = key
                    break

        # Route by keywords
        if "stop" in text and "think" in text:
            decision = {"action": "stop_thinking", "args": {}, "reason": "User requested stop"}
        elif "what tables" in text or "list tables" in text or "tables are in" in text:
            decision = {"action": "get_tables", "args": {}, "reason": "List available tables"}
        elif "schema" in text:
            decision = {
                "action": "get_schema",
                "args": {"table_name": table_name} if table_name else {},
                "reason": f"Show schema{f' for {table_name}' if table_name else ''}",
            }
        elif "execute sql" in text or "run sql" in text:
            # If the prompt includes a SELECT, use it; else fall back to generate_sql(query)
            sql_snippet = None
            if "select " in text:
                # very naive slice of 'select ...'
                sql_snippet = "select " + text.split("select ", 1)[1].split("\n", 1)[0]
            if sql_snippet:
                decision = {"action": "execute_sql", "args": {"sql": sql_snippet}, "reason": "Execute provided SQL"}
            else:
                decision = {
                    "action": "execute_sql",
                    "args": {"query": "users"},  # fallback—agent.act will generate SQL from this query
                    "reason": "Execute generated SQL for the user request",
                }
        elif "generate sql" in text or "find all" in text or "list all" in text:
            # Try to pass original intent through as 'query' (best-effort)
            decision = {"action": "generate_sql", "args": {"query": prompt}, "reason": "Generate SQL from NL query"}
        else:
            # Default: introspect first, then the agent loop/sufficiency gate will decide next step
            decision = {"action": "get_tables", "args": {}, "reason": "Default to listing tables"}

        return json.dumps(decision)

    


