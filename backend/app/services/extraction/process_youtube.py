from datetime import date
from typing import Optional

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.services.extraction.youtube import YouTubeScraper
from app.database.repository import Repository


TRANSCRIPT_UNAVAILABLE_MARKER = "__UNAVAILABLE__"

def process_youtube_transcript(url: str) -> bool:
    scraper = YouTubeScraper()
    repo = Repository()
    
    video_id = scraper._extract_video_id(url)
    repo.create_youtube_video(video_id=video_id, title="", url=url, channel_id="", published_at=date.today(), description="")
    transcript_result = scraper.get_transcript(video_id)
    processed = 0
    unavailable = 0
    failed = 0
    
    
    try:
        transcript_result = scraper.get_transcript(video_id)
        if transcript_result:
            repo.update_youtube_video_transcript(video_id, transcript_result.text)
            processed += 1
        else:
            repo.update_youtube_video_transcript(video_id, TRANSCRIPT_UNAVAILABLE_MARKER)
            unavailable += 1
    except Exception as e:
        repo.update_youtube_video_transcript(video_id, TRANSCRIPT_UNAVAILABLE_MARKER)
        unavailable += 1
        print(f"Error processing video {video_id}: {e}")
        return False
    
    return True


if __name__ == "__main__":
    result = process_youtube_transcript("https://www.youtube.com/watch?v=E8zpgNPx8jE&t=376s")
