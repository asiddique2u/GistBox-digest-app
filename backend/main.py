import os

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import TypeAdapter, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from app.agent.digest_models import DigestDetailLevel
from app.schemas.digest import DigestRequest, DigestResponse
from app.services.content_digest import DigestGenerationError
from app.services.pdf_digest import (
    MAX_REQUEST_BODY_BYTES,
    OCRProcessingError,
    OCRUnavailableError,
    PDFPageLimitError,
    PDFProcessingError,
    PDFTooLargeError,
    UnsupportedPDFError,
    process_pdf_digest,
)
from app.services.request_context import DigestRequestContext
from app.services.url_digest import (
    ContentTooLarge,
    ContentExtractionError,
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

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
if "*" in allowed_origins:
    raise ValueError("CORS_ALLOWED_ORIGINS must contain explicit origins.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post(
    "/digest",
    response_model=DigestResponse,
    response_model_exclude_none=True,
)
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


@app.post(
    "/digest/pdf",
    response_model=DigestResponse,
    response_model_exclude_none=True,
)
async def create_pdf_digest(
    request: Request, background_tasks: BackgroundTasks
) -> DigestResponse:
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            request_size = int(content_length)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="The request has an invalid Content-Length header.",
            ) from exc
        if request_size < 0:
            raise HTTPException(
                status_code=400,
                detail="The request has an invalid Content-Length header.",
            )
        if request_size > MAX_REQUEST_BODY_BYTES:
            raise HTTPException(
                status_code=413,
                detail="The upload exceeds the 10 MB file limit.",
            )

    form = await request.form(max_files=1, max_fields=1)
    try:
        file = form.get("file")
        if not isinstance(file, UploadFile):
            raise HTTPException(
                status_code=422,
                detail="Provide one PDF file in the 'file' field.",
            )
        try:
            detail_level = TypeAdapter(DigestDetailLevel).validate_python(
                form.get("detail_level", "detailed")
            )
        except ValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail="Choose a valid digest detail level.",
            ) from exc

        return await _create_pdf_digest_response(
            file=file,
            detail_level=detail_level,
            background_tasks=background_tasks,
        )
    finally:
        await form.close()


async def _create_pdf_digest_response(
    file: UploadFile,
    detail_level: DigestDetailLevel,
    background_tasks: BackgroundTasks,
) -> DigestResponse:
    context = DigestRequestContext(
        url="",
        detail_level=detail_level,
        source_type="pdf",
    )
    cleanup_scheduled = False
    try:
        try:
            digest = await run_in_threadpool(
                process_pdf_digest,
                source=file.file,
                filename=file.filename or "",
                detail_level=detail_level,
                context=context,
            )
        except UnsupportedPDFError as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc
        except (PDFTooLargeError, PDFPageLimitError) as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        except PDFProcessingError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except OCRUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except OCRProcessingError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except DigestGenerationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        response = DigestResponse(
            filename=context.filename,
            detail_level=detail_level,
            title=digest.title,
            summary=digest.summary,
        )
        background_tasks.add_task(context.clear)
        cleanup_scheduled = True
        return response
    finally:
        if not cleanup_scheduled:
            context.clear()

