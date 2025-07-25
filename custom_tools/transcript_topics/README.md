# Topic Detection 

Detecting and separating a transcript by topics

Aaron Do


## Dependencies
- dotenv
- google
- rich

## File Breakdown

run_topic_detection
- takes in an input file and returns the raw transcript with added headings and subheadings in an output file
- uses Gemini 2.5 Flash - API key needed

topic_detection
- function that takes in client and transcript string
- returns the raw transcript with added headings and subheadings as a string



