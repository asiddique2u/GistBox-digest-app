# GistBox

**Turn information into intelligence.**

GistBox turns public web content and uploaded PDFs into clear, useful digests.
Its FastAPI backend can extract an article, YouTube transcript, or PDF text,
generate a digest with an available AI provider, and fall back to an extractive
summary when needed.

## Features

- Digest public article URLs and YouTube videos with transcripts.
- Upload PDFs up to 10 MB and 20 pages, including scanned PDFs processed with
  Tesseract OCR.
- Choose `short`, `medium`, or `detailed` coverage without a generated
  word-count cap.
- Try configured AI providers in order, with support for OpenAI, Gemini,
  Anthropic, Ollama, and OpenRouter.
- Use an extractive fallback when AI providers are unavailable.
- Explore the API interactively with the generated OpenAPI docs.

## Quick start

### Requirements

- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/)
- Tesseract OCR installed and available on `PATH` to process scanned PDFs

### Install and run

From the repository root:

```shell
uv sync
cd backend
uv run uvicorn main:app --reload
```

The API is available at <http://127.0.0.1:8000>. Open
<http://127.0.0.1:8000/docs> to try the endpoints.

### Run the frontend

Requires Node.js 20.9 or newer.

In another terminal:

```shell
cd frontend/nextjs
npm install
npm run dev
```

Open <http://localhost:3000>. The frontend proxies digest requests to
`http://127.0.0.1:8000` by default. To use another backend, copy
`frontend/nextjs/.env.example` to `.env.local` and set `DIGEST_API_URL`.
PDF uploads go directly from the browser to the backend; set
`NEXT_PUBLIC_DIGEST_API_URL` to that backend's URL. The backend allows
`localhost:3000` and `127.0.0.1:3000` by default for local development.
The Render Docker image installs Tesseract automatically; local scanned-PDF
processing requires the Tesseract executable to be installed separately.
In PowerShell, use `npm.cmd` (for example, `npm.cmd run dev`) if the execution
policy blocks the `npm.ps1` shim; this does not require changing the policy.

### Deploy the frontend to Vercel

Create a Vercel project from this repository and set its **Root Directory** to
`frontend/nextjs`. The Vercel configuration is in that directory. Set
`DIGEST_API_URL` in the Vercel project's environment variables to the HTTPS URL
of a separately deployed FastAPI backend. Also set
`NEXT_PUBLIC_DIGEST_API_URL` to the same URL for direct PDF uploads; this
variable is embedded in the frontend build. The frontend config does not deploy
the Python backend, and both variables are required in production.

AI credentials are optional. Without configured providers, GistBox uses the
extractive fallback by default.

## API

### `POST /digest`

Request a digest for a public article or supported YouTube URL:

```json
{
  "url": "https://example.com/article",
  "detail_level": "detailed"
}
```

`detail_level` is optional and defaults to `detailed`. It controls coverage depth;
there is no generated word-count limit. Digests use Markdown bullets and adapt
to the source (for example, video summaries start with an overview of what and
how the video presents its subject before detailed bullets; tutorials use
numbered steps; reviews identify products and source-provided ratings; and
educational digests cover topics with brief explanations).

| Level | Coverage |
| --- | --- |
| `short` | Essential takeaways with enough detail to understand them |
| `medium` | Main points, context, and important supporting details |
| `detailed` | Thorough coverage of important ideas, examples, steps, and supporting details |

Example response:

```json
{
  "url": "https://example.com/article",
  "detail_level": "detailed",
  "title": "A concise digest title",
  "summary": "- The article's main point and supporting details.\n- Why the findings matter."
}
```

In PowerShell, you can call the endpoint with:

```powershell
$body = @{
  url = "https://example.com/article"
  detail_level = "detailed"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/digest" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
```

Other useful endpoints:

- `GET /health` — checks that the API is running.
- `GET /docs` — interactive API documentation.

Only public HTTP(S) destinations are accepted. Private destinations and
redirects to private addresses are rejected. The endpoint accepts HTML pages
up to 2 MB; unsupported content types are rejected.

### `POST /digest/pdf`

Upload a PDF as `multipart/form-data` with the fields `file` and optional
`detail_level` (`short`, `medium`, or `detailed`). Selectable text is extracted
directly; pages without usable embedded text are processed with Tesseract OCR.
Uploads are limited to 10 MB and 20 pages. The response includes the uploaded
filename, detail level, title, and summary. For example:

```shell
curl.exe -X POST http://127.0.0.1:8000/digest/pdf `
  -F "file=@report.pdf" `
  -F "detail_level=detailed"
```

The browser uploads PDFs directly to the Render API rather than through the
Next.js proxy. Configure `CORS_ALLOWED_ORIGINS` on Render as a comma-separated
list containing the exact Vercel production origin and any local development
origins you need, for example `https://your-site.vercel.app,http://localhost:3000`.
Do not use a wildcard origin.

Each digest request keeps its source text or YouTube transcript, metadata, and
result in a request-scoped in-memory context. The context is cleared after the
response is sent; no request data is currently persisted. PDF files are
processed from temporary storage and removed on both success and failure. Its
structured fields provide a clear point to add an opt-in retention store later.

## AI provider configuration

Create `backend/app/.env` and add credentials for the providers you want to
enable. Keep this file private; it is excluded from Git.

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash-lite

ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-5

OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4o-mini

OLLAMA_MODEL=
OLLAMA_BASE_URL=http://localhost:11434/v1

DIGEST_PROVIDER_ORDER=openai,gemini,anthropic,ollama,openrouter
DIGEST_EXTRACTIVE_FALLBACK=true
```

Provider details:

- Only providers with credentials are attempted. Gemini accepts
  `GEMINI_API_KEY` or `GOOGLE_API_KEY`.
- OpenRouter uses `OPENROUTER_API_KEY` and defaults to
  `openai/gpt-4o-mini`; set `OPENROUTER_MODEL` to choose another supported
  model.
- Ollama is enabled when `OLLAMA_MODEL` is set and its server is available.
- Providers are tried in `DIGEST_PROVIDER_ORDER`; each request has a
  30-second timeout.
- If all providers fail, the default extractive fallback uses the source
  content without an AI request. Set `DIGEST_EXTRACTIVE_FALLBACK=false` to
  disable it.

## Project structure

```text
backend/
  app/
    schemas/       API request and response models
    services/
      request_context.py  Request-scoped transient digest data
      agent/       Digest generation and provider adapters
      extraction/  Web and video content extraction
  tests/           Backend tests
  main.py          FastAPI application
frontend/nextjs/   Frontend workspace
mobile/flutter/    Mobile workspace
```

The backend is organized as a modular monolith. Provider integrations are
isolated behind adapters so provider selection and fallback do not require
changes to the digest API.

## Run tests

From the `backend` directory:

```shell
uv run python -m unittest discover -s tests
```

## Deploy the backend to Render

The root `render.yaml` defines the FastAPI Docker web service and does not
create a PostgreSQL database. The Dockerfile installs Tesseract and the Python
dependencies. In Render, create or sync a **Blueprint** from this repository,
then set `CORS_ALLOWED_ORIGINS` to the exact Vercel production origin (and any
local development origin you need). Add any AI provider keys in the Render
service's environment settings. In Vercel, set both `DIGEST_API_URL` and
`NEXT_PUBLIC_DIGEST_API_URL` to the Render service's HTTPS URL, then redeploy
the frontend.

## Roadmap

The longer-term GistBox product direction includes:

- Saved links, digest history, and content search.
- Questions and answers grounded in extracted content, with source references.
- Research across multiple URLs and documents.
- Web and mobile clients using the same backend API.
- User accounts and opt-in data retention.
