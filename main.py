import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

# -------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------
KINOCHECK_API_KEY = os.environ.get("KINOCHECK_API_KEY", "YOUR_KINOCHECK_API_KEY")
KINOCHECK_API_HOST = "://kinocheck.com"
INTRO_SKIP_SECONDS = 5  # Change this if you want to skip more/less
# -------------------------------------------------------------

@app.get("/manifest.json")
def get_manifest():
    """Returns the manifest required by AIOMetadata."""
    return {
        "id": "com.nuvio.kinocheck.bridge",
        "version": "1.0.0",
        "name": "KinoCheck Trailer Bridge",
        "description": "Feeds high-quality KinoCheck trailers directly to AIOMetadata",
        "resources": ["stream"],
        "types": ["movie", "series"],
        "idPrefixes": ["tt"],
        "catalogs": []
    }

@app.get("/stream/{video_type}/{imdb_id}.json")
def get_stream(video_type: str, imdb_id: str):
    """
    Listens for AIOMetadata stream requests (e.g., /stream/movie/tt4154796.json)
    Queries KinoCheck using the IMDb ID, and maps it to Stremio/Nuvio specs.
    """
    # Clean up the incoming ID if it has extra extensions (like .json from some clients)
    clean_imdb_id = imdb_id.split(".")[0]
    
    # Determine the endpoint based on content type
    endpoint = "shows" if video_type == "series" else "movies"
    
    url = f"https://{KINOCHECK_API_HOST}/{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Api-Key": KINOCHECK_API_KEY,
        "X-Api-Host": KINOCHECK_API_HOST
    }
    params = {
        "imdb_id": clean_imdb_id,
        "language": "en"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        
        if response.status_code != 200:
            return JSONResponse(content={"streams": []})
            
        data = response.json()
        trailer_data = data.get("trailer")
        
        # If no trailer object is found in the response, return an empty array smoothly
        if not trailer_data or "youtube_video_id" not in trailer_data:
            return JSONResponse(content={"streams": []})
            
        yt_id = trailer_data["youtube_video_id"]
        
        # Construct the stream payload AIOMetadata expects
        return {
            "streams": [
                {
                    "title": f"🎬 KinoCheck Trailer ({INTRO_SKIP_SECONDS}s Intro Skip)",
                    "ytId": yt_id,
                    "url": f"https://youtube.com{yt_id}&t={INTRO_SKIP_SECONDS}s"
                }
            ]
        }
        
    except Exception as e:
        # Fallback gracefully so your whole media layout doesn't crash on network hiccups
        return JSONResponse(content={"streams": []})

if __name__ == "__main__":
    import uvicorn
    # Launches the local server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
