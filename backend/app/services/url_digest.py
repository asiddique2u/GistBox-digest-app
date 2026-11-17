import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import parse_qs, urljoin, urlsplit

import httpx
import trafilatura
from trafilatura.metadata import extract_metadata

from ..agent.digest_models import DigestDetailLevel, DigestOutput
from ..extraction.youtube import TranscriptFetchError, YouTubeScraper
from .content_digest import DigestGenerationError, generate_digest_for_content
from .request_context import DigestRequestContext

MAX_REDIRECTS = 5
MAX_HTML_BYTES = 2 * 1024 * 1024
REQUEST_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
YOUTUBE_HOSTS = frozenset(
    {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
)
YOUTUBE_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


class UnsafeURL(ValueError):
    pass


class URLFetchError(RuntimeError):
    pass


class UnsupportedContentType(RuntimeError):
    pass


class ContentTooLarge(RuntimeError):
    pass


class ContentExtractionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExtractedContent:
    title: str
    text: str
    article_type: str


def _validate_public_url(url: str) -> tuple[str, int]:
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise UnsafeURL("The URL is invalid") from exc

    if parsed.scheme not in {"http", "https"} or not hostname:
        raise UnsafeURL("Only HTTP and HTTPS URLs are accepted")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeURL("URLs containing credentials are not accepted")

    expected_ports = {None, 80} if parsed.scheme == "http" else {None, 443}
    if port not in expected_ports:
        raise UnsafeURL("Only standard HTTP and HTTPS ports are accepted")

    hostname = hostname.rstrip(".").lower()
    request_port = port or (443 if parsed.scheme == "https" else 80)

    try:
        addresses = {ipaddress.ip_address(hostname)}
    except ValueError:
        if hostname in YOUTUBE_HOSTS:
            return hostname, request_port
        try:
            records = socket.getaddrinfo(
                hostname, request_port, type=socket.SOCK_STREAM
            )
        except OSError as exc:
            raise URLFetchError("The URL host could not be resolved") from exc
        addresses = {ipaddress.ip_address(record[4][0]) for record in records}

    if not addresses or any(not address.is_global for address in addresses):
        raise UnsafeURL("The URL must resolve to a public internet address")

    return hostname, request_port


def _download_html(url: str) -> str:
    current_url = url
    headers = {
        "User-Agent": "GistBox/1.0",
        "Accept": "text/html,application/xhtml+xml",
    }

    with httpx.Client(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=False,
        headers=headers,
        trust_env=False,
    ) as client:
        for redirect_count in range(MAX_REDIRECTS + 1):
            _validate_public_url(current_url)
            try:
                with client.stream("GET", current_url) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise URLFetchError(
                                "The remote server returned an invalid redirect"
                            )
                        if redirect_count == MAX_REDIRECTS:
                            raise URLFetchError("The URL redirected too many times")
                        current_url = urljoin(current_url, location)
                        continue

                    if response.is_error:
                        raise URLFetchError(
                            f"The remote server returned HTTP {response.status_code}"
                        )

                    content_type = response.headers.get(
                        "content-type", ""
                    ).split(";")[0]
                    if content_type.strip().lower() not in {
                        "text/html",
                        "application/xhtml+xml",
                    }:
                        raise UnsupportedContentType(
                            "The URL must point to an HTML page"
                        )

                    body = bytearray()
                    for chunk in response.iter_bytes():
                        if len(body) + len(chunk) > MAX_HTML_BYTES:
                            raise ContentTooLarge(
                                "The HTML page exceeds the 2 MB limit"
                            )
                        body.extend(chunk)
                    try:
                        return bytes(body).decode(
                            response.encoding or "utf-8", errors="replace"
                        )
                    except LookupError:
                        return bytes(body).decode("utf-8", errors="replace")
            except httpx.RequestError as exc:
                raise URLFetchError("The URL could not be retrieved") from exc

    raise URLFetchError("The URL could not be retrieved")


def _youtube_video_id(url: str, hostname: str) -> str:
    parsed = urlsplit(url)
    if hostname == "youtu.be":
        video_id = parsed.path.strip("/").split("/", 1)[0]
    elif parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [""])[0]
    elif parsed.path.startswith("/shorts/"):
        video_id = parsed.path.removeprefix("/shorts/").split("/", 1)[0]
    else:
        raise ContentExtractionError("The YouTube URL does not identify a video")

    if not YOUTUBE_VIDEO_ID.fullmatch(video_id):
        raise ContentExtractionError(
            "The YouTube URL does not contain a valid video ID"
        )
    return video_id


def _extract_youtube_content(url: str, hostname: str) -> ExtractedContent:
    video_id = _youtube_video_id(url, hostname)
    try:
        transcript = YouTubeScraper().get_transcript(video_id)
    except TranscriptFetchError as exc:
        raise URLFetchError(
            "The YouTube transcript service could not retrieve captions"
        ) from exc
    if transcript is None or not transcript.text.strip():
        raise ContentExtractionError("No transcript is available for this YouTube video")
    return ExtractedContent(
        title=f"YouTube video {video_id}",
        text=transcript.text,
        article_type="youtube",
    )


def _extract_web_content(url: str) -> ExtractedContent:
    html = _download_html(url)
    text = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=False,
    )
    if not text or not text.strip():
        raise ContentExtractionError("No readable article text was found at this URL")

    metadata = extract_metadata(html, default_url=url)
    hostname = urlsplit(url).hostname or "Article"
    title = metadata.title.strip() if metadata and metadata.title else hostname
    return ExtractedContent(title=title, text=text, article_type="article")


def process_digest_request(context: DigestRequestContext) -> DigestOutput:
    hostname, _ = _validate_public_url(context.url)
    if hostname in YOUTUBE_HOSTS:
        content = _extract_youtube_content(context.url, hostname)
    else:
        content = _extract_web_content(context.url)

    return generate_digest_for_content(
        context=context,
        title=content.title,
        text=content.text,
        article_type=content.article_type,
    )


def generate_url_digest(
    url: str, detail_level: DigestDetailLevel = "detailed"
) -> DigestOutput:
    context = DigestRequestContext(url=url, detail_level=detail_level)
    try:
        return process_digest_request(context)
    finally:
        context.clear()
