import { NextResponse } from "next/server";

export async function POST(req: Request) {
  // Forward FormData directly to backend
  const form = await req.formData();

  const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
  const target = `${backendUrl}/chat/voice`;

  // forward the formdata; the Fetch API accepts FormData directly
  const token = req.headers.get('authorization');
  const res = await fetch(target, {
    method: "POST",
    headers: {
      'Authorization': token || '',
      'ngrok-skip-browser-warning': 'true'
    },
    body: form,
    // credentials, headers left default so multipart boundary preserved
  });

  // If backend returns JSON, just forward it
  const text = await res.text();
  try {
    const json = JSON.parse(text);
    return NextResponse.json(json, { status: res.status });
  } catch {
    return new NextResponse(text, { status: res.status });
  }
}
