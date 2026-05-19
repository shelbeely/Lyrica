import httpx
from src.logger import get_logger
from .base_fetcher import BaseFetcher, get_http_client, build_result

logger = get_logger("netease_fetcher")

# Unofficial NetEase Cloud Music search endpoint (no auth required for search)
_SEARCH_URL = "https://music.163.com/api/search/get/"
_LYRIC_URL  = "https://music.163.com/api/song/lyric"

_HEADERS = {
    "Referer": "https://music.163.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def _strip_lrc_tags(lrc_text: str) -> str:
    """Convert LRC-tagged lyrics to plain text by dropping timestamp tags."""
    import re
    lines = lrc_text.splitlines()
    plain = []
    for line in lines:
        cleaned = re.sub(r"\[\d{2}:\d{2}[.:]\d{2,3}\]", "", line).strip()
        if cleaned:
            plain.append(cleaned)
    return "\n".join(plain)


class NetEaseFetcher(BaseFetcher):
    """
    Lyrics via NetEase Cloud Music (163.com) — dominant in China and
    strong across East/Southeast Asia.  Uses the unofficial public API
    (no API key required).  Gracefully returns None on any failure so
    other fetchers can cover for it.
    """

    source_name = "netease"

    async def fetch(self, artist: str, song: str, timestamps: bool = False):
        client = get_http_client()
        try:
            logger.info(f"Attempting NetEase for {artist} - {song}")

            # Step 1 — search for the song to get its ID
            search_resp = await client.post(
                _SEARCH_URL,
                data={"s": f"{artist} {song}", "type": 1, "limit": 5, "offset": 0},
                headers=_HEADERS,
            )
            if search_resp.status_code != 200:
                return None

            body = search_resp.json()
            songs = (
                body.get("result", {}).get("songs") or []
            )
            if not songs:
                return None

            song_id = songs[0].get("id")
            ret_title = songs[0].get("name", song)
            ret_artist = ""
            artists = songs[0].get("artists", [])
            if artists:
                ret_artist = ", ".join(a.get("name", "") for a in artists)

            if not song_id:
                return None

            # Step 2 — fetch lyrics for that song ID
            lyric_resp = await client.get(
                _LYRIC_URL,
                params={"id": song_id, "lv": -1, "kv": -1, "tv": -1},
                headers=_HEADERS,
            )
            if lyric_resp.status_code != 200:
                return None

            lyric_data = lyric_resp.json()
            lrc_text = lyric_data.get("lrc", {}).get("lyric", "")
            if not lrc_text:
                return None

            lyrics = _strip_lrc_tags(lrc_text)
            if not lyrics:
                return None

            return build_result(
                source="netease",
                artist=ret_artist or artist,
                title=ret_title,
                lyrics=lyrics,
            )

        except httpx.TimeoutException:
            logger.warning(f"NetEase timeout for {artist} - {song}")
            return None
        except Exception as e:
            logger.error(f"NetEase error: {e}")
            return None
