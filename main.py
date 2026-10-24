
import os
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

KINOCHECK_API_KEY = os.environ.get("KINOCHECK_API_KEY")
KINOCHECK_API_HOST = "api.kinocheck.de"
INTRO_SKIP_SECONDS = 5


@app.get("/manifest.json")
def get_manifest():
    return {
        "id": "com.nuvio.kinocheck.bridge",
        "version": "1.0.1",
        "name": "KinoCheck Trailer Bridge",
        "description": "KinoCheck trailers for Nuvio",
        "resources": [
            {
                "name": "stream",
                "types": ["movie", "series"],
                "idPrefixes": ["tt"]
            }
        ],
        "types": ["movie", "series"],
        "idPrefixes": ["tt"],
        "catalogs": []
    }


@app.get("/stream/{video_type}/{imdb_id}.json")
def get_stream(video_type: str, imdb_id: str):
    if video_type not in ("movie", "series"):
        return JSONResponse({"streams": []})

    if not KINOCHECK_API_KEY:
        return JSONResponse({"streams": []}, status_code=503)

    endpoint = "shows" if video_type == "series" else "movies"

    url = f"https://{KINOCHECK_API_HOST}/{endpoint}"

    headers = {
        "Accept": "application/json",
        "X-Api-Key": KINOCHECK_API_KEY,
        "X-Api-Host": KINOCHECK_API_HOST
    }

    params = {
        "imdb_id": imdb_id,
        "language": "en"
    }

    try:
        response = requests.get(
            url, headers=headers, params=params, timeout=10
        )
        response.raise_for_status()
        data = response.json()

        trailer = data.get("trailer")
        if not isinstance(trailer, dict):
            return {"streams": []}

        yt_id = trailer.get("youtube_video_id")
        if not yt_id:
            return {"streams": []}

        return {
            "streams": [
                {
                    "title": trailer.get("title", "KinoCheck Trailer"),
                    "ytId": yt_id,
                    "url": (
                        f"https://www.youtube.com/watch?v={yt_id}"
                        f"&t={INTRO_SKIP_SECONDS}s"
                    )
                }
            ]
        }

    except (requests.RequestException, ValueError):
        return {"streams": []}
