#!/usr/bin/env python3
"""
AI Agent Demo - Shows how to use the SearchAgent
"""

from agent import SearchAgent
import json


def demo_agent():
    """Demonstrate the AI agent capabilities"""
    print("🤖 AI Agent Demo")
    print("=" * 50)
    
    # Initialize the agent
    agent = SearchAgent()
    
    # Example queries to test different agent behaviors
    test_queries = [
        "Search for user information",
        "What tables are in the database?",
        "Show me the database schema",
        "Generate SQL for finding all users",
        "Hello, how are you?"
    ]
    
    print("\nTesting agent with different queries:")
    print("-" * 30)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. User: {query}")
        response = agent.loop(query)
        print(f"   Agent: {response}")
    
    # Show agent memory
    print("\n" + "=" * 50)
    print("📝 Agent Memory:")
    print("-" * 30)
    
    memory = agent.get_memory()
    for i, entry in enumerate(memory, 1):
        print(f"\nMemory Entry {i}:")
        print(f"  Input: {entry['perception']['input']}")
        print(f"  Action: {entry['decision']['action']}")
        print(f"  Response: {entry['response']}")
        print(f"  Timestamp: {entry['timestamp']}")


def interactive_mode():
    """Run agent in interactive mode"""
    print("\n🤖 AI Agent Interactive Mode")
    print("Type 'quit' to exit, 'memory' to see memory, 'reset' to reset agent")
    print("=" * 60)
    
    agent = SearchAgent()
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() == 'quit':
                print("Goodbye! 👋")
                break
            elif user_input.lower() == 'memory':
                memory = agent.get_memory()
                print(f"\n📝 Memory ({len(memory)} entries):")
                for i, entry in enumerate(memory, 1):
                    print(f"  {i}. {entry['perception']['input']} → {entry['decision']['action']}")
            elif user_input.lower() == 'reset':
                agent.reset()
                print("🔄 Agent reset!")
            elif user_input:
                response = agent.loop(user_input)
                print(f"Agent: {response}")
            else:
                print("Please enter a query.")
                
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"Error: {e}")


def test_agent_features():
    """Test specific agent features"""
    print("\n🧪 Testing Agent Features")
    print("=" * 40)
    
    agent = SearchAgent()
    
    # Test perception
    perception = agent.perceive("test query")
    print(f"Perception: {perception}")
    
    # Test reasoning
    decision = agent.reason(perception)
    print(f"Decision: {decision}")
    
    # Test action
    response = agent.act(decision)
    print(f"Response: {response}")
    
    # Test tools
    tools = agent.tools
    print(f"Available tables: {tools.get_tables()}")
    print(f"User schema: {tools.get_schema('users')}")
    
    # Test SQL generation
    sql = tools.generate_sql("find all users")
    print(f"Generated SQL: {sql}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "demo":
            demo_agent()
        elif mode == "interactive":
            interactive_mode()
        elif mode == "test":
            test_agent_features()
        else:
            print("Usage: python main.py [demo|interactive|test]")
    else:
        # Default to demo mode
        demo_agent()
        print("\n" + "=" * 50)
        print("Try: python main.py interactive")
        print("Or:  python main.py test")

