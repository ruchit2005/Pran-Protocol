"use client";

import React, { useRef, useState } from "react";

type Props = {
  onTranscribed: (text: string, assistant?: any) => void;
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
          const res = await fetch("/api/chat/voice", {
            method: "POST",
            headers: {
              'Authorization': `Bearer ${token}`
            },
            body: fd,
          });

          if (!res.ok) {
            const txt = await res.text();
            onError?.(`Upload error: ${res.status} ${txt}`);
            return;
          }

          const json = await res.json();
          // Expecting: { text, assistant, audio_url }
          onTranscribed(json.text, json.assistant);

          // 🔊 Auto-play TTS if available
          if (json.audio_url) {
            const audio = new Audio(json.audio_url);
            audio.play().catch((err) =>
              console.error("Audio playback failed:", err)
            );
          }
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
      className={`p-3 rounded-2xl shadow-lg transition-all ${recording
          ? "bg-red-500 hover:bg-red-600 text-white"
          : "from-emerald-500 to-cyan-500 bg-gradient-to-r hover:from-emerald-600 hover:to-cyan-600 text-white"
        }`}
    >
      {recording ? "🛑 Stop" : "🎤 Speak"}
    </button>
  );
}
