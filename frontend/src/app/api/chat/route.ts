// In frontend/src/app/api/chat/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    const { query, history, session_id } = await req.json();
    const token = req.headers.get('authorization');

    const backendUrl = process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';
    const pythonApiUrl = `${backendUrl}/chat`;

    const response = await fetch(pythonApiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token || ''
      },
      body: JSON.stringify({
        query,
        session_id,
        history: history || [],
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { error: errorData.detail || 'Failed to fetch from Python API' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in chat API route:', error);
    return NextResponse.json(
      { error: 'Internal Server Error' },
      { status: 500 }
    );
  }
}