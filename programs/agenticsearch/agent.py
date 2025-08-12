import json
from typing import List, Dict, Any, Optional
from tools import Tools


class SearchAgent:
    def __init__(self):
        """Initialize the AI agent with core components"""
        self.memory = []  # Store conversation history
        self.tools = Tools()  # Available tools/actions
        self.state = {
            "context": {},
            "step_count": 0
        }
    
    def loop(self, user_query: str, max_steps: int = 10):
        """
        Main agent loop: perceive -> reason -> act -> remember
        """
        done = False
        results = None

        while not done and self.state["step_count"] < max_steps:
            try:
                self.state["step_count"] += 1

                thought = self.reason(user_query)
                action = thought["action"]
                args = thought["args"]
                reason = thought.get("reason", "")

                output = self.act(action, args)

                if "context" not in self.state:
                    self.state["context"] = []

                self.state["context"].append({
                    "step": self.state["step_count"],
                    "action": action,
                    "args": args,
                    "reason": reason,
                    "output": output
                })

                if action == "stop_thinking":
                    done = True
                    results = output
            
            except Exception as e:
                self.handle_error(e)
                break

        return results

    def reason(self, user_query: str):
        """
        Reason about the user's query and decide on the next action
        """

        system_prompt = f"""
        You are a SQL data agent. Your goal is to help users query and retrieve relevant data from a database. Here are the available tools:
        
        """

        try:
            response = self.tools.llm_call(system_prompt)
            parsed = json.loads(response)

            if not self.validate_action(parsed):
                return self.fallback_action("Invalid action structure")
            
            available_actions = [tool["name"] for tool in self.tools.tools]
            if parsed["action"] not in available_actions:
                return self.fallback_action(f"Invalid action: {parsed['action']}. Available actions: {available_actions}")

            return parsed
        
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return self.fallback_action("Invalid JSON response")
        
        except Exception as e:
            print(f"LLM call failed: {e}")
            return self.fallback_action(f"LLM call failed: {str(e)}")

        
    def validate_action(self, action: Dict[str, Any]) -> bool:
        """
        Validate the action structure
        """

        required = ["action", "args", "reason"]
        return all(key in action for key in required)
    
    def fallback_action(self, error_message: str):
        """
        Fallback action if the reasoning fails
        """
        return {
            "action": "ask_clarification", 
            "args": {"message": f"I encountered an error: {error_message}. Could you please clarify your request?"}, 
            "reason": error_message
        }
    
    
    

        