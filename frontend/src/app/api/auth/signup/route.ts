import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
    try {
        const body = await req.json();
        const backendUrl = process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL || 'http://127.0.0.1:8000';

        const response = await fetch(`${backendUrl}/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Signup failed' }));
            return NextResponse.json(errorData, { status: response.status });
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error('Signup proxy error:', error);
        return NextResponse.json({ detail: 'Internal Server Error' }, { status: 500 });
    }
}
