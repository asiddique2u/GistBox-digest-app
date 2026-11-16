Project: Infera – AI-Powered Content Intelligence Platform
Act as a Senior Software Architect, AI Engineer and Product Manager.
I want to build a product called Infera, an AI-powered content digest and research assistant available through a website and mobile application.
1. Product Vision
Infera converts information available across the internet into structured, understandable knowledge.
Users provide a URL, and the application:
	1. Extracts the content using Python libraries.
	2. Cleans and structures the extracted information.
	3. Uses AI to generate a digest.
	4. Allows users to ask questions about the extracted content.
	5. Generates context-aware answers with references to the original content.
The long-term vision is to make Infera an AI-powered personal research and knowledge management platform.
Tagline: Turn information into intelligence.
2. Core Features
Content Extraction
	• Accept website URLs.
	• Extract article content, title, author and publication date.
	• Support static and JavaScript-rendered websites.
	• Support PDFs.
	• Keep extraction modular so additional content sources can be introduced.
	• Avoid unnecessary website-specific extraction logic.
Suggested libraries:
	• Trafilatura
	• BeautifulSoup
	• Playwright
	• PyMuPDF
	• Newspaper4k
AI Digest Generation
Generate different digest formats:
	• Quick summary
	• Detailed summary
	• Key takeaways
	• Technical explanation
	• Important facts and statistics
	• Conclusions and recommendations
Use structured JSON responses.
AI Question Answering
	• Implement Retrieval Augmented Generation (RAG).
	• Divide extracted content into chunks.
	• Generate embeddings.
	• Store embeddings in a vector database.
	• Retrieve relevant content for user questions.
	• Generate answers grounded in extracted content.
	• Include references to relevant sections of the source.
Link Management
	• Save submitted URLs.
	• Maintain digest history.
	• Organize links into categories.
	• Search saved content.
	• Favourite important content.
	• Regenerate digests.
Multi-Source Research
Plan for future capabilities:
	• Submit multiple URLs.
	• Generate combined digests.
	• Compare information across sources.
	• Ask questions across multiple documents.
	• Identify conflicting information between sources.
Mobile Application
	• Android and iOS support.
	• URL submission.
	• Digest viewing.
	• AI question answering.
	• Saved content.
	• Android Share integration to send URLs directly from other applications.
3. Technology Stack
Prefer the following technologies:
Backend:
	• Python
	• FastAPI
	• Pydantic
Frontend:
	• React
	• Next.js
	• TypeScript
Mobile:
	• Flutter
	• Dart
Database:
	• PostgreSQL
	• pgvector
AI:
	• OpenAI API initially.
	• Design a provider-independent AI integration layer to support Gemini and locally hosted LLMs in the future.
Background Processing:
	• Redis
	• Celery
Deployment:
	• Docker
	• Linux server
	• Cloud deployment
4. Architecture Requirements
Design a modular architecture with clear separation between:
	1. API layer
	2. Authentication and user management
	3. URL processing
	4. Content extraction
	5. Content cleaning and normalization
	6. AI digest generation
	7. Embedding generation
	8. Vector search
	9. RAG-based question answering
	10. Content management
	11. Background processing
Both website and mobile application must communicate with the same backend APIs.
Avoid unnecessary microservices during the initial development. Start with a modular monolith.
5. Development Approach
I want to develop this incrementally.
Break the project into milestones:
Milestone 1: Backend foundation and URL extraction.
Milestone 2: AI digest generation.
Milestone 3: RAG implementation and question answering.
Milestone 4: Database integration and authentication.
Milestone 5: Website development.
Milestone 6: Mobile application development.
Milestone 7: Testing, optimization and deployment.
For every milestone provide:
	• Objectives
	• Technical implementation
	• Required libraries
	• Folder structure
	• API endpoints
	• Database changes
	• Development tasks
	• Testing strategy
	• Expected deliverables
	• Completion criteria
6. Development Principles
	• Maintain clean, modular Python code.
	• Follow SOLID principles where appropriate.
	• Use type hints.
	• Implement proper logging and exception handling.
	• Write unit and integration tests.
	• Use environment variables for configuration.
	• Never hardcode API keys.
	• Implement asynchronous processing for lengthy extraction and AI operations.
	• Design APIs to be reusable across web and mobile.
	• Consider API rate limits and AI token costs.
	• Include security measures against SSRF and malicious URLs.
	• Respect website access restrictions, robots.txt and copyright considerations.
	• Store extracted content to avoid unnecessary repeated processing.
7. AI Architecture
Do not tightly couple business logic to a particular AI provider.
Create an abstraction layer for:
	• Text generation
	• Summarization
	• Embedding generation
	• Question answering
Support switching between AI providers through configuration.
Plan for token optimization, context management and caching.
8. Expected Deliverables
Before writing code, provide:
	1. Complete product requirements document.
	2. High-level system architecture.
	3. Technology stack justification.
	4. Database schema.
	5. API design.
	6. Backend folder structure.
	7. Frontend architecture.
	8. Mobile application architecture.
	9. Development roadmap.
	10. Deployment strategy.
	11. Estimated infrastructure and AI API costs.
Also identify potential technical challenges and risks.
9. Working Instructions
Do not attempt to implement the entire application in one step.
First, prepare the complete technical and product plan.
Review the architecture for unnecessary complexity and recommend simplifications.
Once the plan is finalized, proceed milestone by milestone.
For each milestone:
	• Explain the implementation.
	• Generate production-quality code.
	• Explain important technical decisions.
	• Provide execution instructions.
	• Include tests.
	• Verify that the milestone works before proceeding.
Prioritize building a functional MVP before adding advanced features.
The goal is to build Infera as a maintainable, scalable product rather than a simple AI summarization script.

AI Provider Independence – Core Architecture Requirement
Infera must support multiple AI providers without requiring changes to business logic or application code.
The architecture must not be tightly coupled to OpenAI or any individual LLM provider.
1. Supported AI Providers
Design the system to support:
	• OpenAI API
	• Google Gemini API
	• Anthropic Claude API
	• Meta Llama
	• Mistral AI
	• Locally hosted models through Ollama
	• vLLM-hosted models
	• Other compatible LLM APIs
The architecture should allow new providers to be integrated through independent adapters.
2. Provider Abstraction Layer
Create a centralized AI provider interface.
Separate the following capabilities:
	• Text generation
	• Summarization
	• Structured JSON generation
	• Embedding generation
	• Question answering
	• Content classification
Each provider should implement the relevant interfaces.
Example architecture:
AI Service
|
AI Provider Manager
|
+-- OpenAI Adapter
+-- Gemini Adapter
+-- Claude Adapter
+-- Ollama Adapter
+-- vLLM Adapter
+-- Custom LLM Adapter
Business logic must communicate only with the AI service layer.
3. Dynamic Provider Selection
Allow provider and model selection through configuration.
Example:
AI_PROVIDER=openai
AI_MODEL=gpt-model
Alternatively:
AI_PROVIDER=gemini
AI_MODEL=gemini-model
Or:
AI_PROVIDER=ollama
AI_MODEL=local-model
The actual model identifiers must be configurable rather than hardcoded.
4. Model Routing
Plan for intelligent model selection.
Examples:
	• Quick summaries → Fast, economical model.
	• Detailed summaries → High-quality reasoning model.
	• Question answering → Model optimized for contextual responses.
	• Embeddings → Dedicated embedding model.
	• Complex multi-document research → More capable model.
Allow users or administrators to configure model preferences.
5. Provider Fallback
Implement optional fallback mechanisms.
Example:
Primary: Gemini
Fallback: OpenAI
Secondary fallback: Local Ollama model
If the primary provider is unavailable, the system should optionally switch to another provider.
Include timeout handling, retries and provider health monitoring.

Digest generation tries providers in the order configured by
`DIGEST_PROVIDER_ORDER` (default: `openai,gemini,anthropic,ollama`). Add the
credentials and model IDs for providers you want to enable to the backend
environment:

```dotenv
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.5-flash-lite
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=claude-sonnet-4-5
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434/v1
DIGEST_PROVIDER_ORDER=openai,gemini,anthropic,ollama
DIGEST_EXTRACTIVE_FALLBACK=true
```

Only providers with credentials are attempted; Ollama is enabled only when
`OLLAMA_MODEL` is set and its server is reachable. Each request has a 30-second
timeout. If every enabled provider fails, the default extractive fallback uses
the article title and opening sentences without an AI call. Set
`DIGEST_EXTRACTIVE_FALLBACK=false` to disable it.

6. Embedding Compatibility
Do not assume embeddings from different providers are interchangeable.
Store:
	• Provider
	• Model name
	• Embedding dimensions
	• Model version
	• Content chunk identifier
Implement separate embedding configurations and re-embedding mechanisms when changing embedding models.
7. Cost and Performance Monitoring
Track AI usage independently for each provider:
	• Input tokens
	• Output tokens
	• Estimated cost
	• Response latency
	• Model name
	• Provider
	• Success/failure rate
Provide a mechanism to compare provider performance and cost.
8. Important Architectural Rule
Adding a new LLM provider must require implementing an adapter and registering it with the provider manager.
It must NOT require modifying:
	• Content extraction logic
	• Digest generation business logic
	• RAG implementation
	• API endpoints
	• Website frontend
	• Mobile application
The system should be designed around interchangeable AI providers from the beginning.

## URL Digest API

Start the backend from the `backend` directory:

```powershell
uv run uvicorn main:app --reload
```

Send a public article URL to `POST /digest`:

```powershell
curl.exe -X POST http://127.0.0.1:8000/digest `
  -H "Content-Type: application/json" `
  -d '{"url":"https://example.com/article","detail_level":"medium"}'
```

`detail_level` accepts `short`, `medium`, or `detailed` and defaults to
`medium`. Summary length targets are 5-10%, 15-25%, and 25-35% of the source
word count respectively, measured against the up-to-8,000-character excerpt
sent to the model. These are soft targets, not minimums; providers may return
shorter summaries. The response includes the selected level, title, and summary:

```json
{
  "url": "https://example.com/article",
  "detail_level": "medium",
  "title": "A concise digest title",
  "summary": "The article's main points and why they matter."
}
```

The endpoint extracts text from public HTML pages and YouTube transcripts.
Non-public destinations, non-HTML pages, and pages larger than 2 MB are rejected.
Interactive API documentation is available at `/docs`.

