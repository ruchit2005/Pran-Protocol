"use client";

import React, { useRef, useState } from "react";

type Props = {
  onTranscribed: (text: string, language?: string) => void;
  onError?: (err: string) => void;
};

export default function VoiceRecorder({ onTranscribed, onError }: Props) {
  const [recording, setRecording] = useState(false);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      mediaRef.current = mr;
      chunksRef.current = [];

      mr.ondataavailable = (e: BlobEvent) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
      };

      mr.onstop = async () => {
        try {
          const blob = new Blob(chunksRef.current, { type: mediaRef.current?.mimeType || "audio/webm" });
          const fd = new FormData();
          fd.append("file", blob, "voice.webm");

          const token = localStorage.getItem("token");
          // Use new decouple endpoint
          const res = await fetch("/api/transcribe", {
            method: "POST",
            headers: {
              'Authorization': `Bearer ${token}`
            },
            body: fd,
          });

          if (!res.ok) {
            if (res.status === 401) {
              window.location.href = "/login";
              return;
            }
            const txt = await res.text();
            onError?.(`Upload error: ${res.status} ${txt}`);
            return;
          }

          const json = await res.json();
          // Expecting: { text, language }
          onTranscribed(json.text, json.language);

          // Audio playback logic moved to parent component
        } catch (err: any) {
          onError?.(err?.message || "Upload failed");
        }
      };

      mr.start();
      setRecording(true);
    } catch (err: any) {
      onError?.(err?.message || "Microphone not accessible");
    }
  }

  function stopRecording() {
    if (mediaRef.current && mediaRef.current.state !== "inactive") {
      mediaRef.current.stop();
      mediaRef.current.stream.getTracks().forEach((t) => t.stop());
    }
    setRecording(false);
  }

  return (
    <button
      onClick={() => (recording ? stopRecording() : startRecording())}
      className={`p-3 rounded-full shadow-lg transition-all flex items-center gap-2 ${recording
        ? "bg-red-500 hover:bg-red-600 text-white animate-pulse"
        : "bg-white/10 hover:bg-white/20 text-white border border-white/10"
        }`}
    >
      {recording ? (
        <>
          <div className="w-2 h-2 rounded-full bg-white animate-ping" />
          <span className="text-sm font-medium">Recording...</span>
        </>
      ) : (
        "🎤"
      )}
    </button>
  );
}
