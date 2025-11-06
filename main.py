import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


@app.get("/api/answer")
def instant_answer(q: str):
    """Fetch a quick answer from the public DuckDuckGo Instant Answer API.
    This is a lightweight way to pull info from the web without API keys.
    """
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Missing query parameter 'q'")

    try:
        params = {"q": q, "format": "json", "no_redirect": 1, "no_html": 1}
        r = requests.get("https://api.duckduckgo.com/", params=params, timeout=8)
        r.raise_for_status()
        data = r.json()

        answer = None
        source_url = None

        # Prefer direct answer/abstract
        if data.get("AbstractText"):
            answer = data.get("AbstractText")
            source_url = data.get("AbstractURL") or data.get("AbstractSource")
        elif data.get("Answer"):
            answer = data.get("Answer")
        elif data.get("Definition"):
            answer = data.get("Definition")
            source_url = data.get("DefinitionURL")
        # Fallback to first related topic with text and URL
        if not answer:
            related = data.get("RelatedTopics") or []
            for item in related:
                if isinstance(item, dict):
                    if item.get("Text") and item.get("FirstURL"):
                        answer = item.get("Text")
                        source_url = item.get("FirstURL")
                        break
                # Some entries are nested under 'Topics'
                if isinstance(item, dict) and item.get("Topics"):
                    for sub in item["Topics"]:
                        if sub.get("Text") and sub.get("FirstURL"):
                            answer = sub.get("Text")
                            source_url = sub.get("FirstURL")
                            break
                    if answer:
                        break

        if not answer:
            answer = "I couldn't find a concise answer right now. Try rephrasing or asking for a summary."

        return {"answer": answer, "source_url": source_url}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Lookup failed: {str(e)[:200]}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
