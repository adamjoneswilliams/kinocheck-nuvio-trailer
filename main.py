import re
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

KINOCHECK_API_HOST = "api.kinocheck.com"
INTRO_SKIP_SECONDS = 5
REQUEST_TIMEOUT = 10


@app.get("/manifest.json")
def get_manifest():
    return {
        "id": "com.nuvio.kinocheck.bridge",
        "version": "1.1.0",
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


@app.get("/stream/{video_type}/{video_id}.json")
def get_stream(video_type: str, video_id: str):
    # Map Stremio/Nuvio 'series' type to KinoCheck 'shows' endpoint
    if video_type == "series":
        endpoint = "shows"
    elif video_type == "movie":
        endpoint = "movies"
    else:
        return JSONResponse({"streams": []})

    # Detect IMDb IDs (tt1234567) versus numeric TMDB IDs.
    if re.fullmatch(r"tt\d+", video_id):
        id_param = "imdb_id"
    elif video_id.isdigit():
        id_param = "tmdb_id"
    else:
        return JSONResponse({"streams": []})

    params = {
        id_param: video_id,
        "language": "en"
    }

    try:
        response = requests.get(
            f"https://{KINOCHECK_API_HOST}/{endpoint}",
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:
            return JSONResponse({"streams": []})

        data = response.json()
        if not isinstance(data, dict):
            return JSONResponse({"streams": []})

        # FIX: The API structure documentation shows 'trailer' is a direct dictionary object,
        # but in active setups it often arrives as a dictionary or needs standard dict safety checks.
        trailer = data.get("trailer")
        if not isinstance(trailer, dict):
            return JSONResponse({"streams": []})

        yt_id = trailer.get("youtube_video_id")
        if not isinstance(yt_id, str) or not yt_id:
            return JSONResponse({"streams": []})

        return {
            "streams": [
                {
                    "title": "KinoCheck Trailer",
                    "ytId": yt_id,
                    "url": (
                        f"https://www.youtube.com/watch?v={yt_id}"
                        f"&t={INTRO_SKIP_SECONDS}s"
                    )
                }
            ]
        }

    except (requests.RequestException, ValueError):
        return JSONResponse({"streams": []})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
