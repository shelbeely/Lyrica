import httpx
from src.logger import get_logger
from .base_fetcher import BaseFetcher, get_http_client, build_result

logger = get_logger("deezer_fetcher")

_BASE = "https://api.deezer.com"


def _search_deezer_sync_url(artist: str, song: str) -> str:
    """Build Deezer search URL (artist + track)."""
    query = f'artist:"{artist}" track:"{song}"'
    return f"{_BASE}/search?q={query}&limit=1"


class DeezerFetcher(BaseFetcher):
    """
    Song metadata search via Deezer's public API (no auth required).
    Deezer does NOT serve raw lyrics through its public API, so this fetcher
    returns the track title + artist resolved through Deezer and then falls
    back to returning None for lyrics (so downstream fetchers can pick it up).

    Primary use-case: powers the /api/deezer/search endpoint which gives
    callers Deezer track IDs, preview URLs, and cover art for global music.
    The fetch() method is a no-op for lyrics to avoid returning empty results.
    """

    source_name = "deezer"

    async def fetch(self, artist: str, song: str, timestamps: bool = False):
        # Deezer public API doesn't serve lyrics — skip for the lyrics pipeline
        return None

    async def search(self, query: str, limit: int = 20):
        """Search Deezer and return normalised track list."""
        client = get_http_client()
        try:
            logger.info(f"Deezer search: {query!r}")
            resp = await client.get(
                f"{_BASE}/search",
                params={"q": query, "limit": limit},
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            tracks = data.get("data", [])
            results = []
            for t in tracks:
                results.append({
                    "id":          str(t.get("id", "")),
                    "title":       t.get("title", ""),
                    "artist":      t.get("artist", {}).get("name", ""),
                    "album":       t.get("album", {}).get("title", ""),
                    "thumbnail":   t.get("album", {}).get("cover_medium", ""),
                    "preview_url": t.get("preview", ""),
                    "duration":    t.get("duration", 0),
                    "explicit":    t.get("explicit_lyrics", False),
                    "type":        "song",
                    "source":      "deezer",
                })
            logger.info(f"Deezer found {len(results)} results for {query!r}")
            return results
        except httpx.TimeoutException:
            logger.warning(f"Deezer search timeout for {query!r}")
            return []
        except Exception as e:
            logger.error(f"Deezer search error: {e}")
            return []
