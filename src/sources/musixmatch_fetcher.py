import httpx
from src.config import GENIUS_TOKEN  # reuse config pattern; token from env
from src.logger import get_logger
from .base_fetcher import BaseFetcher, get_http_client, build_result
import os

logger = get_logger("musixmatch_fetcher")

MUSIXMATCH_TOKEN = os.environ.get("MUSIXMATCH_TOKEN", "")
_BASE = "https://api.musixmatch.com/ws/1.1"


class MusixmatchFetcher(BaseFetcher):
    """
    Lyrics via Musixmatch — largest lyrics database, 100+ languages.
    Requires a MUSIXMATCH_TOKEN environment variable (free tier available).
    Falls back gracefully when the token is absent.
    """

    source_name = "musixmatch"

    def __init__(self, token: str = MUSIXMATCH_TOKEN):
        self.token = token

    async def fetch(self, artist: str, song: str, timestamps: bool = False):
        if not self.token:
            logger.info("Musixmatch token not configured — skipping")
            return None

        client = get_http_client()
        try:
            logger.info(f"Attempting Musixmatch for {artist} - {song}")

            # Step 1: search for the track to get track_id
            search_resp = await client.get(
                f"{_BASE}/matcher.lyrics.get",
                params={
                    "apikey": self.token,
                    "q_artist": artist,
                    "q_track": song,
                    "format": "json",
                },
            )
            if search_resp.status_code != 200:
                return None

            body = search_resp.json()
            msg = body.get("message", {})
            if msg.get("header", {}).get("status_code") != 200:
                return None

            lyrics_body = msg.get("body", {}).get("lyrics", {})
            lyrics_text = (lyrics_body.get("lyrics_body") or "").strip()

            if not lyrics_text:
                return None

            # Musixmatch free tier appends a truncation notice — strip it
            cutoff = lyrics_text.find("******* This Lyrics is NOT for Commercial use *******")
            if cutoff != -1:
                lyrics_text = lyrics_text[:cutoff].strip()

            if not lyrics_text:
                return None

            return build_result(
                source="musixmatch",
                artist=artist,
                title=song,
                lyrics=lyrics_text,
            )

        except httpx.TimeoutException:
            logger.warning(f"Musixmatch timeout for {artist} - {song}")
            return None
        except Exception as e:
            logger.error(f"Musixmatch error: {e}")
            return None
