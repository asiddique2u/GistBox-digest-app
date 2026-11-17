"use client";

import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  Clipboard,
  FileText,
  Link2,
  LoaderCircle,
  Play,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useState, type FormEvent } from "react";

type DetailLevel = "short" | "medium" | "detailed";

type DigestResponse = {
  url: string;
  detail_level: DetailLevel;
  title: string;
  summary: string;
};

const DETAIL_OPTIONS: {
  value: DetailLevel;
  label: string;
  description: string;
}[] = [
  {
    value: "short",
    label: "Short",
    description: "Just the essential takeaways",
  },
  {
    value: "medium",
    label: "Medium",
    description: "The main ideas and context",
  },
  {
    value: "detailed",
    label: "Detailed",
    description: "Full context, examples, and steps",
  },
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isDigestResponse(value: unknown): value is DigestResponse {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.url === "string" &&
    typeof value.title === "string" &&
    typeof value.summary === "string" &&
    (value.detail_level === "short" ||
      value.detail_level === "medium" ||
      value.detail_level === "detailed")
  );
}

function getHostName(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export default function Home() {
  const [url, setUrl] = useState("");
  const [detailLevel, setDetailLevel] = useState<DetailLevel>("detailed");
  const [digest, setDigest] = useState<DigestResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">(
    "idle",
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setDigest(null);
    setCopyState("idle");

    let normalizedUrl: string;
    try {
      const parsedUrl = new URL(url.trim());
      if (parsedUrl.protocol !== "http:" && parsedUrl.protocol !== "https:") {
        throw new Error("Enter a public HTTP or HTTPS link.");
      }
      normalizedUrl = parsedUrl.toString();
    } catch {
      setError("Enter a valid article or YouTube link beginning with http:// or https://.");
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch("/api/digest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: normalizedUrl,
          detail_level: detailLevel,
        }),
      });

      let payload: unknown;
      try {
        payload = await response.json();
      } catch {
        throw new Error("The digest service returned an unreadable response.");
      }

      if (!response.ok) {
        const message =
          isRecord(payload) && typeof payload.detail === "string"
            ? payload.detail
            : "The link could not be digested. Check it and try again.";
        throw new Error(message);
      }

      if (!isDigestResponse(payload)) {
        throw new Error("The digest service returned an unexpected response.");
      }

      setDigest(payload);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Something went wrong while creating the digest.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function copyDigest() {
    if (!digest) {
      return;
    }

    try {
      await navigator.clipboard.writeText(`${digest.title}\n\n${digest.summary}`);
      setCopyState("copied");
    } catch {
      setCopyState("error");
    }
  }

  function startOver() {
    setUrl("");
    setDigest(null);
    setError(null);
    setCopyState("idle");
  }

  return (
    <main className="site-shell">
      <header className="topbar">
        <Link className="brand" href="/" aria-label="GistBox home">
          <span className="brand-mark">
            <BookOpen size={19} strokeWidth={2.2} />
          </span>
          <span className="brand-name">
            gist<span>box</span>
          </span>
        </Link>

        <nav className="topbar-nav" aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <a className="topbar-cta" href="#digest-form">
            Try it out <ArrowUpRight size={15} />
          </a>
        </nav>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">
            <span className="eyebrow-mark" />
            A clearer way to keep up
          </p>
          <h1>
            Get the good parts.
            <br />
            <span>Skip the scroll.</span>
          </h1>
          <p className="hero-description">
            Turn a long article or video into a clear, detailed digest you can
            actually use.
          </p>
        </div>
        <div className="hero-note" aria-label="From link to understanding">
          <div className="hero-note-icon">
            <Sparkles size={19} />
          </div>
          <div>
            <span className="hero-note-label">A little more signal</span>
            <span className="hero-note-copy">in every link you open.</span>
          </div>
          <ArrowUpRight className="hero-note-arrow" size={18} />
        </div>
      </section>

      <section className="workspace" aria-label="Create a digest">
        <form
          className="composer-panel"
          id="digest-form"
          onSubmit={handleSubmit}
        >
          <div className="panel-heading">
            <div className="step-label">
              <span>01</span> START WITH A LINK
            </div>
            <h2>What are you reading?</h2>
            <p>Drop in an article or YouTube link. We’ll take it from here.</p>
          </div>

          <label className="field-label" htmlFor="source-url">
            Article or video URL
          </label>
          <div className={`url-field ${error ? "url-field-error" : ""}`}>
            <Link2 size={19} aria-hidden="true" />
            <input
              autoComplete="url"
              id="source-url"
              inputMode="url"
              name="url"
              onChange={(event) => {
                setUrl(event.target.value);
                if (error) {
                  setError(null);
                }
              }}
              placeholder="https://youtube.com/watch?v=..."
              required
              type="url"
              value={url}
              aria-describedby={error ? "form-error" : undefined}
              aria-invalid={Boolean(error)}
              disabled={isLoading}
            />
            {url.includes("youtube.com") || url.includes("youtu.be") ? (
              <Play
                className="url-type-icon"
                size={18}
                aria-label="Video link"
              />
            ) : null}
          </div>
          {error ? (
            <p className="form-error" id="form-error" role="alert">
              {error}
            </p>
          ) : (
            <p className="field-hint">
              <span className="hint-dot" />
              Public articles and videos with transcripts
            </p>
          )}

          <fieldset className="detail-fieldset" disabled={isLoading}>
            <legend>How much detail do you need?</legend>
            <div className="detail-options">
              {DETAIL_OPTIONS.map((option) => (
                <label
                  className={`detail-option ${
                    detailLevel === option.value ? "detail-option-selected" : ""
                  }`}
                  key={option.value}
                >
                  <input
                    checked={detailLevel === option.value}
                    name="detail-level"
                    onChange={() => setDetailLevel(option.value)}
                    type="radio"
                    value={option.value}
                  />
                  <span className="detail-option-top">
                    <span className="detail-option-name">{option.label}</span>
                    {option.value === "detailed" ? (
                      <span className="default-badge">DEFAULT</span>
                    ) : null}
                  </span>
                  <span className="detail-option-description">
                    {option.description}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <button
            className="submit-button"
            disabled={isLoading || !url.trim()}
            type="submit"
          >
            {isLoading ? (
              <>
                <LoaderCircle className="spin" size={19} />
                <span>Making your digest…</span>
              </>
            ) : (
              <>
                <Sparkles size={18} />
                <span>Create my digest</span>
                <ArrowRight className="submit-arrow" size={18} />
              </>
            )}
          </button>
          <p className="submit-note">
            <FileText size={14} />
            Your digest is ready to read, copy, and keep.
          </p>
        </form>

        <section
          className={`result-panel ${digest ? "result-panel-filled" : ""}`}
          aria-label="Digest result"
          aria-busy={isLoading}
          aria-live="polite"
        >
          <div className="result-panel-top">
            <div className="step-label">
              <span>02</span> YOUR TAKEAWAYS
            </div>
            {digest ? (
              <div className="result-actions">
                <button
                  className="quiet-button"
                  onClick={copyDigest}
                  type="button"
                  aria-label="Copy digest"
                >
                  {copyState === "copied" ? (
                    <Check size={15} />
                  ) : (
                    <Clipboard size={15} />
                  )}
                  {copyState === "copied"
                    ? "Copied"
                    : copyState === "error"
                      ? "Copy unavailable"
                      : "Copy"}
                </button>
                <button
                  className="quiet-button"
                  onClick={startOver}
                  type="button"
                  aria-label="Start a new digest"
                >
                  <RefreshCw size={14} />
                  New
                </button>
              </div>
            ) : null}
          </div>

          {isLoading ? (
            <div className="loading-state">
              <div className="loading-mark">
                <Sparkles size={22} />
              </div>
              <p className="loading-eyebrow">READING THE SOURCE</p>
              <h2>Finding the signal…</h2>
              <p className="loading-copy">
                Pulling together the ideas, context, and useful details.
              </p>
              <div className="loading-lines" aria-hidden="true">
                <span />
                <span />
                <span />
                <span />
              </div>
            </div>
          ) : digest ? (
            <article className="digest-result">
              <div className="digest-meta">
                <span className="ready-indicator">
                  <span />
                  DIGEST READY
                </span>
                <span className="meta-divider">/</span>
                <span>{digest.detail_level} detail</span>
              </div>
              <h2 className="digest-title">{digest.title}</h2>
              <a
                className="source-link"
                href={digest.url}
                rel="noreferrer"
                target="_blank"
              >
                <Link2 size={15} />
                {getHostName(digest.url)}
                <ArrowUpRight size={13} />
              </a>
              <div className="digest-divider" />
              <div className="markdown-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {digest.summary}
                </ReactMarkdown>
              </div>
            </article>
          ) : (
            <div className="empty-state">
              <div className="empty-art" aria-hidden="true">
                <div className="floating-content-chip">
                  <span className="video-chip-icon">
                    <Play size={11} fill="currentColor" />
                  </span>
                  Long-form video
                </div>
                <div className="paper-card">
                  <span className="paper-overline">THE IMPORTANT BITS</span>
                  <span className="paper-line paper-line-strong" />
                  <span className="paper-line paper-line-short" />
                  <span className="paper-bullet">
                    <i />
                    <b />
                  </span>
                  <span className="paper-bullet">
                    <i />
                    <b />
                  </span>
                  <span className="paper-bullet paper-bullet-short">
                    <i />
                    <b />
                  </span>
                </div>
                <div className="floating-sparkle">
                  <Sparkles size={18} />
                </div>
                <div className="floating-source-chip">
                  <Play size={13} />
                  Article or video
                </div>
              </div>
              <p className="empty-eyebrow">YOUR CLEARER TAKEAWAY</p>
              <h2>
                Less noise.
                <br />
                <span>More meaning.</span>
              </h2>
              <p className="empty-copy">
                Your digest will appear here with a quick overview and the
                details worth remembering.
              </p>
            </div>
          )}
        </section>
      </section>

      <section className="how-section" id="how-it-works">
        <div className="how-heading">
          <p className="eyebrow">A BETTER WAY THROUGH THE BACKLOG</p>
          <h2>From open tab to clear head.</h2>
        </div>
        <div className="how-steps">
          <div className="how-step">
            <span className="how-step-icon">
              <Link2 size={18} />
            </span>
            <div>
              <span className="how-step-number">01 / DROP A LINK</span>
              <p>Bring an article or a video with a transcript.</p>
            </div>
          </div>
          <div className="how-step">
            <span className="how-step-icon">
              <Sparkles size={18} />
            </span>
            <div>
              <span className="how-step-number">02 / GET THE SHAPE</span>
              <p>GistBox finds the main ideas and organizes the details.</p>
            </div>
          </div>
          <div className="how-step">
            <span className="how-step-icon">
              <BookOpen size={18} />
            </span>
            <div>
              <span className="how-step-number">03 / KEEP THE INSIGHT</span>
              <p>Read the digest, copy it, and get on with your day.</p>
            </div>
          </div>
        </div>
      </section>

      <footer className="site-footer">
        <Link className="footer-brand" href="/">
          gist<span>box</span>
        </Link>
        <span>Make room for what matters.</span>
      </footer>
    </main>
  );
}
