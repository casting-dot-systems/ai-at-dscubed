## Topic Detection 

Detecting and separating a transcript by topics

Aaron Do


# Dependencies
- openai
- dotenv
- sentence_transformers
- asyncio
- typing
- pathlib

# File Breakdown

run_transcript_topics - **Run to see output**
- Used to test the function
- Includes a script that opens the txt file with the transcript, runs the function, then prints a txt file with the output
- Function calls: get_transcript_topics

get_transcript_topics
- main function with a schema for tool calling (not tested)
- Inputs: path to the transcript, client
- Function calls: topic_shift_detection
- Outputs: dictionary where the key is the topic and the values are the relevant section from the transcript

topic_shift_detection
- Uses sentence_transformers to detect topic changes based on similarity scores
- Similarity score: -1 is opposite meaning, 1 is the same meaning. Currently set at 0.05, but needs to be optimised
- Returns the transcript separated by topics 

topic_generator
- Input: string (section of the transcript)
- Output: string (topic of the section)
- Uses AI to get topic: model needs to be tested

# Improvements
- Include AI to check if the final output is correct
- Optimise for the threshold of similarity (topic_shift_detection)
- Optimise the model selection
- Optimise the prompt for the topic generator
