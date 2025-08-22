# agent.py
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime


from searchtools import Tools


class SearchAgent:
    def __init__(self):
        """Initialize the AI agent with core components"""
        self.memory: List[Dict[str, Any]] = []         # conversation/history snapshots
        self.tools = Tools()                            # Available tools/actions
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
            is_empty = (output is None) or (output == []) or (output == {})
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

        available = [t["name"] for t in self.tools.get_available_tools()]

        system_prompt = (
            "You are a SQL data agent. Your goal is to help users query and "
            "retrieve relevant data from a PostgreSQL database. Available tools:\n"
            f"{', '.join(available)}.\n\n"
            "Return ONLY valid JSON with keys: action, args, reason.\n"
            "Example: {\"action\":\"get_tables\",\"args\":{},\"reason\":\"list tables\"}"
        )
        user_prompt = f"User query: {user_query}"

        try:
            response = self.tools.llm_call(system_prompt + "\n\n" + user_prompt)
            parsed = json.loads(response)

            if not self.validate_action(parsed):
                return self.fallback_action("Invalid action structure")

            if parsed["action"] not in available:
                return self.fallback_action(
                    f"Invalid action: {parsed['action']}. Available actions: {available}"
                )

            return parsed

        except json.JSONDecodeError as e:
            return self.fallback_action(f"Invalid JSON response: {e}")
        except Exception as e:
            return self.fallback_action(f"LLM call failed: {str(e)}")

    def act(self, action_or_decision: Union[str, Dict[str, Any]], args: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a chosen action. Accepts either:
          - act('get_schema', {'table_name':'users'})
          - act({'action':'get_schema','args':{'table_name':'users'}})
        """
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

            if action == "generate_sql":
                query = args.get("query", "")
                return self.tools.generate_sql(query)

            if action == "execute_sql":
                sql = args.get("sql") or self.tools.generate_sql(args.get("query", ""))
                return self.tools.execute_sql(sql)

            if action == "stop_thinking":
                return {"message": "Stopped by request."}

            if action == "ask_clarification":
                msg = args.get("message", "Could you please clarify your request?")
                return {"message": msg}

            # Unknown action
            return {"error": f"Unknown action '{action}'"}

        except Exception as e:
            self.handle_error(e)
            return {"error": f"Tool execution failed: {str(e)}"}

    # ---------- Sufficiency Gate ----------

    def check_sufficiency(self, user_query: str, output: Any) -> bool:
        """
        LLM-driven sufficiency check (binary Yes/No).
        You can later extend this to return confidence/missing fields.
        """
        # Keep payload short to avoid excessive tokens
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
            return verdict.startswith("y")  # "yes"
        except Exception:
            return False

    # ---------- Helpers ----------

    def validate_action(self, action: Dict[str, Any]) -> bool:
        """Validate the action structure returned by the LLM."""
        required = ["action", "args", "reason"]
        return all(k in action for k in required)

    def fallback_action(self, error_message: str) -> Dict[str, Any]:
        """Fallback action if reasoning fails."""
        return {
            "action": "ask_clarification",
            "args": {
                "message": f"I encountered an error: {error_message}. Could you please clarify your request?"
            },
            "reason": error_message,
        }

    def handle_error(self, e: Exception) -> None:
        """Basic error handler (log to memory)."""
        self.memory.append({
            "perception": {"input": "error"},
            "decision": {"action": "error"},
            "response": {"error": str(e)},
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

    def _remember_snapshot(self, user_query: str, decision: Dict[str, Any], response: Any) -> None:
        """Store a compact snapshot in memory to satisfy main.py's display."""
        self.memory.append({
            "perception": {"input": user_query},
            "decision": {"action": decision.get("action", ""), "args": decision.get("args", {})},
            "response": response,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
