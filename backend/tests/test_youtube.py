import unittest
from unittest.mock import MagicMock, patch

from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    YouTubeTranscriptApiException,
)

from app.extraction.youtube import TranscriptFetchError, YouTubeScraper


class YouTubeScraperTests(unittest.TestCase):
    @patch("app.extraction.youtube.YouTubeTranscriptApi")
    def test_missing_transcript_returns_none(self, api_class: MagicMock) -> None:
        api_class.return_value.fetch.side_effect = TranscriptsDisabled("video-id")

        transcript = YouTubeScraper().get_transcript("video-id")

        self.assertIsNone(transcript)

    @patch("app.extraction.youtube.YouTubeTranscriptApi")
    def test_unexpected_api_failure_is_logged_and_raised(
        self, api_class: MagicMock
    ) -> None:
        api_class.return_value.fetch.side_effect = YouTubeTranscriptApiException(
            "request blocked"
        )

        with self.assertLogs("app.extraction.youtube", level="ERROR"):
            with self.assertRaises(TranscriptFetchError) as error:
                YouTubeScraper().get_transcript("video-id")

        self.assertIsInstance(
            error.exception.__cause__, YouTubeTranscriptApiException
        )


if __name__ == "__main__":
    unittest.main()
