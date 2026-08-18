"""MVP rescue: contract tests for real-provider AI output cleanup/parsing."""
from __future__ import annotations

import json

from types import SimpleNamespace

import pytest

from app.ai.hermes import _extract_structured_json, _prepare_model_output
from app.ai.service import AIService, GeneratedExercise, _dedupe_rag_sources, _exercise_matches_topic, _rag_enabled_for_subject, _verified_rag_sources, _trim_incomplete_trailing_fragment, _valid_generated_exercise
from app.ai.types import AIMessage, AIRequest, AIResponse, AIProvider


class StaticProvider(AIProvider):
    def __init__(self, response: AIResponse) -> None:
        self.response = response

    async def complete(self, req: AIRequest) -> AIResponse:
        return self.response

    async def ping(self) -> bool:
        return True


class SequenceProvider(AIProvider):
    def __init__(self, responses: list[AIResponse]) -> None:
        self.responses = list(responses)
        self.calls = 0

    async def complete(self, req: AIRequest) -> AIResponse:
        self.calls += 1
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]

    async def ping(self) -> bool:
        return True


def test_prepare_model_output_strips_raw_think_blocks() -> None:
    content, structured = _prepare_model_output(
        "<think>private reasoning</think>\n\n**Коротко:** это дробь."
    )

    assert "think" not in content.lower()
    assert "private reasoning" not in content
    assert content == "**Коротко:** это дробь."
    assert structured is None


def test_prepare_model_output_strips_escaped_think_blocks() -> None:
    content, structured = _prepare_model_output(
        "&lt;think&gt;private reasoning&lt;/think&gt;\n\nОтвет ученику"
    )

    assert "think" not in content.lower()
    assert "private reasoning" not in content
    assert content == "Ответ ученику"
    assert structured is None


def test_prepare_model_output_extracts_json_after_reasoning() -> None:
    raw = """
<think>Need JSON.</think>
Here is the result:
{"is_correct": true, "score": 1.0, "explanation": "Верно"}
"""

    content, structured = _prepare_model_output(raw)

    assert structured == {"is_correct": True, "score": 1.0, "explanation": "Верно"}
    assert json.loads(content) == structured
    assert "think" not in content.lower()


def test_extract_structured_json_handles_fenced_json() -> None:
    structured = _extract_structured_json(
        "```json\n{\"question_text\": \"Сколько будет 2+2?\", \"type\": \"numeric\"}\n```"
    )

    assert structured == {"question_text": "Сколько будет 2+2?", "type": "numeric"}


def test_rag_sources_enabled_for_math_like_subjects_only() -> None:
    assert _rag_enabled_for_subject("Математика (6 класс - повторение пройденного материала)")
    assert _rag_enabled_for_subject("Алгебра")
    assert _rag_enabled_for_subject("Геометрия")
    assert not _rag_enabled_for_subject("Русский язык")


def test_rag_sources_are_deduplicated() -> None:
    sources = [
        {"material_title": "Математика 6 класс", "page_number": 114, "chunk_id": "a"},
        {"material_title": "Математика 6 класс", "page_number": 114, "chunk_id": "b"},
        {"material_title": "Математика 6 класс", "page_number": 130, "chunk_id": "c"},
    ]

    deduped = _dedupe_rag_sources(sources)

    assert deduped == [
        {"material_title": "Математика 6 класс", "page_number": 114, "chunk_id": "a"},
        {"material_title": "Математика 6 класс", "page_number": 130, "chunk_id": "c"},
    ]


def test_decimal_topic_rejects_common_fraction_exercise_drift() -> None:
    exercise = GeneratedExercise(
        question_text="Вычисли: 1/2 + 1/3. Выбери правильный ответ.",
        type="single",
        options=["5/6", "2/5"],
        correct_answer="5/6",
        explanation="Приводим к общему знаменателю.",
        typical_mistakes=[],
    )

    assert not _exercise_matches_topic(exercise, "Действия с десятичными дробями")


def test_prepare_model_output_removes_markdown_fence_and_table_separator() -> None:
    content, structured = _prepare_model_output(
        """
```markdown
| Действие | Что помнить |
|---|---|
| Деление | Сделай делитель целым |
```
"""
    )

    assert structured is None
    assert "```" not in content
    assert "|---|" not in content
    assert "Действие" in content


def test_prepare_model_output_removes_visible_entities_and_latex_artifacts() -> None:
    content, structured = _prepare_model_output(
        """
Формула простая:
$$\\text{Среднее} = \\frac{\\text{сумма всех чисел}}{\\text{сколько чисел}}$$

&amp;gt;
25% = 25 ÷ 100 = 0,25
"""
    )

    assert structured is None
    assert "&amp;gt;" not in content
    assert "&gt;" not in content
    assert "$$" not in content
    assert "\\frac" not in content
    assert "\\text" not in content
    assert "Среднее" in content
    assert "сумма всех чисел" in content
    assert "25% = 25 ÷ 100 = 0,25" in content



def test_prepare_model_output_removes_dangling_display_math_marker() -> None:
    content, structured = _prepare_model_output(
        """
Формула выглядит так:

$$(16,1 + 16,1 + 16,1 +

Среднее чисел
"""
    )

    assert structured is None
    assert "$$" not in content
    assert "16,1 + 16,1 + 16,1" in content
    assert "Среднее чисел" in content

def test_prepare_model_output_normalizes_decimal_latex_frac_with_braced_comma() -> None:
    content, structured = _prepare_model_output(r"vср = \frac{110{,}6}{7} = 15{,}8 км/ч")

    assert structured is None
    assert "\\frac" not in content
    assert "110{,}6" not in content
    assert "110,6 / 7" in content
    assert "15,8" in content


def test_prepare_model_output_normalizes_plain_latex_variables_and_dots() -> None:
    content, structured = _prepare_model_output(
        r"""
Средняя порция = сумма всех порций ÷ количество порций

Формула простая:

Среднее = (x_1 + x_2 + x_3 + \dots + x_n) / (n)

где x_1, x_2, \dots — это сколько борща получил каждый.
"""
    )

    assert structured is None
    assert "\\dots" not in content
    assert "x_1" not in content
    assert "x_2" not in content
    assert "x_n" not in content
    assert "…" in content
    assert "x1" in content


def test_verified_rag_sources_require_topic_and_page_metadata() -> None:
    sources = [
        {
            "chunk_id": "good",
            "material_id": 1,
            "material_title": "Виленкин 6 класс — часть 1: Проценты",
            "page_number": 19,
            "part": 1,
            "topic_id": 188,
            "topic_name": "Проценты",
            "snippet": "Процент — это одна сотая часть числа.",
        },
        {
            "chunk_id": "wrong-topic",
            "material_id": 2,
            "material_title": "Виленкин 6 класс — часть 1: Круговые диаграммы",
            "page_number": 27,
            "part": 1,
            "topic_id": 189,
            "topic_name": "Круговые диаграммы",
            "snippet": "Круг делится на секторы.",
        },
        {
            "chunk_id": "no-page",
            "material_id": 3,
            "material_title": "Виленкин 6 класс",
            "part": 1,
            "topic_id": 188,
            "topic_name": "Проценты",
            "snippet": "Нет страницы.",
        },
    ]

    verified = _verified_rag_sources(sources, topic_id=188, topic_name="Проценты")

    assert verified == [
        {
            "chunk_id": "good",
            "material_id": 1,
            "material_title": "Виленкин 6 класс — часть 1: Проценты",
            "page_number": 19,
            "part": 1,
            "topic_id": 188,
            "topic_name": "Проценты",
            "snippet": "Процент — это одна сотая часть числа.",
            "citation_confidence": "verified",
            "label": "Виленкин 6 класс — часть 1: Проценты, часть 1, стр. 19",
        }
    ]


@pytest.mark.asyncio
async def test_generate_exercise_uses_safe_fallback_for_unstructured_output() -> None:
    svc = AIService(
        StaticProvider(
            AIResponse(
                content=" raw reasoning without valid object",
                model="test-model",
                structured=None,
            )
        )
    )

    exercise = await svc.generate_exercise("Математика (6 класс - повторение пройденного материала)", "Действия с обыкновенными дробями", 2)

    assert "think" not in exercise.question_text.lower()
    assert "raw reasoning" not in exercise.question_text.lower()
    assert exercise.type == "single"
    assert exercise.options
    assert exercise.correct_answer in exercise.options
    assert "1/2" in exercise.question_text or "дроб" in exercise.question_text.lower()


@pytest.mark.asyncio
async def test_explain_topic_uses_safe_fallback_when_model_content_empty() -> None:
    svc = AIService(
        StaticProvider(
            AIResponse(
                content="",
                model="test-model",
                structured=None,
            )
        )
    )
    topic = SimpleNamespace(
        name="Фразеологизмы",
        section=SimpleNamespace(subject=SimpleNamespace(name="Русский язык")),
    )
    user = SimpleNamespace(student_profile=SimpleNamespace(grade=7))

    response = await svc.explain_topic(None, user, topic)

    assert response.content
    assert "Фразеологизмы" in response.content
    assert "think" not in response.content.lower()


@pytest.mark.asyncio
async def test_explain_topic_uses_fallback_when_model_content_too_short() -> None:
    svc = AIService(StaticProvider(AIResponse(content="# Деление рациональных чисел\n\nСлишком коротко", model="test-model", structured=None)))
    topic = SimpleNamespace(
        name="Деление рациональных чисел",
        section=SimpleNamespace(
            subject=SimpleNamespace(name="Математика (6 класс - повторение пройденного материала)")
        ),
    )
    user = SimpleNamespace(student_profile=SimpleNamespace(grade=7))

    response = await svc.explain_topic(None, user, topic)

    assert len(response.content) > 500
    assert "правило знаков" in response.content.lower()
    assert "12 : (-3)" in response.content


@pytest.mark.asyncio
async def test_explain_topic_pie_chart_short_model_output_uses_instructional_fallback() -> None:
    svc = AIService(StaticProvider(AIResponse(content="Коротко про круговые диаграммы", model="test-model", structured=None)))
    topic = SimpleNamespace(
        name="Круговые диаграммы",
        section=SimpleNamespace(
            subject=SimpleNamespace(name="Математика (6 класс - повторение пройденного материала)")
        ),
    )
    user = SimpleNamespace(student_profile=SimpleNamespace(grade=7))

    response = await svc.explain_topic(None, user, topic)

    assert len(response.content) > 500
    assert "360" in response.content
    assert "сектор" in response.content.lower()
    assert "Коротко: начни с определения" not in response.content


@pytest.mark.asyncio
async def test_explain_topic_retries_short_model_output_before_fallback() -> None:
    provider = SequenceProvider([
        AIResponse(content="Слишком коротко", model="test-model", structured=None),
        AIResponse(
            content="Среднее арифметическое — это сумма чисел, делённая на их количество. "
            "Чтобы найти среднее, сначала складываем все значения, затем делим на число значений. "
            "Например, для чисел 4, 5 и 6 сумма равна 15, а 15 : 3 = 5. "
            "Проверочный вопрос: почему мы делим именно на 3?",
            model="test-model",
            structured=None,
        ),
    ])
    svc = AIService(provider)
    topic = SimpleNamespace(
        id=187,
        name="Среднее арифметическое",
        section=SimpleNamespace(
            subject=SimpleNamespace(name="Математика")
        ),
    )
    user = SimpleNamespace(student_profile=SimpleNamespace(grade=7))

    response = await svc.explain_topic(None, user, topic)

    assert provider.calls == 2
    assert "4, 5 и 6" in response.content
    assert "Коротко: начни" not in response.content


@pytest.mark.asyncio
async def test_chat_removes_incomplete_trailing_fragment() -> None:
    svc = AIService(
        StaticProvider(
            AIResponse(
                content="Хочешь сам? Придумай свою задачу, и мы её разберём. Или давай я дам похожую:\n\nВ",
                model="test-model",
                structured=None,
            )
        )
    )

    response = await svc.chat([
        {"role": "user", "content": "Дай похожий пример"},
    ], "Математика", "Проценты")

    assert _trim_incomplete_trailing_fragment("Хочешь сам? Придумай свою задачу. Или давай я дам похожую:\n\nВ") == "Хочешь сам? Придумай свою задачу."
    assert response.content.endswith("разберём.")
    assert "похожую" not in response.content
    assert not response.content.endswith("В")


@pytest.mark.asyncio
async def test_generate_exercise_decimal_fallback_matches_decimal_topic() -> None:
    svc = AIService(StaticProvider(AIResponse(content="bad", model="test-model", structured=None)))

    exercise = await svc.generate_exercise(
        "Математика (6 класс - повторение пройденного материала)",
        "Действия с десятичными дробями",
        2,
    )

    assert exercise.type == "single"
    assert exercise.correct_answer == "0,24"
    assert exercise.correct_answer in (exercise.options or [])
    assert "0,6" in exercise.question_text
    assert "1/2" not in exercise.question_text


@pytest.mark.asyncio
async def test_generate_exercise_pie_chart_fallback_is_student_ready() -> None:
    svc = AIService(StaticProvider(AIResponse(content="bad", model="test-model", structured=None)))

    exercise = await svc.generate_exercise(
        "Математика (6 класс - повторение пройденного материала)",
        "Круговые диаграммы",
        1,
    )

    assert exercise.type == "single"
    assert exercise.correct_answer == "90°"
    assert exercise.correct_answer in (exercise.options or [])
    visible = f"{exercise.question_text}\n{exercise.explanation}"
    assert "круг" in visible.lower()
    assert "25%" in visible
    assert "AI" not in visible
    assert "JSON" not in visible
    assert "резерв" not in visible.lower()


@pytest.mark.parametrize(
    ("topic_name", "expected_answer", "needle"),
    [
        ("Разложение числа на простые множители", "2² × 3²", "36"),
        ("Наибольший общий делитель. Взаимно простые числа", "6", "18"),
        ("Наименьшее общее кратное", "24", "6"),
        ("Приведение дробей к наименьшему общему знаменателю", "12", "общий знаменатель"),
        ("Сложение и вычитание смешанных чисел", "3 2/3", "2 1/3"),
        ("Умножение смешанных чисел", "3", "1 1/2"),
        ("Нахождение дроби от числа", "15", "3/4"),
        ("Деление смешанных чисел", "7", "3 1/2"),
        ("Отношения", "3:2", "12 девочек"),
    ],
)
@pytest.mark.asyncio
async def test_generate_exercise_p0_fallback_bank_is_student_ready(
    topic_name: str,
    expected_answer: str,
    needle: str,
) -> None:
    svc = AIService(StaticProvider(AIResponse(content="bad", model="test-model", structured=None)))

    exercise = await svc.generate_exercise(
        "Математика (6 класс - повторение пройденного материала)",
        topic_name,
        1 if topic_name == "Наибольший общий делитель. Взаимно простые числа" else 2,
    )

    assert exercise.type == "single"
    assert exercise.options
    assert exercise.correct_answer == expected_answer
    assert expected_answer in exercise.options
    visible = f"{exercise.question_text}\n{exercise.explanation}"
    assert needle.lower() in visible.lower()
    assert "Сформулируй короткий ответ" not in visible
    assert "AI" not in visible
    assert "JSON" not in visible
    assert "резерв" not in visible.lower()


@pytest.mark.parametrize(
    ("topic_name", "expected_answer", "needle"),
    [
        ("Виды треугольников", "равнобедренный", "две стороны"),
        ("Понятие множества", "{2, 4}", "чётные"),
        ("Дробные выражения", "3/2", "1/2"),
        ("Прямая и обратная пропорциональные зависимости", "15", "прямая"),
        ("Масштаб", "500", "1:100"),
        ("Симметрия", "ось симметрии", "делит фигуру"),
        ("Положительные и отрицательные числа", "-3", "ниже нуля"),
        ("Противоположные числа", "-7", "7"),
        ("Модуль числа", "8", "-8"),
        ("Сравнение положительных и отрицательных чисел", "-2", "-5"),
        ("Сложение отрицательных чисел", "-9", "-4"),
        ("Сложение чисел с разными знаками", "2", "-3"),
        ("Вычитание рациональных чисел", "-7", "3 - 10"),
        ("Умножение рациональных чисел", "-12", "-3"),
        ("Деление рациональных чисел", "-4", "12"),
    ],
)
@pytest.mark.asyncio
async def test_generate_exercise_p1_fallback_bank_is_student_ready(
    topic_name: str,
    expected_answer: str,
    needle: str,
) -> None:
    svc = AIService(StaticProvider(AIResponse(content="bad", model="test-model", structured=None)))

    exercise = await svc.generate_exercise(
        "Математика (6 класс - повторение пройденного материала)",
        topic_name,
        2,
    )

    assert exercise.type == "single"
    assert exercise.options
    assert exercise.correct_answer == expected_answer
    assert expected_answer in exercise.options
    visible = f"{exercise.question_text}\n{exercise.explanation}"
    assert needle.lower() in visible.lower()
    assert "Сформулируй короткий ответ" not in visible
    assert "AI" not in visible
    assert "JSON" not in visible
    assert "резерв" not in visible.lower()


@pytest.mark.asyncio
async def test_generate_exercise_gcd_fallback_varies_by_difficulty_seed() -> None:
    svc = AIService(StaticProvider(AIResponse(content="bad", model="test-model", structured=None)))

    first = await svc.generate_exercise(
        "Математика (6 класс - повторение пройденного материала)",
        "Наибольший общий делитель. Взаимно простые числа",
        1,
    )
    second = await svc.generate_exercise(
        "Математика (6 класс - повторение пройденного материала)",
        "Наибольший общий делитель. Взаимно простые числа",
        2,
    )

    assert first.question_text != second.question_text
    assert first.type == second.type == "single"
    assert first.options
    assert second.options


@pytest.mark.asyncio
async def test_explain_topic_math_fallback_is_instructional() -> None:
    svc = AIService(StaticProvider(AIResponse(content="", model="test-model", structured=None)))
    topic = SimpleNamespace(
        name="Действия с обыкновенными дробями",
        section=SimpleNamespace(
            subject=SimpleNamespace(name="Математика (6 класс - повторение пройденного материала)")
        ),
    )
    user = SimpleNamespace(student_profile=SimpleNamespace(grade=7))

    response = await svc.explain_topic(None, user, topic)

    assert "общему знаменателю" in response.content
    assert "1/2 + 1/3" in response.content
    assert len(response.content) > 500


@pytest.mark.asyncio
async def test_generate_exercise_accepts_json_after_think() -> None:
    content, structured = _prepare_model_output(
        """
<think>Create one task.</think>
{"question_text":"Что означает фразеологизм бить баклуши?","type":"single","options":["Лениться","Бежать","Читать"],"correct_answer":"Лениться","explanation":"Так говорят о безделье.","typical_mistakes":["Понимать буквально"]}
"""
    )
    svc = AIService(StaticProvider(AIResponse(content=content, model="test-model", structured=structured)))

    exercise = await svc.generate_exercise("Русский язык", "Фразеологизмы", 2)

    assert exercise.question_text == "Что означает фразеологизм бить баклуши?"
    assert exercise.type == "single"
    assert exercise.options == ["Лениться", "Бежать", "Читать"]
    assert exercise.correct_answer == "Лениться"


def _assert_student_clean(text: str) -> None:
    lowered = text.lower()
    assert "<think" not in lowered
    assert "&lt;think" not in lowered
    assert "hidden answer" not in lowered
    assert "```json" not in lowered
    assert '"correct_answer"' not in text
    assert "$$" not in text
    assert "\\frac" not in text
    assert "\\text" not in text
    assert "|---|" not in text


def test_valid_generated_exercise_sanitizes_all_student_visible_fields() -> None:
    exercise = _valid_generated_exercise(
        {
            "question_text": "<think>hidden answer</think>```json {\"question_text\":\"bad\"}```Вычисли $$\\frac{1}{2} + \\frac{1}{2}$$.",
            "type": "single",
            "options": ["<think>hidden</think>1", "0"],
            "correct_answer": "1",
            "explanation": "```json\n{\"correct_answer\":\"1\"}\n``` Сложили \\frac{1}{2} и \\frac{1}{2}.",
            "typical_mistakes": ["<think>x</think>Сложить знаменатели"],
        }
    )

    visible = "\n".join(
        [exercise.question_text, *(exercise.options or []), exercise.correct_answer, exercise.explanation, *exercise.typical_mistakes]
    )
    _assert_student_clean(visible)
    assert "1 / 2" in visible


@pytest.mark.asyncio
async def test_check_answer_structured_response_sanitizes_explanation() -> None:
    svc = AIService(
        StaticProvider(
            AIResponse(
                content="ignored",
                model="test-model",
                structured={
                    "is_correct": False,
                    "score": 0,
                    "first_error": "<think>hidden answer</think>Ошибка",
                    "explanation": "<think>hidden answer</think>```json\n{\"correct_answer\":\"4\"}\n``` Подумай про сумму.",
                    "hint_level": 1,
                    "next_difficulty": 1,
                },
            )
        )
    )

    result = await svc.check_answer("2+2", "4", "5")

    _assert_student_clean("\n".join([result.first_error or "", result.explanation]))
    assert "Подумай про сумму" in result.explanation


@pytest.mark.asyncio
async def test_check_answer_fallback_does_not_surface_raw_provider_json() -> None:
    svc = AIService(
        StaticProvider(
            AIResponse(
                content='<think>hidden answer</think>```json {"correct_answer":"4"}``` Подсказка: проверь сложение.',
                model="test-model",
                structured=None,
            )
        )
    )

    result = await svc.check_answer("2+2", "4", "5")

    _assert_student_clean(result.explanation)
    assert "проверь сложение" in result.explanation.lower()


@pytest.mark.asyncio
async def test_generate_quiz_fallback_does_not_surface_raw_provider_json() -> None:
    svc = AIService(
        StaticProvider(
            AIResponse(
                content='<think>hidden answer</think>```json {"correct_answer":"4"}``` Вопрос: сколько будет 2+2?',
                model="test-model",
                structured=None,
            )
        )
    )

    quiz = await svc.generate_quiz("Математика", "Сложение", 1, count=3)
    visible = "\n".join([quiz.questions[0].question_text, quiz.questions[0].explanation])

    _assert_student_clean(visible)
    assert "сколько будет" in visible.lower()
