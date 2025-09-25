import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from searchtools import Tools


class SearchAgent:
    def __init__(self):
        """Initialize the AI agent with core components"""
        self.memory: List[Dict[str, Any]] = []         # conversation/history snapshots
        self.tools = Tools()                           # Available tools/actions
        self.state: Dict[str, Any] = {                 # per-turn state
            "context": [],
            "step_count": 0
        }

    # ---------- Public API ----------

    def loop(self, user_query: str, max_steps: int = 5) -> Any:
        """
        Main agent loop implementing Plan-1:
        reason -> act -> check sufficiency -> repeat (guarded) -> respond
        """
        # reset per-call counters
        self.state["step_count"] = 0
        empty_count = 0
        last_output: Any = None

        while self.state["step_count"] < max_steps:
            self.state["step_count"] += 1

            # Decide next action
            thought = self.reason(user_query)
            action = thought.get("action", "ask_clarification")
            args = thought.get("args", {})
            reason = thought.get("reason", "")

            # Execute the action
            output = self.act(action, args)

            # Record context
            ctx_entry = {
                "step": self.state["step_count"],
                "action": action,
                "args": args,
                "reason": reason,
                "output": output,
                "ts": datetime.utcnow().isoformat() + "Z",
            }
            self.state.setdefault("context", []).append(ctx_entry)
            self._remember_snapshot(user_query, thought, output)

            # Empty/irrelevant guard (prevents infinite looping on empty results)
            is_empty = (output is None) or (output == []) or (output == {})                        or (isinstance(output, dict) and not output.get("ok", True))
            if is_empty:
                empty_count += 1
                if empty_count >= 2:
                    return {
                        "message": "Not enough data to answer yet.",
                        "context": self.state.get("context", []),
                    }

            # Sufficiency gate (LLM-driven)
            if self.check_sufficiency(user_query, output):
                return output

            last_output = output

        # Fallback when we reach the cap
        return {
            "message": "Max steps reached; returning best available results.",
            "results": last_output,
            "context": self.state.get("context", []),
        }

    def perceive(self, q: str) -> Dict[str, Any]:
        """Minimal perceive stub used by main.py test path."""
        return {"input": q, "ts": datetime.utcnow().isoformat() + "Z"}

    def get_memory(self) -> List[Dict[str, Any]]:
        """Return memory entries in the shape main.py expects."""
        return self.memory

    def reset(self) -> None:
        """Reset agent state and short-term memory."""
        self.state = {"context": [], "step_count": 0}
        self.memory = []

    # ---------- Core Reasoning & Acting ----------

    def reason(self, user_query_or_perception: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Decide the next action using the LLM.
        Accepts either a raw user string or a perception dict for flexibility.
        Returns: {"action": <tool>, "args": {...}, "reason": "..."}
        """
        if isinstance(user_query_or_perception, dict):
            user_query = user_query_or_perception.get("input", "")
        else:
            user_query = str(user_query_or_perception)

        available = self.tools.get_available_tools()

        # --- Upgraded planner prompt to stop loops and guide SQL patterns (with metadata support) ---
        system_prompt = (
            "You are a planner for a small SQL data agent that can only use these actions: "
            f"{', '.join(available)}.\n"
            "Your job is to pick the NEXT best action and its args, then stop.\n"
            "Return ONLY valid JSON with keys exactly: action, args, reason.\n\n"
            "RULES:\n"
            "1) Do NOT call the same action twice in a row with the same args.\n"
            "2) If you already listed tables (get_tables), move on to get_schema, get_metadata, or execute_sql.\n"
            "3) Use get_metadata when you need high-level descriptions of tables or key columns.\n"
            "4) Prefer execute_sql once you know the needed tables/columns.\n"
            "5) If the user asks for counts, use SELECT COUNT(*).\n"
            "6) If the user asks for 'last/most recent/top N messages', use ORDER BY timestamp DESC LIMIT N.\n"
            "7) If the user refers to a channel by name, JOIN messages m with channels c on m.channel_id=c.channel_id "
            "   and filter WHERE c.channel_name = '<name>'.\n"
            "8) If the user refers to a username, JOIN messages m with users u on m.user_id=u.user_id "
            "   and filter WHERE u.username = '<name>'.\n"
            "9) If you lack a column name, first call get_schema('<table>').\n"
            "10) If you cannot progress, use ask_clarification with a very specific question.\n\n"
            "EXAMPLES OF GOOD NEXT STEPS:\n"
            "- User: 'What are the last 5 messages?' → action: 'execute_sql', "
            "  args: {\"sql\": \"SELECT message_id, user_id, channel_id, content, timestamp "
            "                   FROM messages ORDER BY timestamp DESC LIMIT 5;\"}\n"
            "- User: 'Show usernames who posted in support' → action: 'execute_sql', "
            "  args: {\"sql\": \"SELECT DISTINCT u.username "
            "                   FROM users u JOIN messages m ON u.user_id=m.user_id "
            "                   JOIN channels c ON m.channel_id=c.channel_id "
            "                   WHERE c.channel_name='support';\"}\n"
            "- User: 'What does the metadata say about messages?' → action: 'get_metadata', "
            "  args: {\"table_name\": \"messages\"}\n\n"
            "FORMAT:\n"
            "Return ONLY JSON like {\"action\":\"...\",\"args\":{...},\"reason\":\"...\"}"
        )
        user_prompt = f"User query: {user_query}"

        try:
            response = self.tools.llm_call(system_prompt + "\n\n" + user_prompt)
            parsed = json.loads(response)

            # --- Strict schema check for planner output ---
            if not self.validate_action(parsed):
                return self.fallback_action("Planner must return JSON with keys {action,args,reason} only.")

            # --- Disallow unknown actions ---
            if parsed["action"] not in available:
                return self.fallback_action(
                    f"Invalid action: {parsed['action']}. Available actions: {available}"
                )

            # --- Anti-repeat guard: don't allow same action+args twice in a row ---
            if self.state.get("context"):
                prev = self.state["context"][-1]
                same_action = parsed["action"] == prev.get("action")
                same_args = parsed.get("args", {}) == prev.get("args", {})
                if same_action and same_args:
                    return self.fallback_action("Repeated same action; choose a different next step.")

            return parsed

        except json.JSONDecodeError as e:
            return self.fallback_action(f"Invalid JSON response: {e}")
        except Exception as e:
            return self.fallback_action(f"LLM call failed: {str(e)}")

    def act(self, action_or_decision: Union[str, Dict[str, Any]], args: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a chosen action."""
        if isinstance(action_or_decision, dict):
            action = action_or_decision.get("action", "ask_clarification")
            args = action_or_decision.get("args", {})  # type: ignore
        else:
            action = action_or_decision
            args = args or {}

        try:
            if action == "get_tables":
                return self.tools.get_tables()

            if action == "get_schema":
                return self.tools.get_schema(args.get("table_name"))

            if action == "get_metadata":
                return self.tools.get_metadata(args.get("table_name"))

            if action == "generate_sql":
                query = args.get("query", "")
                return self.tools.generate_sql(query)

            if action == "execute_sql":
                if "sql" in args and args["sql"]:
                    sql_text = args["sql"]
                elif "query" in args and args["query"]:
                    gen = self.tools.generate_sql(args["query"])
                    if isinstance(gen, dict) and gen.get("ok") and gen.get("sql"):
                        sql_text = gen["sql"]
                    else:
                        return {"error": f"Could not generate SQL: {gen}"}
                else:
                    return {"error": "execute_sql requires 'sql' or 'query'."}
                return self.tools.execute_sql(sql_text)

            if action == "stop_thinking":
                return {"message": "Stopped by request."}

            if action == "ask_clarification":
                msg = args.get("message", "Could you please clarify your request?")
                return {"message": msg}

            return {"error": f"Unknown action '{action}'"}

        except Exception as e:
            self.handle_error(e)
            return {"error": f"Tool execution failed: {str(e)}"}

    def check_sufficiency(self, user_query: str, output: Any) -> bool:
        """LLM-driven sufficiency check."""
        preview = output
        try:
            preview = json.dumps(output)[:4000]
        except Exception:
            preview = str(output)[:4000]

        prompt = (
            "User question: " + user_query + "\n"
            "Tool results: " + str(preview) + "\n\n"
            "Decide if this is enough information to answer the user’s question.\n"
            "It is enough if:\n"
            "- The results are not empty.\n"
            "- The results contain the right columns/fields needed to answer the question.\n"
            "- The results directly answer the user’s question.\n\n"
            "Answer only with \"Yes\" or \"No\"."
        )

        try:
            verdict = self.tools.llm_call(prompt).strip().lower()
            return verdict.startswith("y")
        except Exception:
            return False

    def validate_action(self, action: Dict[str, Any]) -> bool:
        return isinstance(action, dict) and {"action", "args", "reason"} <= set(action.keys())

    def fallback_action(self, error_message: str) -> Dict[str, Any]:
        return {
            "action": "ask_clarification",
            "args": {"message": f"I encountered an error: {error_message}. Could you please clarify your request?"},
            "reason": error_message,
        }

    def handle_error(self, e: Exception) -> None:
        self.memory.append({
            "perception": {"input": "error"},
            "decision": {"action": "error"},
            "response": {"error": str(e)},
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

    def _remember_snapshot(self, user_query: str, decision: Dict[str, Any], response: Any) -> None:
        self.memory.append({
            "perception": {"input": user_query},
            "decision": {"action": decision.get("action", ""), "args": decision.get("args", {})},
            "response": response,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
