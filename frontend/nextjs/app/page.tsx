"use client";

import { FormEvent, useState } from "react";

type DetailLevel = "short" | "medium" | "detailed";

type Digest = {
  url: string;
  detail_level: DetailLevel;
  title: string;
  summary: string;
};

function isDigest(payload: unknown): payload is Digest {
  if (typeof payload !== "object" || payload === null) {
    return false;
  }

  return (
    "url" in payload &&
    typeof payload.url === "string" &&
    "detail_level" in payload &&
    (payload.detail_level === "short" ||
      payload.detail_level === "medium" ||
      payload.detail_level === "detailed") &&
    "title" in payload &&
    typeof payload.title === "string" &&
    "summary" in payload &&
    typeof payload.summary === "string"
  );
}

function getErrorMessage(payload: unknown, status: number): string {
  if (
    typeof payload === "object" &&
    payload !== null &&
    "detail" in payload &&
    typeof payload.detail === "string"
  ) {
    return payload.detail;
  }
  return `The request failed (HTTP ${status}). Please try again.`;
}

export default function Home() {
  const [url, setUrl] = useState("");
  const [detailLevel, setDetailLevel] = useState<DetailLevel>("detailed");
  const [digest, setDigest] = useState<Digest | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setDigest(null);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "");
    if (!apiUrl) {
      setError(
        "The API URL is not configured. Set NEXT_PUBLIC_API_URL in the Vercel project settings and redeploy.",
      );
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${apiUrl}/digest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, detail_level: detailLevel }),
      });
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(getErrorMessage(payload, response.status));
      }
      if (!isDigest(payload)) {
        throw new Error("The API returned an unexpected response.");
      }
      setDigest(payload);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Something went wrong while creating your digest.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="page-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="GistBox home">
          <span className="brand-mark" aria-hidden="true">
            G
          </span>
          <span>GistBox</span>
        </a>
        <span className="topbar-note">A little less scrolling. A lot more knowing.</span>
      </header>

      <section className="hero" aria-labelledby="page-title">
        <div className="eyebrow">
          <span className="eyebrow-dot" />
          YOUR PERSONAL READING COMPANION
        </div>
        <h1 id="page-title">
          Make room for
          <br />
          <span>the good stuff.</span>
        </h1>
        <p className="hero-copy">
          Drop in an article or YouTube link. Get the ideas that matter, without
          the endless scroll.
        </p>

        <form className="digest-form" onSubmit={handleSubmit}>
          <label className="field-label" htmlFor="source-url">
            SOURCE LINK
          </label>
          <div className="url-field">
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              className="link-icon"
            >
              <path
                d="M10 13.5a4 4 0 0 0 5.66 0l3-3A4 4 0 0 0 13 4.84l-1.72 1.72M14 10.5a4 4 0 0 0-5.66 0l-3 3A4 4 0 0 0 13 19.16l1.72-1.72"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
              />
            </svg>
            <input
              id="source-url"
              type="url"
              inputMode="url"
              placeholder="Paste an article or YouTube URL"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              required
            />
          </div>

          <div className="form-footer">
            <div className="detail-control">
              <label className="field-label" htmlFor="detail-level">
                HOW MUCH DETAIL?
              </label>
              <select
                id="detail-level"
                value={detailLevel}
                onChange={(event) =>
                  setDetailLevel(event.target.value as DetailLevel)
                }
              >
                <option value="short">Quick read</option>
                <option value="medium">The essentials</option>
                <option value="detailed">The full picture</option>
              </select>
            </div>
            <button className="submit-button" type="submit" disabled={isLoading}>
              {isLoading ? (
                <>
                  <span className="spinner" aria-hidden="true" />
                  Working on it
                </>
              ) : (
                <>
                  Make my digest
                  <span aria-hidden="true">→</span>
                </>
              )}
            </button>
          </div>
        </form>

        <p className="privacy-note">
          <svg
            aria-hidden="true"
            viewBox="0 0 20 20"
            fill="none"
            className="lock-icon"
          >
            <rect
              x="4.25"
              y="8.25"
              width="11.5"
              height="8.5"
              rx="2"
              stroke="currentColor"
              strokeWidth="1.5"
            />
            <path
              d="M6.75 8V5.75a3.25 3.25 0 0 1 6.5 0V8"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
          Only public pages and videos are supported.
        </p>

        {error && (
          <p className="message error-message" role="alert">
            {error}
          </p>
        )}

        {digest && (
          <article className="digest-result" aria-live="polite">
            <div className="result-heading">
              <div>
                <span className="result-kicker">YOUR DIGEST</span>
                <h2>{digest.title}</h2>
              </div>
              <span className="result-level">{digest.detail_level}</span>
            </div>
            <p className="result-source">{digest.url}</p>
            <div className="digest-summary">{digest.summary}</div>
          </article>
        )}
      </section>

      <footer className="page-footer">
        <span>Read less. Understand more.</span>
        <span>GistBox</span>
      </footer>
    </main>
  );
}
