# PROTOTYPE
# TO BE ADAPTED
###########################################################################################################

# Requires: youtube-transcript-api
import os
import re
from youtube_transcript_api._api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

def extract_video_id(url: str) -> str:
    """Extract the video ID from a YouTube URL."""
    # Handles various YouTube URL formats
    patterns = [
        r"(?:v=|youtu\.be/|embed/|shorts/)([\w-]{11})",
        r"youtube\.com/watch\?v=([\w-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError("Could not extract video ID from URL.")

def sanitize_filename(title: str) -> str:
    """Sanitize the title to be a safe filename."""
    # Remove invalid filename characters and trim length
    sanitized = re.sub(r'[^\w\- ]', '', title).strip().replace(' ', '_')
    return sanitized[:80]  # limit to 80 chars

def main():
    UNCLEANED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../brain/processing_transcripts_info/transcripts/uncleaned'))
    os.makedirs(UNCLEANED_DIR, exist_ok=True)
    url = input("Enter YouTube video URL: ").strip()
    title = input("Enter the video title: ").strip()
    try:
        video_id = extract_video_id(url)
    except Exception as e:
        print(f"Error: {e}")
        return
    print(f"Fetching transcript for video ID: {video_id}")
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
    except TranscriptsDisabled:
        print("Transcripts are disabled for this video.")
        return
    except NoTranscriptFound:
        print("No transcript found for this video.")
        return
    except VideoUnavailable:
        print("Video unavailable.")
        return
    except Exception as e:
        print(f"Failed to fetch transcript: {e}")
        return
    # Join transcript text
    transcript_text = "\n".join([entry['text'] for entry in transcript])
    filename = f"{sanitize_filename(title)}.txt"
    out_path = os.path.join(UNCLEANED_DIR, filename)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(transcript_text)
    print(f"Transcript saved to: {out_path}")

if __name__ == "__main__":
    main()
