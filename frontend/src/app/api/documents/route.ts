import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

// GET /api/documents - List user documents
export async function GET(request: NextRequest) {
  try {
    const token = request.headers.get('authorization');
    
    const response = await fetch(`${API_URL}/documents`, {
      method: 'GET',
      headers: {
        'Authorization': token || '',
        'Content-Type': 'application/json',
        'ngrok-skip-browser-warning': 'true',
      },
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Documents list proxy error:', error);
    return NextResponse.json(
      { detail: 'Failed to fetch documents' },
      { status: 500 }
    );
  }
}

// POST /api/documents - Upload document
export async function POST(request: NextRequest) {
  try {
    const token = request.headers.get('authorization');
    const formData = await request.formData();
    
    const response = await fetch(`${API_URL}/documents/upload`, {
      method: 'POST',
      headers: {
        'Authorization': token || '',
        'ngrok-skip-browser-warning': 'true',
      },
      body: formData,
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Document upload proxy error:', error);
    return NextResponse.json(
      { detail: 'Failed to upload document' },
      { status: 500 }
    );
  }
}
