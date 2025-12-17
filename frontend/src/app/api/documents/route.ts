import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

// Configure body size limit for this route
export const runtime = 'nodejs';
export const maxDuration = 60; // Maximum execution time in seconds

// GET /api/documents - List user documents
export async function GET(request: NextRequest) {
  try {
    const token = request.headers.get('authorization');
    
    if (!token) {
      return NextResponse.json(
        { detail: 'Authorization required' },
        { status: 401 }
      );
    }
    
    const response = await fetch(`${API_URL}/documents`, {
      method: 'GET',
      headers: {
        'Authorization': token,
        'Content-Type': 'application/json',
        'ngrok-skip-browser-warning': 'true',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Backend documents list error:', response.status, errorText);
      try {
        const errorJson = JSON.parse(errorText);
        return NextResponse.json(errorJson, { status: response.status });
      } catch {
        return NextResponse.json(
          { detail: errorText || 'Failed to fetch documents' },
          { status: response.status }
        );
      }
    }

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
    
    if (!token) {
      return NextResponse.json(
        { detail: 'Authorization required' },
        { status: 401 }
      );
    }
    
    const formData = await request.formData();
    const file = formData.get('file') as File;
    
    if (!file) {
      return NextResponse.json(
        { detail: 'No file provided' },
        { status: 400 }
      );
    }

    console.log('Proxying document upload:', file.name, file.size, 'bytes');
    
    const response = await fetch(`${API_URL}/documents/upload`, {
      method: 'POST',
      headers: {
        'Authorization': token,
        'ngrok-skip-browser-warning': 'true',
      },
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Backend document upload error:', response.status, errorText);
      
      // Handle specific error cases
      if (response.status === 401 || response.status === 403) {
        return NextResponse.json(
          { detail: 'Authentication failed. Please log in again.' },
          { status: 401 }
        );
      }
      
      try {
        const errorJson = JSON.parse(errorText);
        return NextResponse.json(errorJson, { status: response.status });
      } catch {
        return NextResponse.json(
          { detail: errorText || 'Upload failed' },
          { status: response.status }
        );
      }
    }

    const data = await response.json();
    console.log('Document upload successful:', data);
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Document upload proxy error:', error);
    return NextResponse.json(
      { detail: 'Failed to upload document' },
      { status: 500 }
    );
  }
}
