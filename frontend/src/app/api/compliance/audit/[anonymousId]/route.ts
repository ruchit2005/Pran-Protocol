import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  req: NextRequest,
  context: { params: Promise<{ anonymousId: string }> }
) {
  try {
    const token = req.headers.get('authorization');
    
    if (!token) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    const { anonymousId } = await context.params;
    const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    
    const response = await fetch(`${backendUrl}/compliance/audit/${anonymousId}`, {
      headers: {
        'Authorization': token,
        'ngrok-skip-browser-warning': 'true'
      }
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch audit trail' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching audit trail:', error);
    return NextResponse.json(
      { error: 'Internal Server Error' },
      { status: 500 }
    );
  }
}
