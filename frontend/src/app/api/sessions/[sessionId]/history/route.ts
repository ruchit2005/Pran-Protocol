import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest, { params }: { params: Promise<{ sessionId: string }> }) {
    try {
        const backendUrl = process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';
        const token = req.headers.get('authorization');
        const { sessionId } = await params;

        const response = await fetch(`${backendUrl}/sessions/${sessionId}/history`, {
            headers: {
                'Authorization': token || ''
            },
        });

        if (!response.ok) {
            return NextResponse.json({ detail: 'Failed to fetch history' }, { status: response.status });
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        return NextResponse.json({ detail: 'Internal Server Error' }, { status: 500 });
    }
}
