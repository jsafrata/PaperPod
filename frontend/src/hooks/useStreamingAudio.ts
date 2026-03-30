"use client";

import { useRef, useCallback } from "react";

/**
 * Streams PCM audio chunks into a Web Audio API buffer for real-time playback.
 * Handles Gemini Live API's raw PCM output (24kHz, 16-bit, mono).
 */
export function useStreamingAudio() {
  const audioCtxRef = useRef<AudioContext | null>(null);
  const nextStartTimeRef = useRef(0);
  const isPlayingRef = useRef(false);

  const getAudioContext = useCallback(() => {
    if (!audioCtxRef.current || audioCtxRef.current.state === "closed") {
      audioCtxRef.current = new AudioContext({ sampleRate: 24000 });
    }
    if (audioCtxRef.current.state === "suspended") {
      audioCtxRef.current.resume();
    }
    return audioCtxRef.current;
  }, []);

  /**
   * Queue a PCM audio chunk for playback.
   * @param pcmData - Raw PCM bytes (16-bit signed LE, mono, 24kHz)
   */
  const playChunk = useCallback(
    (pcmData: ArrayBuffer) => {
      const ctx = getAudioContext();
      const sampleRate = 24000;

      // Convert 16-bit PCM to Float32
      const int16 = new Int16Array(pcmData);
      const float32 = new Float32Array(int16.length);
      for (let i = 0; i < int16.length; i++) {
        float32[i] = int16[i] / 32768;
      }

      // Create audio buffer
      const buffer = ctx.createBuffer(1, float32.length, sampleRate);
      buffer.getChannelData(0).set(float32);

      // Schedule playback
      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(ctx.destination);

      const now = ctx.currentTime;
      const startTime = Math.max(now, nextStartTimeRef.current);
      source.start(startTime);
      nextStartTimeRef.current = startTime + buffer.duration;

      isPlayingRef.current = true;
      source.onended = () => {
        if (nextStartTimeRef.current <= ctx.currentTime + 0.05) {
          isPlayingRef.current = false;
        }
      };
    },
    [getAudioContext]
  );

  /**
   * Reset the playback queue (e.g. when interrupted).
   */
  const reset = useCallback(() => {
    nextStartTimeRef.current = 0;
    isPlayingRef.current = false;
    // Don't close the AudioContext — keep it alive for reuse
  }, []);

  /**
   * Stop all currently playing/queued streaming audio.
   */
  const stop = useCallback(() => {
    // Close the context to immediately stop all playing/queued audio
    if (audioCtxRef.current && audioCtxRef.current.state !== "closed") {
      audioCtxRef.current.close();
      audioCtxRef.current = null;
    }
    nextStartTimeRef.current = 0;
    isPlayingRef.current = false;
  }, []);

  /**
   * Ensure the AudioContext is created and resumed during a user gesture.
   */
  const ensureReady = useCallback(() => {
    getAudioContext();
  }, [getAudioContext]);

  const getIsPlaying = useCallback(() => isPlayingRef.current, []);

  return { playChunk, reset, stop, ensureReady, getIsPlaying };
}
