from get_transcript_topics import get_topics_in_transcript
from dotenv import load_dotenv
from openai import OpenAI
import os
import json
import asyncio
from typing import Dict
from pathlib import Path

load_dotenv()
api_key=os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

    
transcript_path="custom_tools/transcript_topics/samples/sample_transcript_2.txt"
final_dict=asyncio.run(get_topics_in_transcript(transcript_path, client))


# Print Dictionary to output file
file=open("custom_tools/transcript_topics/samples/sample_2_out.txt","w")
for keys in final_dict.keys():
    file.write(keys + '\n')
    file.write(final_dict[keys] + '\n\n')


