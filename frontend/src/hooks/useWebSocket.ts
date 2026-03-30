"use client";

import { useRef, useCallback, useEffect, useState } from "react";
import { WS_URL } from "@/lib/constants";
import type { WSClientMessage, WSServerMessage } from "@/lib/types";

interface UseWebSocketOptions {
  sessionId: string | null;
  onMessage: (msg: WSServerMessage) => void;
  onDisconnect?: () => void;
}

export function useWebSocket({ sessionId, onMessage, onDisconnect }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;
  const onDisconnectRef = useRef(onDisconnect);
  onDisconnectRef.current = onDisconnect;

  // Connect with auto-reconnection
  useEffect(() => {
    if (!sessionId) return;

    let reconnectTimer: ReturnType<typeof setTimeout>;
    let reconnectAttempts = 0;
    let isMounted = true;

    function connect() {
      const url = `${WS_URL}/api/ws/${sessionId}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttempts = 0;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WSServerMessage;
          onMessageRef.current(msg);
        } catch (e) {
          console.error("Failed to parse WS message:", e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;
        onDisconnectRef.current?.();
        // Auto-reconnect with exponential backoff (max 5 attempts)
        if (isMounted && reconnectAttempts < 5) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 10000);
          reconnectAttempts++;
          reconnectTimer = setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {
        // onclose will fire after this — reconnection handled there
      };
    }

    connect();

    return () => {
      isMounted = false;
      clearTimeout(reconnectTimer);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [sessionId]);

  // Send message
  const send = useCallback((msg: WSClientMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    } else {
      console.warn("WebSocket not connected, cannot send:", msg);
    }
  }, []);

  // Convenience methods
  const sendInterrupt = useCallback(
    (question: string, currentTurnIndex: number) => {
      send({ type: "interrupt", question, current_turn_index: currentTurnIndex, use_live: true });
    },
    [send]
  );

  const sendVoiceInterrupt = useCallback(
    (audioBase64: string, currentTurnIndex: number, sampleRate = 16000) => {
      send({ type: "voice_interrupt", audio: audioBase64, current_turn_index: currentTurnIndex, sample_rate: sampleRate });
    },
    [send]
  );

  const sendSimplify = useCallback(
    (currentTurnIndex: number) => {
      send({ type: "simplify", current_turn_index: currentTurnIndex, use_live: true });
    },
    [send]
  );

  const sendGoDeeper = useCallback(
    (currentTurnIndex: number) => {
      send({ type: "go_deeper", current_turn_index: currentTurnIndex, use_live: true });
    },
    [send]
  );

  const sendQuizStart = useCallback(
    (section?: string, currentTurnIndex?: number) => {
      send({ type: "quiz_start", section, current_turn_index: currentTurnIndex });
    },
    [send]
  );

  const sendQuizAnswer = useCallback(
    (questionId: string, answer: string) => {
      send({ type: "quiz_answer", question_id: questionId, answer });
    },
    [send]
  );

  return {
    isConnected,
    send,
    sendInterrupt,
    sendVoiceInterrupt,
    sendSimplify,
    sendGoDeeper,
    sendQuizStart,
    sendQuizAnswer,
  };
}
