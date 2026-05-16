from youtube_transcript_api import YouTubeTranscriptApi
import inspect

print(f"fetch is class method: {inspect.ismethod(YouTubeTranscriptApi.fetch)}")
print(f"fetch is function: {inspect.isfunction(YouTubeTranscriptApi.fetch)}")

try:
    print("Trying class call...")
    YouTubeTranscriptApi.list("dQw4w9WgXcQ")
    print("Class call worked")
except Exception as e:
    print(f"Class call failed: {e}")

try:
    print("Trying instance call...")
    YouTubeTranscriptApi().list("dQw4w9WgXcQ")
    print("Instance call worked")
except Exception as e:
    print(f"Instance call failed: {e}")
