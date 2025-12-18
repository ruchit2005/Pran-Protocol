// In frontend/src/app/api/chat/route.ts
import { NextRequest, NextResponse } from 'next/server';

// Configure route for longer execution time (document processing can take time)
export const maxDuration = 60; // 60 seconds for Vercel
export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  try {
    // Extract ALL fields from request body
    const body = await req.json();
    const { query, history, session_id, generate_audio, latitude, longitude, locale } = body;
    const token = req.headers.get('authorization');

    const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const pythonApiUrl = `${backendUrl}/chat`;

    // Create abort controller with longer timeout for document processing
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 55000); // 55 second timeout

    try {
      const response = await fetch(pythonApiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token || '',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({
          query,
          session_id,
          history: history || [],
          generate_audio,
          latitude,
          longitude,
          locale
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json();
        return NextResponse.json(
          { error: errorData.detail || 'Failed to fetch from Python API' },
          { status: response.status }
        );
      }

      const data = await response.json();
      return NextResponse.json(data);
    } catch (fetchError: any) {
      clearTimeout(timeoutId);
      
      if (fetchError.name === 'AbortError') {
        return NextResponse.json(
          { error: 'Request timeout - document processing took too long. Please try with a smaller document or simpler query.' },
          { status: 504 }
        );
      }
      throw fetchError;
    }
  } catch (error) {
    console.error('Error in chat API route:', error);
    return NextResponse.json(
      { error: 'Internal Server Error' },
      { status: 500 }
    );
  }
}