import { NextResponse } from "next/server";

export async function POST(req: Request) {
    const body = await req.json();

    const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    const target = `${backendUrl}/tts`;

    const token = req.headers.get('authorization');

    const res = await fetch(target, {
        method: "POST",
        headers: {
            'Content-Type': 'application/json',
            'Authorization': token || '',
            'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify(body),
    });

    const text = await res.text();
    try {
        const json = JSON.parse(text);
        return NextResponse.json(json, { status: res.status });
    } catch {
        return new NextResponse(text, { status: res.status });
    }
}
