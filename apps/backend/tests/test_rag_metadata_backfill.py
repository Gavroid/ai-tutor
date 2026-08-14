from types import SimpleNamespace

from scripts.rag_metadata_backfill import enrich_metadata, infer_part


def test_infer_part_from_vilenkin_material_title():
    assert infer_part("Виленкин 6 класс — часть 2: Решение уравнений") == 2
    assert infer_part("Виленкин 6 класс — часть 1: Проценты") == 1


def test_infer_part_preserves_existing_part():
    assert infer_part("Без части", existing=3) == 3


def test_enrich_metadata_adds_citation_safe_fields_without_page_invention():
    topic = SimpleNamespace(id=188, name="Проценты")
    material = SimpleNamespace(title="Виленкин 6 класс — часть 1: Проценты")
    enriched, changed = enrich_metadata({"topic_id": 188, "page_number": 137}, topic=topic, material=material)

    assert changed is True
    assert enriched["topic_id"] == 188
    assert enriched["topic_name"] == "Проценты"
    assert enriched["page_number"] == 137
    assert enriched["part"] == 1
    assert enriched["material_title"] == "Виленкин 6 класс — часть 1: Проценты"


def test_enrich_metadata_is_idempotent_when_fields_already_present():
    topic = SimpleNamespace(id=204, name="Пропорции")
    material = SimpleNamespace(title="Виленкин 6 класс — часть 1: Пропорции")
    meta = {"topic_id": 204, "topic_name": "Пропорции", "page_number": 125, "part": 1, "material_title": material.title}

    enriched, changed = enrich_metadata(meta, topic=topic, material=material)

    assert enriched == meta
    assert changed is False
