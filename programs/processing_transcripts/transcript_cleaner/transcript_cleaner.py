import os
import asyncio
import aiofiles
from openai import AsyncOpenAI

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../brain/processing_transcripts_info/transcripts'))
UNCLEANED_DIR = os.path.join(BASE_DIR, 'uncleaned')
CLEANED_DIR = os.path.join(BASE_DIR, 'cleaned')

SYSTEM_PROMPT = (
    "You are a transcript cleaner. You will receive a messy meeting transcript as a single block of text. "
    "Your job is to: 1) Decide and clarify which person is talking at what time, 2) Fix grammar mistakes, "
    "3) Remove filler words, 4) Format the transcript as a readable conversation with speaker names. "
    "If the transcript contains pauses or interruptions, note them as [pause] or [interruption]. "
    "Use only the names you can infer from the transcript. If you cannot infer a name, use 'Person 1', 'Person 2', etc. as speaker names."
)

async def clean_transcript_with_gpt(text: str) -> str:
    client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    response = await client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        temperature=0.2,
        max_tokens=2048,
    )
    content = response.choices[0].message.content
    return content.strip() if content else ""

async def process_file(filename: str):
    uncleaned_path = os.path.join(UNCLEANED_DIR, filename)
    cleaned_path = os.path.join(CLEANED_DIR, filename)
    async with aiofiles.open(uncleaned_path, 'r', encoding='utf-8') as f:
        text = await f.read()
    cleaned = await clean_transcript_with_gpt(text)
    async with aiofiles.open(cleaned_path, 'w', encoding='utf-8') as f:
        await f.write(cleaned)
    print(f"Processed and cleaned: {filename}")

async def clean_all_transcripts():
    os.makedirs(CLEANED_DIR, exist_ok=True)
    files = [f for f in os.listdir(UNCLEANED_DIR) if f.endswith('.txt')]
    await asyncio.gather(*(process_file(f) for f in files))

if __name__ == "__main__":
    asyncio.run(clean_all_transcripts()) 