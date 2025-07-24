import os
import json
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from dotenv import load_dotenv
from google import genai
from google.genai import types


# Files
transcript_path="custom_tools/transcript_topics/samples/sample_transcript_2.txt"
transcript = open(transcript_path, "r").read()
outfile=open("custom_tools/transcript_topics/samples/sample_out_2.txt","w")

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
        temperature=1,
        #max_output_tokens=100,
        thinking_config=types.ThinkingConfig(
            thinking_budget=0  # Disables thinking
        )
    ),
)

prompt = f"""
Given the following transcript, return the list of topics and subtopics with the raw, unedited sections of the transcript. the combination of all the sections should be the entire transcript:

{transcript}
"""

response = chat.send_message(prompt)


outfile.write(response.text)

    
