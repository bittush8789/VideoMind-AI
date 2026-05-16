from youtube_transcript_api import YouTubeTranscriptApi
import sys

print(f"Python version: {sys.version}")
print(f"YouTubeTranscriptApi: {YouTubeTranscriptApi}")
print(f"Attributes: {dir(YouTubeTranscriptApi)}")
try:
    print(f"get_transcript exists: {hasattr(YouTubeTranscriptApi, 'get_transcript')}")
except Exception as e:
    print(f"Error checking: {e}")
