import os
import json
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from dotenv import load_dotenv
from google import genai
from google.genai import types


# Load environment variables from .env file
load_dotenv()
console = Console()

# Configure your API key (for Google AI Studio)
# Replace with your actual API key or set it as an environment variable
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("Please set the GOOGLE_API_KEY environment variable.")
client=genai.Client(api_key=GOOGLE_API_KEY)


# You can also set generation_config directly when initializing the model
# This sets defaults for all future calls with this model instance
chat = client.chats.create(
    model='gemini-2.5-flash',
    config=types.GenerateContentConfig(
        temperature=0.5,
        max_output_tokens=100,
        thinking_config=types.ThinkingConfig(
            thinking_budget=0  # Disables thinking
        )
    ),
)

console.print(Panel(Align("[bold]Welcome to the DSCubed AI Assistant![/bold]\n[italic]Type 'help' to see the list of available tools.[/italic]\n[italic red]Type 'exit' to end the conversation.[/italic red]", align="center")))
while True:
    # Generate content from a text prompt
    prompt = input(">> ")

    if prompt.lower() in {"exit","end","quit","bye","goodbye"}:
        console.print(Panel(Align("[bold]Thank you for using the DSCubed AI Assistant! Goodbye![/bold]", align="center")))
        break
    if prompt.lower() in {"help"}:
        console.print(Panel("[bold]Available tools:[/bold]\n[italic] - calculator (add, subtract, multiply, divide)[/italic]\n[italic] - get current time in a given timezone (e.g. 'Asia/Tokyo')[/italic]\n[italic] - get stock price of a given stock (e.g. 'AAPL')[/italic]"))
        continue
    response = chat.send_message(prompt)

    console.print(Panel(Align(f"{response.text}")))
    
