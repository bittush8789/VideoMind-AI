from youtube_transcript_api import YouTubeTranscriptApi
import re
import yt_dlp
import json
import os
import time
import random

def extract_video_id(url: str) -> str:
    """Extracts the video ID from a YouTube URL."""
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if video_id_match:
        return video_id_match.group(1)
    return url  # Assume it's already a video ID if no match

def get_transcript(video_id: str) -> str:
    """Fetches the transcript for a given YouTube video ID, preferring English/Hindi."""
    # Add a small random delay to avoid looking like a bot
    time.sleep(random.uniform(1.0, 3.0))
    
    try:
        # 1. Try to list all transcripts first to see what's available
        try:
            # Using 'list' as the debug script showed it exists instead of 'list_transcripts'
            transcript_list_obj = YouTubeTranscriptApi().list(video_id)
            
            # Prefer English, then Hindi, then any
            try:
                transcript = transcript_list_obj.find_transcript(['en', 'hi'])
            except:
                # Get the first one available
                transcript = next(iter(transcript_list_obj))
            
            transcript_data = transcript.fetch()
        except Exception as list_err:
            print(f"List transcripts failed: {list_err}, falling back to fetch")
            try:
                # Using 'fetch' as the debug script showed it exists instead of 'get_transcript'
                transcript_data = YouTubeTranscriptApi().fetch(video_id, languages=['en', 'hi'])
            except:
                # Last resort: just get whatever is available
                transcript_data = YouTubeTranscriptApi().fetch(video_id)

        # Extract text robustly
        text_parts = []
        for entry in transcript_data:
            if isinstance(entry, dict):
                text_parts.append(entry.get('text', ''))
            else:
                text_parts.append(getattr(entry, 'text', ''))
        
        return " ".join(text_parts).strip()
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Too Many Requests" in error_msg:
            print("YouTube rate limit hit. Trying fallback with yt-dlp...")
            fallback_text = get_transcript_yt_dlp(video_id)
            if fallback_text and not fallback_text.startswith("Error"):
                return fallback_text
        return f"Error fetching transcript: {error_msg}"

def get_transcript_yt_dlp(video_id: str) -> str:
    """Fallback method using yt-dlp to fetch transcripts/subtitles."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Options to get subtitles without downloading the video
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en.*', 'hi.*', '.*'], # Try English, then Hindi, then anything
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Check for subtitles
            subtitles = info.get('subtitles') or info.get('automatic_captions')
            if not subtitles:
                return "Error: No subtitles found for this video."
            
            # Pick a language (prefer English)
            lang = None
            for l in ['en', 'en-US', 'en-GB']:
                if l in subtitles:
                    lang = l
                    break
            
            if not lang:
                # Just take the first one available
                lang = next(iter(subtitles))
            
            # Get the subtitle URL (prefer json format if available, otherwise vtt)
            sub_formats = subtitles[lang]
            sub_url = None
            for f in sub_formats:
                if f.get('ext') == 'json3': # YouTube's internal format, easy to parse
                    sub_url = f.get('url')
                    break
            
            if not sub_url:
                 sub_url = sub_formats[0].get('url')
            
            # Fetch the subtitle content
            import requests
            response = requests.get(sub_url)
            if response.status_code == 200:
                if 'json' in sub_url or 'json3' in sub_url:
                    data = response.json()
                    text_parts = []
                    for event in data.get('events', []):
                        for seg in event.get('segs', []):
                            text_parts.append(seg.get('utf8', ''))
                    return "".join(text_parts).strip()
                else:
                    # Very basic VTT/SRT parsing (just strip tags and timestamps)
                    content = response.text
                    # Simple regex to remove VTT/SRT headers and timestamps
                    content = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}', '', content)
                    content = re.sub(r'<[^>]+>', '', content)
                    content = re.sub(r'WEBVTT|NOTE|STYLE|REGION|Kind:|Language:', '', content)
                    return " ".join(content.split()).strip()
            
            return "Error: Could not fetch subtitle content."
            
    except Exception as e:
        return f"Error in yt-dlp fallback: {str(e)}"

def get_transcript_with_timestamps(video_id: str):
    """Fetches the transcript with timestamps."""
    try:
        # Using fetch() as identified in debug script
        return YouTubeTranscriptApi().fetch(video_id)
    except Exception as e:
        return []
