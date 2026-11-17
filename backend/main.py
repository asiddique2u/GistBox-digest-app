import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas.digest import DigestRequest, DigestResponse
from app.services.url_digest import (
    ContentTooLarge,
    ContentExtractionError,
    DigestGenerationError,
    UnsupportedContentType,
    URLFetchError,
    UnsafeURL,
    generate_url_digest,
)

app = FastAPI(
    title="GistBox API",
    description="API for GistBox application",
    version="1.0.0",
)

frontend_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/digest", response_model=DigestResponse)
def create_digest(request: DigestRequest) -> DigestResponse:
    url = str(request.url)
    try:
        digest = generate_url_digest(url, detail_level=request.detail_level)
    except UnsafeURL as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UnsupportedContentType as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except ContentTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ContentExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except URLFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except DigestGenerationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return DigestResponse(
        url=request.url,
        detail_level=request.detail_level,
        title=digest.title,
        summary=digest.summary,
    )

