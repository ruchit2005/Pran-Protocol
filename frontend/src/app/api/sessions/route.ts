import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
    try {
        const body = await req.json();
        const backendUrl = process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';
        const token = req.headers.get('authorization');

        const response = await fetch(`${backendUrl}/sessions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': token || ''
            },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            return NextResponse.json({ detail: 'Failed to create session' }, { status: response.status });
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch {
        return NextResponse.json({ detail: 'Internal Server Error' }, { status: 500 });
    }
}

export async function GET(req: NextRequest) {
    try {
        const backendUrl = process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';
        const token = req.headers.get('authorization');

        const response = await fetch(`${backendUrl}/sessions`, {
            headers: {
                'Authorization': token || ''
            },
        });

        if (!response.ok) {
            return NextResponse.json({ detail: 'Failed to fetch sessions' }, { status: response.status });
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch {
        return NextResponse.json({ detail: 'Internal Server Error' }, { status: 500 });
    }
}
