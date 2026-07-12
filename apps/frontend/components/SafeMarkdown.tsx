"use client";

import { renderMarkdown } from "@/lib/markdown";

interface SafeMarkdownProps {
  text: string;
  /** Если true — рендерит в typewriter-стиле, когда text растёт по чанкам. */
  streaming?: boolean;
  className?: string;
}

/**
 * Безопасный рендер Markdown для AI-ответов.
 *
 * Sprint 7.1: заменяет `whitespace-pre-wrap` текст с raw-разметкой
 * на безопасный HTML-рендер:
 *   - **жирный**, *курсив*, `код`
 *   - # заголовки h1-h3, > blockquote, --- hr
 *   - - список, 1. нумерованный, ```code block```
 *   - авто-экранирование HTML для всего, что не входит в подмножество
 *
 * Использует dangerouslySetInnerHTML после того, как наш парсер сделал
 * весь escape — никаких external library с известными XSS.
 */
export default function SafeMarkdown({
  text,
  streaming = false,
  className = "",
}: SafeMarkdownProps) {
  // streaming: добавляем курсор в конце во время печатания
  const html = renderMarkdown(text || "");
  const cursor = streaming ? '<span class="animate-pulse">▍</span>' : "";
  return (
    <div
      className={className}
      dangerouslySetInnerHTML={{ __html: html + cursor }}
    />
  );
}
