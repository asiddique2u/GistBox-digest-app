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

AI credentials are optional. Without configured providers, GistBox uses the
extractive fallback by default.

To run the website locally, open another terminal:

```shell
cd frontend/nextjs
npm install
Copy-Item .env.example .env.local
npm run dev
```

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

## Roadmap

The longer-term GistBox product direction includes:

- Saved links, digest history, and content search.
- Questions and answers grounded in extracted content, with source references.
- Research across multiple URLs and documents.
- Web and mobile clients using the same backend API.
- User accounts, persistence, and deployment.

## Deployment

The API is configured as a Render web service in `render.yaml`; the website
deploys separately to Vercel.

### Deploy the API to Render

1. Push the repository to GitHub and create a Render **Blueprint** from it.
   Render will use `render.yaml` at the repository root, install the locked
   dependencies with `uv`, and check the service at `/health`.
2. Set `FRONTEND_ORIGINS` in the Render service's environment to the exact
   website origin, for example `https://your-project.vercel.app`. Multiple
   origins can be comma-separated. Until the Vercel URL is available, use
   `http://localhost:3000`.
3. Add any AI provider API keys you want to use in Render's environment
   settings. Without keys, the extractive fallback remains available.
4. Copy the service's public URL, such as `https://gistbox-api.onrender.com`.

The Blueprint uses Render's free web-service plan. Free services can spin down
when idle, so the first request after a quiet period may take longer.

### Deploy the website to Vercel

1. Import the same GitHub repository as a Vercel project.
2. Set **Root Directory** to `frontend/nextjs`; Vercel should detect Next.js.
3. Add `NEXT_PUBLIC_API_URL` with the Render service URL (no trailing slash),
   then deploy.
4. Update Render's `FRONTEND_ORIGINS` to the exact Vercel production URL and
   redeploy/restart the API. Add any Vercel preview origins you want to permit
   as additional comma-separated values.

For local frontend development, set `NEXT_PUBLIC_API_URL` in
`frontend/nextjs/.env.local` to `http://localhost:8000`. The
`NEXT_PUBLIC_API_URL` value is public and must contain only the API URL; never
put API keys in `NEXT_PUBLIC_` variables.
