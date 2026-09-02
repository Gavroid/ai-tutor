/**
 * Sprint 3.9.7 — Безопасный Markdown → HTML парсер для AI-ответов.
 *
 * Допустимое подмножество:
 *   - **жирный**, *курсив*, `код`
 *   - # заголовки (h1-h3)
 *   - - список, 1. нумерованный
 *   - > blockquote («слова репетитора»)
 *   - --- hr
 *   - ```code block``` (опционально с языком после ```)
 *   - 💡/⚠️/📌/✅/❌ в начале строки → callout-блок
 *   - $...$ или строки начинающиеся с "=" → формула
 *
 * Безопасность:
 *   - HTML экранируется через ESCAPE_HTML.
 *   - Никаких внешних markdown-библиотек (только собственный парсер).
 *   - Streaming-safe: незакрытые конструкции на промежуточных чанках
 *     парсятся в текущем состоянии без поломок.
 *   - Только тёмная тема — все цвета через md-* классы (CSS-переменные).
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

/**
 * Sprint 3.9.7: **жирный** → highlight chip с фоном accent + radius 6px.
 * Также поддерживает `код` с правильным контрастом в dark mode.
 */
function renderInline(text: string): string {
  const tokens = parseInline(text);
  return tokens
    .map((tok) => {
      switch (tok.type) {
        case "bold":
          return `<span class="md-strong">${ESCAPE_HTML(tok.text)}</span>`;
        case "italic":
          return `<em>${ESCAPE_HTML(tok.text)}</em>`;
        case "code":
          return `<code class="md-code-inline">${ESCAPE_HTML(tok.text)}</code>`;
        default:
          return ESCAPE_HTML(tok.text);
      }
    })
    .join("");
}

function isTableRow(line: string): boolean {
  const trimmed = line.trim();
  return trimmed.startsWith("|") && trimmed.endsWith("|") && trimmed.split("|").length >= 4;
}

function isTableSeparator(line: string): boolean {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
}

function splitTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function renderTable(rows: string[][]): string {
  if (rows.length === 0) return "";
  const [head, ...body] = rows;
  return `<div class="md-table-wrap"><table class="md-table"><thead><tr>${head
    .map((cell) => `<th>${renderInline(cell)}</th>`)
    .join("")}</tr></thead><tbody>${body
    .map((row) => `<tr>${row.map((cell) => `<td>${renderInline(cell)}</td>`).join("")}</tr>`)
    .join("")}</tbody></table></div>`;
}

/**
 * Sprint 3.9.7: callout для строк начинающихся с 💡 ⚠️ 📌 ✅ ❌.
 * Семантический класс для каждого иконки.
 *
 * Используем флаг `u` чтобы корректно работать с surrogate pairs
 * (большинство emoji — 2 UTF-16 code units). Также явно перечисляем
 * варианты с variation selector (\uFE0F) — без этого ⚠️ не матчится.
 */
const CALLOUT_ICONS: Record<string, string> = {
  "💡": "tip",
  "⚠": "warn", // ⚠️
  "⚠️": "warn",
  "📌": "note",
  "✅": "ok",
  "❌": "err",
};

const CALLOUT_RE = /^([💡⚠️📌✅❌])\s*(.+)$/u;

function detectCallout(line: string): { kind: string; text: string } | null {
  const trimmed = line.trim();
  const m = CALLOUT_RE.exec(trimmed);
  if (!m) return null;
  const [, icon, text] = m;
  const kind = CALLOUT_ICONS[icon] ?? CALLOUT_ICONS[icon.charAt(0)] ?? "note";
  return { kind, text };
}

/**
 * Sprint 3.9.7: формула. Распознаём $...$ (inline) или строки начинающиеся с "=".
 * Не пытаемся рендерить LaTeX (no KaTeX) — только центрированный .md-formula блок.
 */
function detectFormula(line: string): string | null {
  const trimmed = line.trim();
  // Inline $...$
  const m = /^\$([^$]+)\$$/.exec(trimmed);
  if (m) return m[1];
  // Строка-формула (начинается с = или содержит много операторов).
  if (/^=\s*[^\s]/.test(trimmed)) return trimmed.substring(1).trim();
  return null;
}

/** Парсит Markdown → HTML. Безопасен для dangerouslySetInnerHTML. */
export function renderMarkdown(md: string): string {
  if (!md) return "";
  const lines = md.split(/\r?\n/);
  const out: string[] = [];
  let i = 0;
  let inCodeBlock = false;
  let codeLang = "";
  let codeBuf: string[] = [];

  while (i < lines.length) {
    const line = lines[i];

    // ----- Code block -----
    if (inCodeBlock) {
      if (line.trim().startsWith("```")) {
        // Sprint 3.9.7: code block с header (язык) и кнопкой copy.
        // data-md-copy — атрибут для React island который вешает handler.
        const langLabel = codeLang || "text";
        out.push(
          `<div class="md-codeblock" data-md-copy-wrapper>` +
            `<div class="md-codeblock-head">` +
              `<span class="md-codeblock-lang">${ESCAPE_HTML(langLabel)}</span>` +
              `<button type="button" class="md-codeblock-copy" data-md-copy="${ESCAPE_HTML(codeBuf.join("\n"))}" aria-label="Скопировать код">` +
                `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>` +
                `<span>Скопировать</span>` +
              `</button>` +
            `</div>` +
            `<pre class="md-codeblock-pre"><code class="md-codeblock-code">${ESCAPE_HTML(
              codeBuf.join("\n")
            )}</code></pre>` +
          `</div>`
        );
        codeBuf = [];
        codeLang = "";
        inCodeBlock = false;
        i++;
        continue;
      }
      codeBuf.push(line);
      i++;
      continue;
    }
    if (line.trim().startsWith("```")) {
      // Sprint 3.9.7: ```python → lang="python"
      const langMatch = /^```\s*([a-zA-Z0-9_+-]*)/.exec(line.trim());
      codeLang = langMatch ? langMatch[1] : "";
      inCodeBlock = true;
      i++;
      continue;
    }

    // ----- Table -----
    if (
      isTableRow(line) &&
      i + 1 < lines.length &&
      (isTableSeparator(lines[i + 1]) || isTableRow(lines[i + 1]))
    ) {
      const rows: string[][] = [splitTableRow(line)];
      i++;
      if (i < lines.length && isTableSeparator(lines[i])) i++;
      while (i < lines.length && isTableRow(lines[i])) {
        rows.push(splitTableRow(lines[i]));
        i++;
      }
      out.push(renderTable(rows));
      continue;
    }

    // ----- Callout -----
    const callout = detectCallout(line);
    if (callout) {
      out.push(
        `<aside class="md-callout md-callout-${callout.kind}" role="note">` +
          `<span class="md-callout-icon" aria-hidden="true">${line.trim().charAt(0)}</span>` +
          `<div class="md-callout-body">${renderInline(callout.text)}</div>` +
        `</aside>`
      );
      i++;
      continue;
    }

    // ----- Formula -----
    const formula = detectFormula(line);
    if (formula) {
      out.push(`<div class="md-formula">${ESCAPE_HTML(formula)}</div>`);
      i++;
      continue;
    }

    // ----- Heading -----
    const hMatch = /^(#{1,3})\s+(.+)$/.exec(line);
    if (hMatch) {
      const level = hMatch[1].length;
      const cls = `md-h${level}`;
      out.push(`<h${level} class="${cls}">${renderInline(hMatch[2])}</h${level}>`);
      i++;
      continue;
    }

    // ----- Blockquote (слова репетитора) -----
    if (line.startsWith("> ")) {
      out.push(
        `<blockquote class="md-quote">${renderInline(line.substring(2))}</blockquote>`
      );
      i++;
      continue;
    }

    // ----- Horizontal rule -----
    if (/^---+\s*$/.test(line)) {
      out.push('<hr class="md-hr" />');
      i++;
      continue;
    }

    // ----- Unordered list (с акцентными маркерами) -----
    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ""));
        i++;
      }
      out.push(
        `<ul class="md-ul">${items
          .map((it) => `<li class="md-li">${renderInline(it)}</li>`)
          .join("")}</ul>`
      );
      continue;
    }

    // ----- Ordered list (нумерованные пилюли) -----
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ""));
        i++;
      }
      out.push(
        `<ol class="md-ol">${items
          .map((it, idx) => `<li class="md-li md-li-step"><span class="md-li-pill">${idx + 1}</span><span class="md-li-text">${renderInline(it)}</span></li>`)
          .join("")}</ol>`
      );
      continue;
    }

    // ----- Empty line -----
    if (!line.trim()) {
      i++;
      continue;
    }

    // ----- Paragraph (multi-line) -----
    const paragraphLines: string[] = [line];
    i++;
    while (
      i < lines.length &&
      lines[i].trim() &&
      !isTableRow(lines[i]) &&
      !/^#{1,3}\s/.test(lines[i]) &&
      !/^\s*[-*]\s/.test(lines[i]) &&
      !/^\s*\d+\.\s/.test(lines[i]) &&
      !lines[i].startsWith("> ") &&
      !lines[i].trim().startsWith("```") &&
      !CALLOUT_RE.test(lines[i].trim()) &&
      !detectFormula(lines[i])
    ) {
      paragraphLines.push(lines[i]);
      i++;
    }
    out.push(`<p class="md-p">${renderInline(paragraphLines.join(" "))}</p>`);
  }

  // Незакрытый code block в конце стрима — рендерим то что есть.
  if (inCodeBlock && codeBuf.length > 0) {
    const langLabel = codeLang || "text";
    out.push(
      `<div class="md-codeblock" data-md-copy-wrapper>` +
        `<div class="md-codeblock-head">` +
          `<span class="md-codeblock-lang">${ESCAPE_HTML(langLabel)}</span>` +
          `<button type="button" class="md-codeblock-copy" data-md-copy="${ESCAPE_HTML(codeBuf.join("\n"))}" aria-label="Скопировать код">` +
            `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>` +
            `<span>Скопировать</span>` +
          `</button>` +
        `</div>` +
        `<pre class="md-codeblock-pre"><code class="md-codeblock-code">${ESCAPE_HTML(
          codeBuf.join("\n")
        )}</code></pre>` +
      `</div>`
    );
  }

  return out.join("");
}
