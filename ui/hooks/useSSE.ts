"use client";
import { useEffect, useRef, useCallback } from "react";
import type { SSEEvent, SSEEventType } from "@/types";

type Handler = (event: SSEEvent) => void;

export function useSSE(url: string | null, onEvent: Handler) {
  const esRef = useRef<EventSource | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    if (!url) return;
    if (esRef.current) {
      esRef.current.close();
    }
    const es = new EventSource(url);
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const parsed = JSON.parse(e.data) as SSEEvent;
        onEventRef.current(parsed);
      } catch {
        // ignore malformed events
      }
    };

    es.onerror = () => {
      es.close();
      esRef.current = null;
    };
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      esRef.current?.close();
      esRef.current = null;
    };
  }, [connect]);

  const cancel = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
  }, []);

  return { connect, cancel };
}
