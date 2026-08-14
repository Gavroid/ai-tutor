const pptxgen = require('pptxgenjs');
const fs = require('fs');
const path = require('path');

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'Hermes Agent';
pptx.company = 'AI-Tutor';
pptx.subject = 'AI-Tutor stakeholder presentation';
pptx.title = 'AI-Tutor MVP: статус и дорожная карта';
pptx.lang = 'ru-RU';
pptx.theme = {
  headFontFace: 'Calibri',
  bodyFontFace: 'Calibri',
  lang: 'ru-RU',
};
pptx.defineLayout({ name: 'CUSTOM_WIDE', width: 13.333, height: 7.5 });
pptx.layout = 'CUSTOM_WIDE';
pptx.margin = 0;
pptx.defineSlideMaster({
  title: 'BLANK',
  background: { color: '0B1020' },
  objects: [],
  slideNumber: { x: 12.2, y: 7.08, color: '6B7280' },
});

const C = {
  bg: '0B1020',
  bg2: '101A33',
  panel: '17213C',
  panel2: '111827',
  ink: 'F8FAFC',
  muted: 'A7B0C5',
  blue: '38BDF8',
  violet: 'A78BFA',
  green: '34D399',
  amber: 'FBBF24',
  rose: 'FB7185',
  white: 'FFFFFF',
  line: '334155',
};

function slide(bg = C.bg) {
  const s = pptx.addSlide('BLANK');
  s.background = { color: bg };
  s.addShape(pptx.ShapeType.arc, { x: -1.0, y: -1.1, w: 4.0, h: 4.0, line: { color: bg, transparency: 100 }, fill: { color: C.blue, transparency: 82 } });
  s.addShape(pptx.ShapeType.arc, { x: 10.8, y: 4.8, w: 3.4, h: 3.4, line: { color: bg, transparency: 100 }, fill: { color: C.violet, transparency: 84 } });
  return s;
}

function title(s, kicker, heading, sub) {
  s.addText(kicker.toUpperCase(), { x: 0.55, y: 0.42, w: 6.2, h: 0.28, fontFace: 'Calibri', fontSize: 9, bold: true, color: C.blue, charSpacing: 1.2, margin: 0 });
  s.addText(heading, { x: 0.55, y: 0.78, w: 11.8, h: 0.78, fontFace: 'Calibri', fontSize: 25, bold: true, color: C.ink, breakLine: false, margin: 0, fit: 'shrink' });
  if (sub) s.addText(sub, { x: 0.57, y: 1.55, w: 10.9, h: 0.36, fontFace: 'Calibri', fontSize: 11.5, color: C.muted, margin: 0, fit: 'shrink' });
}

function pill(s, text, x, y, color = C.blue, w = 1.6) {
  s.addShape(pptx.ShapeType.roundRect, { x, y, w, h: 0.38, rectRadius: 0.08, line: { color, transparency: 20, width: 1 }, fill: { color, transparency: 84 } });
  s.addText(text, { x: x + 0.08, y: y + 0.105, w: w - 0.16, h: 0.14, fontSize: 8, bold: true, color, align: 'center', margin: 0, fit: 'shrink' });
}

function card(s, x, y, w, h, opts = {}) {
  s.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.12,
    line: { color: opts.line || C.line, transparency: 20, width: 1 },
    fill: { color: opts.fill || C.panel, transparency: opts.transparency ?? 0 },
    shadow: { type: 'outer', color: '000000', opacity: 0.15, blur: 1, angle: 45, distance: 1 },
  });
}

function statCard(s, x, y, w, h, num, label, color = C.green) {
  card(s, x, y, w, h, { fill: C.panel });
  s.addText(num, { x: x + 0.2, y: y + 0.18, w: w - 0.4, h: 0.45, fontSize: 24, bold: true, color, align: 'center', margin: 0, fit: 'shrink' });
  s.addText(label, { x: x + 0.18, y: y + 0.76, w: w - 0.36, h: 0.42, fontSize: 9.5, color: C.muted, align: 'center', margin: 0, fit: 'shrink' });
}

function bulletCard(s, x, y, w, h, head, bullets, color = C.blue) {
  card(s, x, y, w, h, { fill: C.panel });
  s.addShape(pptx.ShapeType.ellipse, { x: x + 0.2, y: y + 0.22, w: 0.28, h: 0.28, line: { color, transparency: 10 }, fill: { color, transparency: 10 } });
  s.addText(head, { x: x + 0.58, y: y + 0.18, w: w - 0.8, h: 0.28, fontSize: 12, bold: true, color: C.ink, margin: 0, fit: 'shrink' });
  const runs = [];
  bullets.forEach((b, idx) => runs.push({ text: b, options: { bullet: { indent: 10 }, breakLine: idx < bullets.length - 1 } }));
  s.addText(runs, { x: x + 0.34, y: y + 0.66, w: w - 0.58, h: h - 0.82, fontSize: 9.5, color: C.muted, breakLine: false, fit: 'shrink', paraSpaceAfter: 4, margin: 0.03 });
}

function section(s, part, titleText, subtitle, color = C.blue) {
  s.background = { color: C.bg };
  s.addShape(pptx.ShapeType.roundRect, { x: 0.72, y: 0.82, w: 1.05, h: 1.05, rectRadius: 0.18, line: { color, transparency: 5 }, fill: { color, transparency: 8 } });
  s.addText(part, { x: 0.72, y: 1.08, w: 1.05, h: 0.42, fontSize: 20, bold: true, color: C.white, align: 'center', margin: 0 });
  s.addText(titleText, { x: 2.05, y: 0.92, w: 10.2, h: 0.62, fontSize: 28, bold: true, color: C.ink, margin: 0, fit: 'shrink' });
  s.addText(subtitle, { x: 2.08, y: 1.68, w: 9.5, h: 0.45, fontSize: 13, color: C.muted, margin: 0, fit: 'shrink' });
}

function timeline(s, items) {
  const startX = 0.82, y = 3.05, step = 2.45;
  items.forEach((it, i) => {
    const x = startX + i * step;
    s.addShape(pptx.ShapeType.ellipse, { x, y, w: 0.54, h: 0.54, line: { color: it.color, width: 1 }, fill: { color: it.color, transparency: 5 } });
    s.addText(String(i + 1), { x, y: y + 0.13, w: 0.54, h: 0.18, fontSize: 11, bold: true, color: C.bg, align: 'center', margin: 0 });
    if (i < items.length - 1) s.addShape(pptx.ShapeType.chevron, { x: x + 0.72, y: y + 0.13, w: 1.38, h: 0.28, line: { color: C.line, transparency: 100 }, fill: { color: C.line, transparency: 35 } });
    s.addText(it.title, { x: x - 0.24, y: y + 0.78, w: 1.6, h: 0.36, fontSize: 10.5, bold: true, color: C.ink, align: 'center', margin: 0, fit: 'shrink' });
    s.addText(it.sub, { x: x - 0.34, y: y + 1.22, w: 1.8, h: 0.55, fontSize: 8.5, color: C.muted, align: 'center', margin: 0, fit: 'shrink' });
  });
}

// 1 Title
let s = slide();
s.addText('AI-TUTOR MVP', { x: 0.7, y: 0.55, w: 3.2, h: 0.28, fontSize: 10, bold: true, color: C.blue, charSpacing: 1.5, margin: 0 });
s.addText('AI-репетитор: статус проекта и дорожная карта', { x: 0.68, y: 1.05, w: 8.7, h: 1.15, fontSize: 33, bold: true, color: C.ink, margin: 0, fit: 'shrink' });
s.addText('Презентация для стейкхолдера простым языком: что уже готово, куда идём дальше и чем каждая фаза отличается от предыдущей.', { x: 0.72, y: 2.32, w: 7.1, h: 0.7, fontSize: 14, color: C.muted, margin: 0, fit: 'shrink' });
statCard(s, 8.25, 0.82, 1.5, 1.2, '42/42', 'тем математики готовы', C.green);
statCard(s, 9.95, 0.82, 1.5, 1.2, '4', 'роли в продукте', C.blue);
statCard(s, 11.65, 0.82, 1.15, 1.2, '24/7', 'контроль и backup', C.amber);
timeline(s, [
  { title: 'MVP готов', sub: 'ученик, родитель, учитель, админ', color: C.green },
  { title: '1 месяц', sub: 'качество пилота', color: C.blue },
  { title: '3 месяца', sub: 'масштабирование', color: C.violet },
  { title: 'Фазы', sub: 'от прототипа к платформе', color: C.amber },
  { title: 'Фишки', sub: 'что продаёт идею', color: C.rose },
]);
s.addNotes('Открыть презентацию с простого тезиса: это уже рабочий MVP, но сейчас главный фокус — качество пилота и масштабирование.');

// 2 Agenda / five parts
s = slide();
title(s, 'Структура', '5 частей презентации', 'Разделение совпадает с запросом: от фактов текущего проекта к плану развития и отличиям фаз.');
const agenda = [
  ['1', 'Что сделано', 'Рабочий MVP, математика 42/42, роли, мониторинг, backup'],
  ['2', 'Ближайший месяц', 'Пилот, качество контента, реальный ученик, понятная отчётность'],
  ['3', '3 месяца', 'Больше предметов, адаптивность, аналитика, управление качеством'],
  ['4', 'Отличия фаз', 'Как проект меняется от прототипа к образовательной платформе'],
  ['5', 'Топ-5 фишек', 'Что будет впечатлять пользователей и стейкхолдеров на каждом этапе'],
];
agenda.forEach((a, i) => {
  const x = 0.8 + (i % 3) * 4.05;
  const y = 2.05 + Math.floor(i / 3) * 1.75;
  card(s, x, y, i < 3 ? 3.65 : 5.8, 1.32, { fill: C.panel });
  s.addShape(pptx.ShapeType.ellipse, { x: x + 0.22, y: y + 0.25, w: 0.55, h: 0.55, line: { color: C.blue }, fill: { color: C.blue, transparency: 8 } });
  s.addText(a[0], { x: x + 0.22, y: y + 0.38, w: 0.55, h: 0.18, fontSize: 11, bold: true, color: C.bg, align: 'center', margin: 0 });
  s.addText(a[1], { x: x + 0.95, y: y + 0.22, w: (i < 3 ? 2.3 : 4.4), h: 0.27, fontSize: 12, bold: true, color: C.ink, margin: 0, fit: 'shrink' });
  s.addText(a[2], { x: x + 0.95, y: y + 0.58, w: (i < 3 ? 2.35 : 4.55), h: 0.42, fontSize: 9.2, color: C.muted, margin: 0, fit: 'shrink' });
});

// 3 Section part 1
s = slide();
section(s, '1', 'Что сделано по итогам проекта', 'Проект доведён до рабочего MVP: можно тестировать реальный учебный сценарий, а не только демонстрационный экран.', C.green);

// 4 Done overview
s = slide();
title(s, 'Часть 1', 'Что уже сделано: рабочий MVP', 'Коротко: есть продуктовый контур, учебная математика, роли пользователей, безопасность, мониторинг и восстановление.');
bulletCard(s, 0.6, 2.0, 3.85, 2.05, 'Учебный контур', ['Ученик видит предметы, темы, урок, чат и практику', 'Математика полностью подготовлена: 42 темы из 42', 'Есть диагностика и маршрут прохождения'], C.green);
bulletCard(s, 4.75, 2.0, 3.85, 2.05, 'Роли вокруг ученика', ['Родитель видит сводку и рекомендации', 'Учитель управляет материалами и готовностью тем', 'Админ контролирует пользователей, инвайты, аудит и мониторинг'], C.blue);
bulletCard(s, 8.9, 2.0, 3.85, 2.05, 'Эксплуатация', ['Production-домен работает', 'Backup и offsite-копии настроены', 'Prometheus/Grafana следят за состоянием'], C.amber);
statCard(s, 1.2, 4.65, 2.2, 1.1, '42/42', 'тем математики готовы', C.green);
statCard(s, 3.9, 4.65, 2.2, 1.1, '15/15', 'P0 темы прошли smoke', C.blue);
statCard(s, 6.6, 4.65, 2.2, 1.1, '4 роли', 'ученик / родитель / учитель / админ', C.violet);
statCard(s, 9.3, 4.65, 2.2, 1.1, 'OK', 'production health', C.amber);

// 5 What done details
s = slide();
title(s, 'Часть 1', 'Что сделано: результат для пользователей', 'Перевод с технического языка на простой: что человек реально получает в продукте.');
bulletCard(s, 0.65, 1.85, 3.9, 1.55, 'Для ученика', ['понятный маршрут по математике', 'объяснение темы и практика', 'следующий шаг после ответа'], C.green);
bulletCard(s, 4.72, 1.85, 3.9, 1.55, 'Для родителя', ['видно, что происходит с обучением', 'есть слабые темы и “что сделать завтра”', 'без доступа к личному чату ребёнка'], C.blue);
bulletCard(s, 8.78, 1.85, 3.9, 1.55, 'Для учителя', ['готовность тем в одном месте', 'редактор follow-up и fallback-заданий', 'видно, что требует вычитки'], C.violet);
bulletCard(s, 2.68, 4.05, 3.9, 1.55, 'Для администратора', ['мониторинг, пользователи, инвайты', 'аудит действий', 'состояние сервиса без SSH'], C.amber);
bulletCard(s, 6.75, 4.05, 3.9, 1.55, 'Для владельца проекта', ['есть управляемый пилот', 'есть backup и rollback', 'понятно, что улучшать дальше'], C.rose);

// 6 Section part 2
s = slide();
section(s, '2', 'Что предстоит сделать в ближайший месяц', 'Цель месяца — превратить рабочий MVP в надёжный пилот с ребёнком: меньше ручных проверок, больше качества обучения.', C.blue);

// 7 Month roadmap
s = slide();
title(s, 'Часть 2', 'План на ближайший месяц', 'Фокус не на “ещё одной фиче”, а на качестве, доказуемости и удобстве пилота.');
const month = [
  ['1', 'Живой пилот', 'Провести реальный сценарий с учеником: диагностика → маршрут → 2–3 темы → родительская сводка.'],
  ['2', 'Редактура математики', 'Проверить объяснения и задания человеком, убрать слабые формулировки.'],
  ['3', 'Больше практики', 'Сделать вариативность задач: базовые, средние, сложные.'],
  ['4', 'Адаптивность', 'Использовать mastery, ошибки и диагностику для выбора следующей темы.'],
  ['5', 'Пилотная отчётность', 'Еженедельный отчёт: что освоено, где просадка, что делать дальше.'],
];
month.forEach((it, i) => bulletCard(s, 0.72 + (i % 2) * 6.05, 1.65 + Math.floor(i / 2) * 1.55, 5.55, 1.18, it[1], [it[2]], i % 2 ? C.violet : C.blue));
pill(s, 'Итог месяца: можно регулярно тестировать с ребёнком', 4.3, 6.55, C.green, 4.8);

// 8 Month outcomes
s = slide();
title(s, 'Часть 2', 'Как будет выглядеть продукт через месяц', 'Ожидаемое состояние после пилотного месяца — не “идеально”, а достаточно надёжно для регулярного использования.');
statCard(s, 0.8, 1.7, 2.2, 1.25, '1', 'реальный ученик в пилоте', C.green);
statCard(s, 3.4, 1.7, 2.2, 1.25, '42', 'вычитанные темы математики', C.blue);
statCard(s, 6.0, 1.7, 2.2, 1.25, '3×', 'варианты практики на тему', C.violet);
statCard(s, 8.6, 1.7, 2.2, 1.25, '1/нед', 'понятный отчёт родителю', C.amber);
statCard(s, 11.2, 1.7, 1.3, 1.25, 'OK', 'стабильность', C.green);
bulletCard(s, 0.9, 3.55, 3.55, 1.8, 'Измеримый прогресс', ['mastery по темам', 'ошибки и повторение', 'следующая тема не случайна'], C.green);
bulletCard(s, 4.9, 3.55, 3.55, 1.8, 'Понятность для семьи', ['родитель видит простой план', 'ребёнок понимает следующий шаг', 'учитель видит проблемные места'], C.blue);
bulletCard(s, 8.9, 3.55, 3.55, 1.8, 'Готовность к расширению', ['знаем, что работает', 'знаем стоимость поддержки', 'можно переносить шаблон на новые предметы'], C.violet);

// 9 Section part 3
s = slide();
section(s, '3', 'Что предстоит сделать за 3 месяца', 'Цель квартала — перейти от пилота по математике к учебной платформе с несколькими предметами и управлением качеством.', C.violet);

// 10 Three month roadmap
s = slide();
title(s, 'Часть 3', 'План на ближайшие 3 месяца', 'Квартальный горизонт: масштабирование без потери качества и контроля.');
const quarter = [
  ['Месяц 1', 'Пилот математики', ['живой тест', 'качество заданий', 'отчётность родителю']],
  ['Месяц 2', 'Алгебра и геометрия', ['источники', 'маршруты', 'fallback bank', 'smoke по темам']],
  ['Месяц 3', 'Платформенный слой', ['аналитика', 'управление качеством', 'масштабирование ролей']],
];
quarter.forEach((q, i) => {
  const x = 0.75 + i * 4.15;
  card(s, x, 1.85, 3.65, 3.55, { fill: i === 0 ? '102A22' : i === 1 ? '17213C' : '21183A' });
  s.addText(q[0], { x: x + 0.22, y: 2.08, w: 3.1, h: 0.28, fontSize: 13, bold: true, color: i === 0 ? C.green : i === 1 ? C.blue : C.violet, margin: 0 });
  s.addText(q[1], { x: x + 0.22, y: 2.55, w: 3.1, h: 0.4, fontSize: 17, bold: true, color: C.ink, margin: 0, fit: 'shrink' });
  const runs = q[2].map((b, idx) => ({ text: b, options: { bullet: { indent: 10 }, breakLine: idx < q[2].length - 1 } }));
  s.addText(runs, { x: x + 0.35, y: 3.18, w: 2.85, h: 1.45, fontSize: 11, color: C.muted, margin: 0.03, paraSpaceAfter: 5 });
});
pill(s, 'Квартальный результат: AI-репетитор становится управляемой учебной платформой', 2.55, 6.22, C.violet, 8.4);

// 11 Three month outcomes
s = slide();
title(s, 'Часть 3', 'Ожидаемый результат через 3 месяца', 'Проект должен уйти от “ручного пилота” к системе, которую можно повторяемо расширять.');
bulletCard(s, 0.7, 1.75, 3.85, 1.75, 'Учебный охват', ['математика стабилизирована', 'алгебра и геометрия подготовлены', 'preview-предметы постепенно проходят такую же подготовку'], C.violet);
bulletCard(s, 4.75, 1.75, 3.85, 1.75, 'Качество', ['контент проходит редакторский контроль', 'темы имеют источники и fallback-задания', 'ошибки ребёнка превращаются в план повторения'], C.blue);
bulletCard(s, 8.8, 1.75, 3.85, 1.75, 'Управление', ['teacher workspace становится центром качества', 'admin видит реальные риски', 'backup/monitoring остаются обязательными'], C.green);
bulletCard(s, 2.65, 4.15, 3.85, 1.45, 'Данные для решений', ['видно, что ребёнок учит', 'видно, что работает', 'видно, какие темы требуют улучшения'], C.amber);
bulletCard(s, 6.85, 4.15, 3.85, 1.45, 'Готовность к росту', ['можно добавлять учеников', 'можно добавлять предметы', 'можно обсуждать внешнее тестирование'], C.rose);

// 12 Section part 4
s = slide();
section(s, '4', 'Глобальное отличие проекта в каждой фазе', 'Главная мысль: каждая новая фаза меняет не только набор функций, а уровень зрелости продукта.', C.amber);

// 13 Phase differences
s = slide();
title(s, 'Часть 4', 'Чем каждая фаза отличается от предыдущей', 'От “работает на экране” к “можно доверять процессу обучения”.');
const phases = [
  ['Фаза 0', 'Прототип', 'Проверяем, что идея вообще возможна.', 'Экран и AI-ответы'],
  ['Фаза 1', 'MVP', 'Появляется рабочий путь ученика и основные роли.', 'Учебный сценарий'],
  ['Фаза 2', 'Пилот', 'Появляется качество, диагностика и реальные данные.', 'Обучение ребёнка'],
  ['Фаза 3', 'Платформа', 'Появляется масштабирование предметов и управление качеством.', 'Повторяемый процесс'],
  ['Фаза 4', 'Экосистема', 'Появляется сеть пользователей, методика и внешняя проверка.', 'Образовательный продукт'],
];
phases.forEach((p, i) => {
  const y = 1.42 + i * 1.05;
  card(s, 0.72, y, 11.9, 0.82, { fill: i % 2 ? C.panel2 : C.panel, transparency: 0 });
  s.addText(p[0], { x: 0.95, y: y + 0.22, w: 1.0, h: 0.18, fontSize: 9, bold: true, color: C.amber, margin: 0 });
  s.addText(p[1], { x: 2.05, y: y + 0.17, w: 1.8, h: 0.25, fontSize: 12, bold: true, color: C.ink, margin: 0 });
  s.addText(p[2], { x: 4.0, y: y + 0.17, w: 4.65, h: 0.26, fontSize: 10, color: C.muted, margin: 0, fit: 'shrink' });
  pill(s, p[3], 9.15, y + 0.19, [C.blue, C.green, C.violet, C.amber, C.rose][i], 2.6);
});

// 14 Section part 5
s = slide();
section(s, '5', 'Топ-5 фишек на каждом этапе проекта', 'Что будет самым заметным и ценным для обычного пользователя и для стейкхолдера.', C.rose);

// 15 Top 5 now
s = slide();
title(s, 'Часть 5', 'Топ-5 фишек текущего этапа', 'Что уже можно показывать как сильные стороны MVP.');
const featuresNow = [
  ['1', 'Математика 42/42', 'полный маршрут тем с источниками и практикой'],
  ['2', 'AI-урок', 'объяснение, чат, практика и следующий шаг'],
  ['3', 'Родительская сводка', 'понятно, где ребёнку нужна помощь'],
  ['4', 'Учительская готовность', 'видно, какие темы готовы и что улучшать'],
  ['5', 'Ops-контур', 'backup, мониторинг, health-checks, rollback-ready'],
];
featuresNow.forEach((f, i) => bulletCard(s, 0.7 + (i % 2) * 6.1, 1.55 + Math.floor(i / 2) * 1.45, i === 4 ? 11.95 : 5.55, 1.1, `${f[0]}. ${f[1]}`, [f[2]], [C.green, C.blue, C.violet, C.amber, C.rose][i]));

// 16 Top 5 next month
s = slide();
title(s, 'Часть 5', 'Топ-5 фишек ближайшего месяца', 'Что станет заметно лучше после пилотного месяца.');
[
  ['Живой учебный маршрут', 'следующая тема выбирается не случайно'],
  ['Редакторское качество', 'задания становятся “как у хорошего репетитора”'],
  ['Реальные отчёты родителю', 'понятно, что делать завтра'],
  ['Диагностика перед стартом', 'ребёнок начинает со своих слабых мест'],
  ['Вариативная практика', 'не однотипные задания, а серия упражнений'],
].forEach((f, i) => bulletCard(s, 0.7 + (i % 2) * 6.1, 1.55 + Math.floor(i / 2) * 1.45, i === 4 ? 11.95 : 5.55, 1.1, `${i + 1}. ${f[0]}`, [f[1]], [C.blue, C.green, C.violet, C.amber, C.rose][i]));

// 17 Top 5 3 months
s = slide();
title(s, 'Часть 5', 'Топ-5 фишек горизонта 3 месяца', 'Что превращает MVP в платформу.');
[
  ['Несколько предметов', 'математика → алгебра → геометрия → дальше'],
  ['Адаптивный план', 'система сама выбирает повторение и новую тему'],
  ['Контроль качества контента', 'учитель видит и улучшает слабые места'],
  ['Управленческая аналитика', 'понятно, какие темы и сценарии работают'],
  ['Масштабируемый пилот', 'можно добавлять учеников без ручного хаоса'],
].forEach((f, i) => bulletCard(s, 0.7 + (i % 2) * 6.1, 1.55 + Math.floor(i / 2) * 1.45, i === 4 ? 11.95 : 5.55, 1.1, `${i + 1}. ${f[0]}`, [f[1]], [C.violet, C.blue, C.green, C.amber, C.rose][i]));

// 18 Risks / decisions
s = slide();
title(s, 'Управленческий взгляд', 'Главные решения и риски', 'Чтобы двигаться быстрее, нужно явно выбрать границы пилота и критерии качества.');
bulletCard(s, 0.7, 1.65, 3.8, 2.0, 'Решение 1: фокус', ['пока не распыляться на все предметы', 'довести математику до сильного пилота', 'потом переносить шаблон'], C.blue);
bulletCard(s, 4.8, 1.65, 3.8, 2.0, 'Решение 2: качество', ['нужна редакторская вычитка', 'AI не должен быть единственным автором', 'учительская роль становится ключевой'], C.green);
bulletCard(s, 8.9, 1.65, 3.8, 2.0, 'Решение 3: пилот', ['1–3 реальных ученика', 'еженедельный отчёт', 'фиксируем, что улучшает обучение'], C.violet);
bulletCard(s, 2.75, 4.35, 3.8, 1.45, 'Риск', ['сырой контент снижает доверие быстрее, чем отсутствие новых функций'], C.rose);
bulletCard(s, 6.85, 4.35, 3.8, 1.45, 'Контроль', ['каждая новая тема проходит источники, практику, smoke и ручную проверку'], C.amber);

// 19 Final summary
s = slide();
title(s, 'Итог', 'Что сказать стейкхолдеру одной фразой', 'AI-Tutor уже стал рабочим MVP. Следующий этап — доказать ценность на живом учебном процессе и масштабировать только то, что реально работает.');
statCard(s, 1.0, 2.05, 2.35, 1.35, 'MVP', 'уже работает', C.green);
statCard(s, 3.85, 2.05, 2.35, 1.35, '42/42', 'математика готова', C.blue);
statCard(s, 6.7, 2.05, 2.35, 1.35, '1 мес', 'пилот и качество', C.amber);
statCard(s, 9.55, 2.05, 2.35, 1.35, '3 мес', 'платформа', C.violet);
card(s, 1.35, 4.25, 10.6, 1.25, { fill: '102A22' });
s.addText('Рекомендация: следующий шаг — не добавлять хаотично новые функции, а провести живой math-пилот, собрать данные и затем масштабировать проверенный шаблон на новые предметы.', { x: 1.72, y: 4.6, w: 9.85, h: 0.5, fontSize: 16, bold: true, color: C.ink, align: 'center', margin: 0, fit: 'shrink' });
s.addNotes('Закрыть презентацию решением: математика — пилотный флагман; качество и данные важнее скорости добавления новых предметов.');

const out = path.join('/root/workspace/ai-tutor/docs', 'AI-Tutor-Stakeholder-Presentation-2026-08-14.pptx');
pptx.writeFile({ fileName: out });
console.log(out);
