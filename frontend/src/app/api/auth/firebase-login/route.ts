export async function POST(request: Request) {
  try {
    const { idToken, email, displayName, photoURL } = await request.json();

    // Forward Firebase token to backend for verification
    const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const response = await fetch(`${backendUrl}/auth/firebase-login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'ngrok-skip-browser-warning': 'true',
      },
      body: JSON.stringify({
        id_token: idToken,
        email,
        display_name: displayName,
        photo_url: photoURL,
      }),
    });

    if (!response.ok) {
      // Try to parse as JSON, fallback to text
      let error;
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        error = await response.json();
      } else {
        const text = await response.text();
        console.error('Backend error (non-JSON):', text);
        error = { detail: 'Backend authentication error. Check backend logs.' };
      }
      return Response.json(error, { status: response.status });
    }

    const data = await response.json();
    return Response.json(data);
  } catch (error) {
    console.error('Firebase login error:', error);
    return Response.json(
      { detail: 'Authentication failed' },
      { status: 500 }
    );
  }
}
