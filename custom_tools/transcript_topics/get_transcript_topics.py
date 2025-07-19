from topic_shift_detection import topic_shift_splitter
from topic_generator import topic_generator
from dotenv import load_dotenv
from openai import OpenAI
import os
import json
import asyncio
from typing import Dict


# Define a function that performs calculations
async def get_topics_in_transcript(transcript_path, client) -> Dict[str, str]:
    """
    Get the topics in a transcript. There is an in-built function to read the file from the path so that the AI can read it.

    Args:
        transcript_path: The path to the transcript to get the topics from, which gets fed into a open() function
        client: client to access the OpenAI
    Returns:
        The prompt for the model
    """

    transcript=open(transcript_path,"r").read()
    #result = f"""
        #Start with the following transcript.
        
        #return the output as the entire verbatim transcript, with add new lines and topic headers. Leave everything else unchanged.

#        The transcript sections should combine to form the entire transcript

#        The following is the transcript:
#        {transcript}
#        """

    result = topic_shift_splitter(transcript)
    topics_in_transcript=[]

    for i in range(0, len(result)):
        topics_in_transcript.append(topic_generator(result[i], client))

    # Print to topics to output file
    #file=open("samples/test_out_2.txt","w")
    #for content in topics_in_transcript:
    #    file.write(content + '\n\n')

    # Create and return dictionary
    final_dict={}
    for i in range(0, len(result)):
        final_dict[topics_in_transcript[i]]=result[i]
    
    # Print Dictionary to output file
    #file=open("samples/test_out_3.txt","w")
    #for keys in final_dict.keys():
    #    file.write(keys + '\n')
    #    file.write(final_dict[keys] + '\n\n')
    
    return final_dict


# Define the function schema
transcript_topics_function = {
    "type": "function",
    "function": {
        "name": "get_topics_in_transcript",
        "description": "Get the topics in a transcript. There is an in-built function to read the file from the path.",
        "parameters": {
            "type": "object",
            "properties": {
                "transcript_path": {
                    "type": "string",
                    "description": "The path to the transcript to get the topics from"
                },
                #"out_path": {
                #    "type": "string",
                #    "description": "the file location for the output file"
                #}
            },
            "required": ["transcript_path"]
        }
    }
}