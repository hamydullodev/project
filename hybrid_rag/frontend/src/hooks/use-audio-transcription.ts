"use client";

import * as React from "react";

import { transcribeAudio } from "@/lib/api";

interface UseAudioTranscriptionOptions {
  onResult: (transcript: string) => void;
  onError?: (message: string) => void;
}

interface UseAudioTranscriptionResult {
  supported: boolean;
  listening: boolean;
  transcribing: boolean;
  start: () => void;
  stop: () => void;
}

/**
 * Records a mic clip via `MediaRecorder` and sends it to the backend's local
 * Whisper endpoint (`POST /api/transcribe`) for transcription — replaces the
 * earlier `use-speech-recognition.ts`, which relied on the browser's built-in
 * Web Speech API (Chrome/Edge/Safari only, and itself a cloud call under the
 * hood on most browsers). Recording + server-side transcription works in any
 * browser that supports `MediaRecorder` (i.e. all current major browsers,
 * including Firefox) and keeps transcription fully local to this project's
 * own backend, matching `LLM_PROVIDER=ollama`'s "local-first" stance.
 *
 * `supported` starts false and flips in a mount-only effect, the same
 * SSR-safe-flag pattern `use-speech-recognition.ts` used (and `isMac` in
 * search-box.tsx, `mounted` in theme-toggle.tsx).
 */
export function useAudioTranscription({
  onResult,
  onError,
}: UseAudioTranscriptionOptions): UseAudioTranscriptionResult {
  const [supported, setSupported] = React.useState(false);
  const [listening, setListening] = React.useState(false);
  const [transcribing, setTranscribing] = React.useState(false);
  const recorderRef = React.useRef<MediaRecorder | null>(null);
  const chunksRef = React.useRef<BlobPart[]>([]);
  const onResultRef = React.useRef(onResult);
  const onErrorRef = React.useRef(onError);

  React.useEffect(() => {
    onResultRef.current = onResult;
    onErrorRef.current = onError;
  }, [onResult, onError]);

  React.useEffect(() => {
    const hasSupport =
      typeof navigator !== "undefined" &&
      Boolean(navigator.mediaDevices?.getUserMedia) &&
      typeof window.MediaRecorder !== "undefined";
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSupported(hasSupport);
  }, []);

  const start = React.useCallback(() => {
    if (listening || transcribing) return;

    navigator.mediaDevices
      .getUserMedia({ audio: true })
      .then((stream) => {
        const recorder = new MediaRecorder(stream);
        chunksRef.current = [];

        recorder.ondataavailable = (event) => {
          if (event.data.size > 0) chunksRef.current.push(event.data);
        };

        recorder.onstop = () => {
          stream.getTracks().forEach((track) => track.stop());
          setListening(false);

          const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
          chunksRef.current = [];
          if (blob.size === 0) return;

          setTranscribing(true);
          transcribeAudio(blob)
            .then((transcript) => {
              if (transcript) onResultRef.current(transcript);
            })
            .catch((error: unknown) => {
              onErrorRef.current?.(
                error instanceof Error ? error.message : "Audio matnga o'girilmadi.",
              );
            })
            .finally(() => setTranscribing(false));
        };

        recorderRef.current = recorder;
        recorder.start();
        setListening(true);
      })
      .catch(() => {
        onErrorRef.current?.("Mikrofonga ruxsat berilmadi.");
      });
  }, [listening, transcribing]);

  const stop = React.useCallback(() => {
    recorderRef.current?.stop();
    recorderRef.current = null;
  }, []);

  React.useEffect(() => {
    return () => {
      recorderRef.current?.stop();
    };
  }, []);

  return { supported, listening, transcribing, start, stop };
}
