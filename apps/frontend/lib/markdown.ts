/**
 * Минимальный безопасный Markdown → HTML парсер для AI-ответов.
 *
 * Sprint 7.1: фронт парсит markdown в реальном времени во время WS-стрима,
 * чтобы избежать "||жирный||" в чате.
 *
 * Безопасность:
 *   - НЕ используем innerHTML для пользовательского ввода.
 *   - HTML-теги из AI-вывода экранируются.
 *   - Разрешено только наше подмножество markdown:
 *     **жирный**, *курсив*, `код`, # заголовки (h1-h3), - список, 1. нумерованный,
 *     > blockquote, --- hr, ```code block```, переводы строк.
 *   - Запрещены: [ссылки](), ![картинки](), html, tables (overkill для стрима).
 */

const ESCAPE_HTML = (s: string): string =>
  s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

interface InlineToken {
  type: "bold" | "italic" | "code" | "text";
  text: string;
}

function parseInline(text: string): InlineToken[] {
  const tokens: InlineToken[] = [];
  let i = 0;
  let buf = "";
  const flushBuf = (): void => {
    if (buf) {
      tokens.push({ type: "text", text: buf });
      buf = "";
    }
  };
  while (i < text.length) {
    const ch = text[i];
    // **жирный**
    if (ch === "*" && text[i + 1] === "*") {
      const end = text.indexOf("**", i + 2);
      if (end !== -1) {
        flushBuf();
        tokens.push({ type: "bold", text: text.substring(i + 2, end) });
        i = end + 2;
        continue;
      }
    }
    // *курсив*
    if (ch === "*" && text[i + 1] !== "*" && text[i + 1] !== " ") {
      const end = findUnescapedStar(text, i + 1);
      if (end !== -1) {
        flushBuf();
        tokens.push({ type: "italic", text: text.substring(i + 1, end) });
        i = end + 1;
        continue;
      }
    }
    // `код`
    if (ch === "`") {
      const end = text.indexOf("`", i + 1);
      if (end !== -1) {
        flushBuf();
        tokens.push({ type: "code", text: text.substring(i + 1, end) });
        i = end + 1;
        continue;
      }
    }
    buf += ch;
    i++;
  }
  flushBuf();
  return tokens;
}

function findUnescapedStar(text: string, from: number): number {
  for (let j = from; j < text.length; j++) {
    if (text[j] === "*" && text[j + 1] !== "*" && text[j - 1] !== "*") return j;
  }
  return -1;
}

function renderInline(text: string): string {
  const tokens = parseInline(text);
  return tokens
    .map((tok) => {
      switch (tok.type) {
        case "bold":
          return `<strong>${ESCAPE_HTML(tok.text)}</strong>`;
        case "italic":
          return `<em>${ESCAPE_HTML(tok.text)}</em>`;
        case "code":
          return `<code class="rounded bg-slate-100 px-1 py-0.5 text-sm">${ESCAPE_HTML(
            tok.text
          )}</code>`;
        default:
          return ESCAPE_HTML(tok.text);
      }
    })
    .join("");
}

/** Парсит Markdown → HTML. Безопасен для dangerouslySetInnerHTML. */
export function renderMarkdown(md: string): string {
  if (!md) return "";
  const lines = md.split(/\r?\n/);
  const out: string[] = [];
  let i = 0;
  let inCodeBlock = false;
  let codeBuf: string[] = [];
  while (i < lines.length) {
    const line = lines[i];
    if (inCodeBlock) {
      if (line.trim().startsWith("```")) {
        out.push(
          `<pre class="overflow-x-auto rounded-lg bg-slate-900 p-3 text-sm text-slate-100"><code>${ESCAPE_HTML(
            codeBuf.join("\n")
          )}</code></pre>`
        );
        codeBuf = [];
        inCodeBlock = false;
        i++;
        continue;
      }
      codeBuf.push(line);
      i++;
      continue;
    }
    if (line.trim().startsWith("```")) {
      inCodeBlock = true;
      i++;
      continue;
    }
    // Заголовки
    const hMatch = /^(#{1,3})\s+(.+)$/.exec(line);
    if (hMatch) {
      const level = hMatch[1].length;
      out.push(`<h${level} class="mt-3 mb-1 font-semibold text-slate-900">${renderInline(
        hMatch[2]
      )}</h${level}>`);
      i++;
      continue;
    }
    // Цитата
    if (line.startsWith("> ")) {
      out.push(
        `<blockquote class="my-2 border-l-4 border-slate-300 pl-3 italic text-slate-700">${renderInline(
          line.substring(2)
        )}</blockquote>`
      );
      i++;
      continue;
    }
    // Горизонтальная линия
    if (/^---+\s*$/.test(line)) {
      out.push('<hr class="my-3 border-slate-200" />');
      i++;
      continue;
    }
    // Ненумерованный список
    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ""));
        i++;
      }
      out.push(
        `<ul class="my-2 ml-5 list-disc text-slate-900">${items
          .map((it) => `<li>${renderInline(it)}</li>`)
          .join("")}</ul>`
      );
      continue;
    }
    // Нумерованный список
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ""));
        i++;
      }
      out.push(
        `<ol class="my-2 ml-5 list-decimal text-slate-900">${items
          .map((it) => `<li>${renderInline(it)}</li>`)
          .join("")}</ol>`
      );
      continue;
    }
    // Пустая строка → конец абзаца
    if (!line.trim()) {
      i++;
      continue;
    }
    // Обычный текст (может быть несколько подряд идущих строк)
    const paragraphLines: string[] = [line];
    i++;
    while (i < lines.length && lines[i].trim() && !/^#{1,3}\s/.test(lines[i]) && !/^\s*[-*]\s/.test(lines[i]) && !/^\s*\d+\.\s/.test(lines[i]) && !lines[i].startsWith("> ") && !lines[i].trim().startsWith("```")) {
      paragraphLines.push(lines[i]);
      i++;
    }
    out.push(
      `<p class="my-2 leading-relaxed text-slate-900">${renderInline(
        paragraphLines.join(" ")
      )}</p>`
    );
  }
  if (inCodeBlock && codeBuf.length > 0) {
    out.push(
      `<pre class="overflow-x-auto rounded-lg bg-slate-900 p-3 text-sm text-slate-100"><code>${ESCAPE_HTML(
        codeBuf.join("\n")
      )}</code></pre>`
    );
  }
  return out.join("");
}
