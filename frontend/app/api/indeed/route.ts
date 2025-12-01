import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || process.env.API_KEY || "";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Forward the request to the backend
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    // Add API key if configured (required in production)
    if (API_KEY) {
      headers["X-API-Key"] = API_KEY;
    }

    const response = await fetch(`${BACKEND_URL}/api/jobs/indeed`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response
        .json()
        .catch(() => ({ error: "Unknown error" }));
      return NextResponse.json(
        {
          error:
            errorData.detail ||
            errorData.error ||
            `Backend error: ${response.status}`,
        },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Indeed API error:", error);
    return NextResponse.json(
      { error: "Failed to search jobs", details: error.message },
      { status: 500 }
    );
  }
}
