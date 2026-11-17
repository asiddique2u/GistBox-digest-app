# GistBox

**Turn information into intelligence.**

GistBox turns public web content into clear, useful digests. Its FastAPI
backend can extract an article or YouTube transcript, generate a digest with
an available AI provider, and fall back to an extractive summary when needed.

## Features

- Digest public article URLs and YouTube videos with transcripts.
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

### Install and run

From the repository root:

```shell
uv sync
uv run uvicorn --app-dir backend main:app --reload
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
In PowerShell, use `npm.cmd` (for example, `npm.cmd run dev`) if the execution
policy blocks the `npm.ps1` shim; this does not require changing the policy.

### Deploy the frontend to Vercel

Create a Vercel project from this repository and set its **Root Directory** to
`frontend/nextjs`. The Vercel configuration is in that directory. Set
`DIGEST_API_URL` in the Vercel project's environment variables to the HTTPS URL
of a separately deployed FastAPI backend; the frontend config does not deploy
the Python backend. `DIGEST_API_URL` is required in production.

AI credentials are optional. Without configured providers, GistBox uses the
extractive fallback by default.

The website is available at <http://localhost:3000>.

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

Each digest request keeps its source text or YouTube transcript, metadata, and
result in a request-scoped in-memory context. The context is cleared after the
response is sent; no request data is currently persisted. Its structured
fields provide a clear point to add an opt-in retention store later.

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
render.yaml        Render API service configuration
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

The root `render.yaml` defines the FastAPI web service and does not create a
PostgreSQL database. In Render, create a **Blueprint** from this repository;
Render will use the configured build command, start command, and `/health`
check. Add any AI provider keys in the Render service's environment settings.
Then set `DIGEST_API_URL` in Vercel to the Render service's HTTPS URL. The
free web-service plan may spin down when idle, so the first request after a
quiet period can take longer.

## Roadmap

The longer-term GistBox product direction includes:

- Saved links, digest history, and content search.
- Questions and answers grounded in extracted content, with source references.
- Research across multiple URLs and documents.
- Web and mobile clients using the same backend API.
- User accounts and opt-in data retention.
