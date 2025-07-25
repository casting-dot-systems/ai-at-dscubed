import os
import json
from topic_detection import topic_detection
from dotenv import load_dotenv
from google import genai
from google.genai import types


# Files
transcript_path="custom_tools/transcript_topics/samples/sample_transcript_2.txt"
transcript = open(transcript_path, "r").read()
outfile=open("custom_tools/transcript_topics/samples/sample_out_2.txt","w")

# Load environment variables from .env file
load_dotenv()

# Configure your API key (for Google AI Studio)
# Replace with your actual API key or set it as an environment variable
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("Please set the GOOGLE_API_KEY environment variable.")
client=genai.Client(api_key=GOOGLE_API_KEY)

output=topic_detection(client, transcript)

outfile.write(output)

    
