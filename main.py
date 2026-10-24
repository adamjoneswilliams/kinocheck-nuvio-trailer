import os
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

# -------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------
KINOCHECK_API_KEY = os.environ.get("KINOCHECK_API_KEY", "TZ5gJp6KtjES1fTviZVYWKQxoanq8XIS4doXAD20cG5hu0EqUQBPbwMdj3VaGJFi")
KINOCHECK_API_HOST = "api.kinocheck.com"
INTRO_SKIP_SECONDS = 5  
# -------------------------------------------------------------

@app.get("/manifest.json")
def get_manifest():
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
    # FIXED LOGIC: Isolates the string 'tt4154796' safely even if extensions get sent
    clean_imdb_id = imdb_id.replace(".json", "")
    
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
        response = requests.get(url, headers=headers, params=params, timeout=6)
        
        if response.status_code != 200:
            return JSONResponse(content={"streams": []})
            
        data = response.json()
        if not isinstance(data, dict):
            return JSONResponse(content={"streams": []})
            
        trailer_data = data.get("trailer")
        if not trailer_data or "youtube_video_id" not in trailer_data:
            return JSONResponse(content={"streams": []})
            
        yt_id = trailer_data["youtube_video_id"]
        
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
        return JSONResponse(content={"streams": [], "error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
