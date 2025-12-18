"use client";

import React, { useRef, useState } from "react";
import { Mic, Square } from "lucide-react";
import { useTranslations } from 'next-intl';

type Props = {
  onTranscribed: (text: string, language?: string) => void;
  onError?: (err: string) => void;
  onProcessingChange?: (isProcessing: boolean) => void;
};

export default function VoiceRecorder({ onTranscribed, onError, onProcessingChange }: Props) {
  const [recording, setRecording] = useState(false);
  const t = useTranslations('Chat');
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
        onProcessingChange?.(true); // Start processing indicator
        try {
          const blob = new Blob(chunksRef.current, { type: mediaRef.current?.mimeType || "audio/webm" });
          const fd = new FormData();
          fd.append("file", blob, "voice.webm");

          const token = localStorage.getItem("token");

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
            onProcessingChange?.(false);
            return;
          }

          const json = await res.json();
          onTranscribed(json.text, json.language);

          // 🔊 Auto-play TTS if available
          if (json.audio_url) {
            const audio = new Audio(json.audio_url);
            audio.play().catch((err) =>
              console.error("Audio playback failed:", err)
            );
          }
        } catch (err: unknown) {
          if (err instanceof Error) {
            onError?.(err.message || "Upload failed");
          } else {
            onError?.("Upload failed");
          }
        } finally {
          onProcessingChange?.(false); // End processing indicator
        }
      };

      mr.start();
      setRecording(true);
    } catch (err: unknown) {
      if (err instanceof Error) {
        onError?.(err.message || "Microphone not accessible");
      } else {
        onError?.("Microphone not accessible");
      }
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
      className={`p-3.5 rounded-full shadow-lg transition-all duration-300 flex items-center justify-center group ${recording
        ? "bg-accent text-white ring-4 ring-accent/20 animate-pulse"
        : "bg-white text-primary-light border border-primary-light/20 hover:bg-primary hover:text-white hover:shadow-organic hover:-translate-y-0.5"
        }`}
      title={recording ? t('stopRecording') : t('speakQuery')}
    >
      {recording ? (
        <Square className="w-5 h-5 fill-current" />
      ) : (
        <Mic className="w-5 h-5" />
      )}
    </button>
  );
}