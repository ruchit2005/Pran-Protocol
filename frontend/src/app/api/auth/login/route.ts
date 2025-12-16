import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
    try {
        const formData = await req.formData();
        const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

        // Convert FormData to URLSearchParams for x-www-form-urlencoded
        const params = new URLSearchParams();
        formData.forEach((value, key) => {
            params.append(key, value as string);
        });

        const response = await fetch(`${backendUrl}/auth/login`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/x-www-form-urlencoded',
                'ngrok-skip-browser-warning': 'true'
            },
            body: params,
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Login failed' }));
            return NextResponse.json(errorData, { status: response.status });
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error('Login proxy error:', error);
        return NextResponse.json({ detail: 'Internal Server Error' }, { status: 500 });
    }
}
