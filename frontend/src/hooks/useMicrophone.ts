"use client";

import { useRef, useState, useCallback } from "react";

/**
 * Captures microphone audio as PCM data for sending to the backend.
 * Records 16kHz mono PCM (matching Gemini Live API's expected input).
 */
export function useMicrophone() {
  const [isRecording, setIsRecording] = useState(false);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const chunksRef = useRef<Float32Array[]>([]);

  /**
   * Start recording from the microphone.
   */
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      mediaStreamRef.current = stream;
      const audioCtx = new AudioContext({ sampleRate: 16000 });
      audioCtxRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);
      const processor = audioCtx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      chunksRef.current = [];

      processor.onaudioprocess = (e) => {
        const data = e.inputBuffer.getChannelData(0);
        chunksRef.current.push(new Float32Array(data));
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      setIsRecording(true);
    } catch (err) {
      console.error("Microphone access denied:", err);
    }
  }, []);

  /**
   * Stop recording and return the captured audio as PCM bytes (16-bit signed LE).
   */
  const stopRecording = useCallback((): ArrayBuffer => {
    // Stop media stream
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }

    // Disconnect processor
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    // Close audio context
    if (audioCtxRef.current) {
      audioCtxRef.current.close();
      audioCtxRef.current = null;
    }

    setIsRecording(false);

    // Merge chunks and convert to 16-bit PCM
    const totalLength = chunksRef.current.reduce((acc, c) => acc + c.length, 0);
    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of chunksRef.current) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }
    chunksRef.current = [];

    // Convert Float32 to Int16
    const int16 = new Int16Array(merged.length);
    for (let i = 0; i < merged.length; i++) {
      const s = Math.max(-1, Math.min(1, merged[i]));
      int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }

    return int16.buffer;
  }, []);

  return { isRecording, startRecording, stopRecording };
}
