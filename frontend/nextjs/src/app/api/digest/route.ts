import { NextResponse } from "next/server";

type DetailLevel = "short" | "medium" | "detailed";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isDigestRequest(
  value: unknown,
): value is { url: string; detail_level: DetailLevel } {
  return (
    isRecord(value) &&
    typeof value.url === "string" &&
    value.url.trim().length > 0 &&
    (value.detail_level === "short" ||
      value.detail_level === "medium" ||
      value.detail_level === "detailed")
  );
}

export async function POST(request: Request) {
  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json(
      { detail: "The request must contain valid JSON." },
      { status: 400 },
    );
  }

  if (!isDigestRequest(payload)) {
    return NextResponse.json(
      { detail: "Provide a URL and a valid digest detail level." },
      { status: 400 },
    );
  }

  const backendUrl =
    process.env.DIGEST_API_URL ??
    (process.env.NODE_ENV === "production" ? null : "http://127.0.0.1:8000");
  if (!backendUrl) {
    console.error("DIGEST_API_URL is required in production.");
    return NextResponse.json(
      { detail: "The digest service URL is not configured." },
      { status: 500 },
    );
  }

  let digestUrl: URL;
  try {
    digestUrl = new URL("/digest", backendUrl);
  } catch {
    console.error("DIGEST_API_URL must be an absolute URL.");
    return NextResponse.json(
      { detail: "The digest service URL is misconfigured." },
      { status: 500 },
    );
  }

  try {
    const upstreamResponse = await fetch(digestUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    });

    let upstreamPayload: unknown;
    try {
      upstreamPayload = await upstreamResponse.json();
    } catch (error) {
      console.error("The digest service returned invalid JSON.", error);
      return NextResponse.json(
        { detail: "The digest service returned an unreadable response." },
        { status: 502 },
      );
    }

    return NextResponse.json(upstreamPayload, {
      status: upstreamResponse.status,
    });
  } catch (error) {
    console.error("Unable to reach the digest service.", error);
    return NextResponse.json(
      {
        detail:
          "Could not connect to GistBox. Make sure the backend is running and try again.",
      },
      { status: 502 },
    );
  }
}
