/**
 * Sprint 3.9.7 — Smoke-тесты для markdown.ts.
 * Запускается через tsx / ts-node. Не требует jest/vitest.
 *
 * Проверяет:
 * - Базовые элементы (жирный, курсив, код, заголовки)
 * - Callout-блоки (💡 ⚠️ 📌 ✅ ❌)
 * - Code block с языком и copy-кнопкой
 * - Formula ($...$)
 * - md-strong с highlight chip
 * - Списки с акцентными маркерами и ol-пилюлями
 * - Blockquote (слова репетитора)
 * - Streaming: незакрытые конструкции не падают
 * - XSS: HTML из AI-вывода экранируется
 */

import { renderMarkdown } from "./lib/markdown";

let pass = 0;
let fail = 0;

function assertContains(name: string, html: string, needle: string): void {
  if (html.includes(needle)) {
    pass++;
    console.log(`  ✓ ${name}`);
  } else {
    fail++;
    console.log(`  ✗ ${name}`);
    console.log(`    expected to contain: ${needle}`);
    console.log(`    got: ${html.substring(0, 200)}`);
  }
}

function assertNotContains(name: string, html: string, needle: string): void {
  if (!html.includes(needle)) {
    pass++;
    console.log(`  ✓ ${name}`);
  } else {
    fail++;
    console.log(`  ✗ ${name}`);
    console.log(`    expected NOT to contain: ${needle}`);
  }
}

function assertEqual(name: string, actual: string, expected: string): void {
  if (actual === expected) {
    pass++;
    console.log(`  ✓ ${name}`);
  } else {
    fail++;
    console.log(`  ✗ ${name}`);
    console.log(`    expected: ${expected}`);
    console.log(`    actual:   ${actual}`);
  }
}

console.log("\n=== Sprint 3.9.7 — markdown.ts smoke tests ===\n");

// ----- 1. Basic inline -----
console.log("1. Inline tokens");
{
  const h = renderMarkdown("Просто **жирный** и *курсив* и `код`.");
  assertContains("**bold → md-strong**", h, '<span class="md-strong">жирный</span>');
  assertContains("*italic → em*", h, '<em>курсив</em>');
  assertContains("`code → md-code-inline`", h, '<code class="md-code-inline">код</code>');
}

// ----- 2. Headings -----
console.log("\n2. Headings");
{
  const h = renderMarkdown("# H1\n\n## H2\n\n### H3");
  assertContains("h1 → md-h1", h, '<h1 class="md-h1">');
  assertContains("h2 → md-h2", h, '<h2 class="md-h2">');
  assertContains("h3 → md-h3", h, '<h3 class="md-h3">');
}

// ----- 3. Lists -----
console.log("\n3. Lists");
{
  const ul = renderMarkdown("- первый\n- второй\n- третий");
  assertContains("ul → md-ul", ul, '<ul class="md-ul">');
  assertContains("li → md-li", ul, '<li class="md-li">');
  // ❌ Старый list-disc НЕ должен попасть.
  assertNotContains("no list-disc", ul, 'list-disc');

  const ol = renderMarkdown("1. шаг\n2. шаг\n3. шаг");
  assertContains("ol → md-ol", ol, '<ol class="md-ol">');
  assertContains("step 1 pill", ol, '<span class="md-li-pill">1</span>');
  assertContains("step 2 pill", ol, '<span class="md-li-pill">2</span>');
  assertContains("step 3 pill", ol, '<span class="md-li-pill">3</span>');
  assertNotContains("no list-decimal", ol, 'list-decimal');
}

// ----- 4. Callouts -----
console.log("\n4. Callouts (💡 ⚠️ 📌 ✅ ❌)");
{
  const tip = renderMarkdown("💡 Это совет");
  assertContains("tip callout", tip, 'md-callout md-callout-tip');
  assertContains("tip icon", tip, 'md-callout-icon');

  const warn = renderMarkdown("⚠️ Это предупреждение");
  assertContains("warn callout", warn, 'md-callout md-callout-warn');

  const note = renderMarkdown("📌 Это заметка");
  assertContains("note callout", note, 'md-callout md-callout-note');

  const ok = renderMarkdown("✅ Это правильно");
  assertContains("ok callout", ok, 'md-callout md-callout-ok');

  const err = renderMarkdown("❌ Это ошибка");
  assertContains("err callout", err, 'md-callout md-callout-err');
}

// ----- 5. Code block -----
console.log("\n5. Code block with header + copy");
{
  const h = renderMarkdown("```python\ndef hello():\n    print('world')\n```");
  assertContains("codeblock wrapper", h, 'class="md-codeblock"');
  assertContains("codeblock head", h, 'md-codeblock-head');
  assertContains("codeblock lang = python", h, 'md-codeblock-lang">python');
  assertContains("copy button with data-md-copy", h, 'data-md-copy="');
  assertContains("pre element", h, 'md-codeblock-pre');
  assertNotContains("no old slate-900", h, 'bg-slate-900');

  // Без языка — fallback на "text"
  const hNoLang = renderMarkdown("```\nfoo\nbar\n```");
  assertContains("codeblock lang fallback = text", hNoLang, 'md-codeblock-lang">text');

  // Copy содержит сам код
  assertContains("copy contains code", h, "data-md-copy=\"def hello():");
}

// ----- 6. Formula -----
console.log("\n6. Formula ($...$ или =)");
{
  const inline = renderMarkdown("$x^2 + y^2 = z^2$");
  assertContains("inline formula", inline, '<div class="md-formula">x^2 + y^2 = z^2</div>');

  const eqn = renderMarkdown("= mc^2");
  assertContains("equation formula", eqn, '<div class="md-formula">mc^2</div>');
}

// ----- 7. Blockquote -----
console.log("\n7. Blockquote (слова репетитора)");
{
  const h = renderMarkdown("> Это цитата");
  assertContains("md-quote", h, '<blockquote class="md-quote">');
  assertNotContains("no italic-slate-700", h, 'italic text-slate-700');
}

// ----- 8. Paragraph -----
console.log("\n8. Paragraph");
{
  const h = renderMarkdown("Это обычный текст с **термином**.");
  assertContains("paragraph → md-p", h, '<p class="md-p">');
  assertNotContains("no text-slate-900 (light class)", h, 'text-slate-900');
  assertNotContains("no bg-slate-100", h, 'bg-slate-100');
  assertNotContains("no border-slate-200", h, 'border-slate-200');
  assertContains("md-strong inside paragraph", h, '<span class="md-strong">термином</span>');
}

// ----- 9. XSS / escaping -----
console.log("\n9. XSS — HTML должен быть экранирован");
{
  const h = renderMarkdown("Попытка <script>alert('xss')</script> и **жирный**");
  assertNotContains("script tag not raw", h, '<script>');
  assertContains("script text escaped", h, '&lt;script&gt;');
  assertContains("bold still works", h, 'md-strong">жирный</span>');
}

// ----- 10. Streaming safety -----
console.log("\n10. Streaming safety — незакрытые конструкции");
{
  // Незакрытый code block — должен отрендерить что есть
  const h = renderMarkdown("```python\ndef foo(");
  assertContains("unclosed code still rendered", h, 'md-codeblock');
  assertContains("unclosed code has content", h, 'def foo(');

  // Незакрытый **жирный** — должен показать текст без span
  const h2 = renderMarkdown("**незакрытый жирный без close");
  // Контент после ** должен появиться как plain text
  assertContains("unclosed bold shown as text", h2, 'незакрытый');
}

// ----- 11. Multi-line paragraph -----
console.log("\n11. Multi-line paragraph (Sprint 7.1 behavior)");
{
  const h = renderMarkdown("Первая строка\nвторая строка **жирно**");
  assertContains("paragraph", h, '<p class="md-p">');
  assertContains("joined with space", h, 'Первая строка вторая строка');
  assertContains("md-strong inside multi-line", h, '<span class="md-strong">жирно</span>');
}

// ----- 12. Empty input -----
console.log("\n12. Edge cases");
{
  assertEqual("empty string", renderMarkdown(""), "");
  assertEqual("whitespace only", renderMarkdown("   \n\n"), "");
}

// ----- 13. Table (existing feature must still work) -----
console.log("\n13. Table — backwards compat");
{
  const t = renderMarkdown("| a | b |\n|---|---|\n| 1 | 2 |");
  assertContains("table renders", t, '<table class="md-table">');
}

console.log(`\n=== ${pass} passed, ${fail} failed ===\n`);
if (fail > 0) process.exit(1);
