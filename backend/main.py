from fastapi import BackgroundTasks, FastAPI, HTTPException

from app.schemas.digest import DigestRequest, DigestResponse
from app.services.request_context import DigestRequestContext
from app.services.url_digest import (
    ContentTooLarge,
    ContentExtractionError,
    DigestGenerationError,
    UnsupportedContentType,
    URLFetchError,
    UnsafeURL,
    process_digest_request,
)

app = FastAPI(
    title="GistBox API",
    description="API for GistBox application",
    version="1.0.0",
)

@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/digest", response_model=DigestResponse)
def create_digest(
    request: DigestRequest, background_tasks: BackgroundTasks
) -> DigestResponse:
    context = DigestRequestContext(
        url=str(request.url),
        detail_level=request.detail_level,
    )
    cleanup_scheduled = False
    try:
        try:
            digest = process_digest_request(context)
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

        response = DigestResponse(
            url=request.url,
            detail_level=request.detail_level,
            title=digest.title,
            summary=digest.summary,
        )
        background_tasks.add_task(context.clear)
        cleanup_scheduled = True
        return response
    finally:
        if not cleanup_scheduled:
            context.clear()

