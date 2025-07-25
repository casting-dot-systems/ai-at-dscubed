import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types


def topic_detection(client, transcript:str)->str:
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

    return response.text

    
