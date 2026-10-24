import re

import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

KINOCHECK_API_BASE = "https://api.kinocheck.com"
INTRO_SKIP_SECONDS = 5
REQUEST_TIMEOUT = 10


def empty_streams():
    return {"streams": []}


def fetch_kinocheck(video_type: str, video_id: str):
    """Return the upstream response, or raise a useful error for diagnostics."""
    endpoint = {"movie": "movies", "series": "shows"}.get(video_type)
    if endpoint is None:
        raise ValueError("video_type must be 'movie' or 'series'")

    video_id = video_id.removesuffix(".json")
    if re.fullmatch(r"tt\d+", video_id):
        id_parameter = "imdb_id"
    elif video_id.isdigit():
        id_parameter = "tmdb_id"
    else:
        raise ValueError("ID must be an IMDb ID (tt...) or numeric TMDB ID")

    params = {id_parameter: video_id, "language": "en"}
    headers = {"Accept": "application/json"}
    data = None
    # The entity endpoint can return a PHP error object for some IMDb IDs.
    # KinoCheck's /trailers endpoint accepts the same IDs, so try it as fallback.
    for api_endpoint in (endpoint, "trailers"):
        response = requests.get(
            f"{KINOCHECK_API_BASE}/{api_endpoint}",
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        if extract_youtube_id(data):
            return data

    if not isinstance(data, (dict, list)):
        raise ValueError(f"KinoCheck returned {type(data).__name__}, expected an object or list")
    return data


def extract_youtube_id(data):
    if isinstance(data, list):
        for item in data:
            found = extract_youtube_id(item)
            if found:
                return found
        return None
    if not isinstance(data, dict):
        return None

    # The /trailers endpoint can return a video resource directly.
    direct_id = data.get("youtube_video_id")
    if isinstance(direct_id, str) and re.fullmatch(r"[A-Za-z0-9_-]+", direct_id):
        return direct_id

    trailer = data.get("trailer")
    candidates = [trailer] if isinstance(trailer, dict) else []
    videos = data.get("videos")
    if isinstance(videos, list):
        candidates.extend(video for video in videos if isinstance(video, dict))

    for video in candidates:
        youtube_id = video.get("youtube_video_id")
        categories = video.get("categories") or []
        is_trailer = "Trailer" in categories
        if isinstance(youtube_id, str) and re.fullmatch(r"[A-Za-z0-9_-]+", youtube_id):
            # The dedicated trailer field is already KinoCheck's selected trailer.
            if video is trailer or is_trailer:
                return youtube_id
    return None


@app.get("/manifest.json")
def get_manifest():
    return {
        "id": "com.nuvio.kinocheck.bridge",
        "version": "1.1.0",
        "name": "KinoCheck Trailer Bridge",
        "description": "KinoCheck trailers for Nuvio",
        "resources": ["stream"],
        "types": ["movie", "series"],
        "idPrefixes": ["tt"],
        "catalogs": [],
    }


@app.get("/stream/{video_type}/{video_id}.json")
def get_stream(video_type: str, video_id: str):
    try:
        data = fetch_kinocheck(video_type, video_id)
    except (requests.RequestException, ValueError):
        return JSONResponse(content=empty_streams())

    youtube_id = extract_youtube_id(data)
    if youtube_id is None:
        return JSONResponse(content=empty_streams())

    return {
        "streams": [
            {
                "title": "KinoCheck Trailer",
                "ytId": youtube_id,
                "url": f"https://www.youtube.com/watch?v={youtube_id}&t={INTRO_SKIP_SECONDS}s",
            }
        ]
    }


@app.get("/debug/{video_type}/{video_id}.json")
def debug_stream(video_type: str, video_id: str):
    """Show the raw KinoCheck result and parsed YouTube ID while troubleshooting."""
    try:
        data = fetch_kinocheck(video_type, video_id)
    except requests.HTTPError as exc:
        return JSONResponse(
            status_code=502,
            content={"error": "KinoCheck rejected the request", "details": str(exc), "body": exc.response.text[:2000]},
        )
    except (requests.RequestException, ValueError) as exc:
        return JSONResponse(status_code=502, content={"error": str(exc)})

    return {"kinocheck": data, "youtube_video_id": extract_youtube_id(data)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

