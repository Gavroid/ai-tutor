"""Project-owned Geometry source notes manifest.

This builds source/RAG-shaped rows from internally authored Geometry notes. It
avoids external textbook scans and diagram-dependent extraction while preserving
metadata needed by the RAG readiness audit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from app.geometry_plan import GEOMETRY_TOPIC_PLAN

_LICENSE = "Project-owned internal notes"
_ATTRIBUTION = "AI-Tutor project-authored Geometry notes, created for this pilot curriculum."
_SOURCE = "internal_geometry_notes"
_SOURCE_TITLE = "Geometry internal source notes"

_NOTE_BY_TOPIC: dict[int, str] = {
    53: "Прямая задаёт направление без начала и конца. Отрезок ограничен двумя точками и имеет длину. Луч начинается в одной точке и продолжается в одном направлении. Угол образуют два луча с общим началом; его величину измеряют в градусах. В задачах важно сначала назвать объект, затем указать его границы или вершину.",
    54: "Длину отрезка находят сравнением с единицей измерения. Если точка лежит между концами большего отрезка, длины соседних частей складываются. Углы измеряют в градусах: прямой угол равен 90°, развёрнутый равен 180°. При вычислениях полезно записывать, какие части образуют целый отрезок или целый угол.",
    55: "Смежные углы имеют общую сторону, а две другие стороны образуют прямую; поэтому их сумма равна 180°. Вертикальные углы появляются при пересечении двух прямых и всегда равны. Чтобы не перепутать свойства, нужно определить пару углов: смежные дают сумму, вертикальные дают равенство.",
    56: "Перпендикулярные прямые пересекаются под прямым углом. Если при пересечении прямых один угол равен 90°, то остальные углы тоже определяются через смежность и вертикальность. В доказательствах достаточно показать наличие одного прямого угла, чтобы сделать вывод о перпендикулярности прямых.",
    57: "Треугольники равны, если их можно совместить так, что совпадут соответствующие стороны и углы. Основные признаки равенства используют ограниченный набор данных: две стороны и угол между ними, сторона и два прилежащих угла, либо три стороны. Важно проверять соответствие элементов в правильном порядке.",
    58: "Медиана соединяет вершину треугольника с серединой противоположной стороны. Биссектриса делит угол вершины на две равные части. Высота проводится из вершины перпендикулярно прямой, содержащей противоположную сторону. Эти отрезки могут совпадать только в специальных треугольниках, поэтому их определения нужно различать.",
    59: "Равнобедренный треугольник имеет две равные боковые стороны. Углы при основании такого треугольника равны. Обратное утверждение тоже полезно: если два угла треугольника равны, то равны стороны, лежащие напротив этих углов. Эти свойства часто применяются после нахождения равных сторон или углов.",
    60: "Окружность — множество точек плоскости, равноудалённых от центра. Радиус соединяет центр с точкой окружности, диаметр проходит через центр и равен двум радиусам. В задачах на построение обычно фиксируют центр, радиус или расстояние между точками, а затем используют определения окружности и равенства отрезков.",
    61: "Параллельность двух прямых можно доказать по углам, которые образуются при пересечении секущей. Если накрест лежащие углы равны, прямые параллельны. Если соответственные углы равны, прямые также параллельны. Ещё один признак: сумма односторонних углов равна 180°.",
    62: "Если две параллельные прямые пересечены секущей, то соответственные углы равны, накрест лежащие углы равны, а односторонние углы в сумме дают 180°. Эти свойства используют после того, как параллельность уже известна. В вычислениях сначала выбирают нужную пару углов, затем применяют равенство или сумму.",
    63: "Сумма внутренних углов любого треугольника равна 180°. Если известны два угла, третий находят вычитанием их суммы из 180°. В равнобедренном треугольнике это свойство часто используют вместе с равенством углов при основании. Проверка ответа проста: все три угла должны снова дать 180°.",
    64: "Внешний угол треугольника образуется продолжением одной стороны. Он равен сумме двух внутренних углов, не смежных с ним. Также внешний угол вместе со смежным внутренним углом образует 180°. Поэтому одну и ту же задачу можно решить через сумму удалённых внутренних углов или через смежный угол.",
    65: "Для существования треугольника сумма любых двух сторон должна быть больше третьей стороны. На практике достаточно проверить, что сумма двух меньших сторон больше самой большой стороны. Если сумма равна или меньше, треугольник построить нельзя. Это условие помогает быстро отличить возможные наборы длин от невозможных.",
}


def _chunk_hash(material_id: int, text: str) -> str:
    return hashlib.sha256(f"geometry:{material_id}:{text}".encode("utf-8")).hexdigest()[:16]


def build_geometry_internal_source_manifest() -> dict[str, object]:
    materials: list[dict[str, object]] = []
    chunks: list[dict[str, object]] = []
    audit_rows: list[dict[str, object]] = []
    for idx, topic in enumerate(GEOMETRY_TOPIC_PLAN, start=1):
        material_id = 20000 + idx
        text = _NOTE_BY_TOPIC[topic.topic_id]
        title = f"Geometry internal notes — {topic.focus}"
        source_section = f"{topic.section} / {topic.focus}"
        metadata = {
            "subject_code": "geometry",
            "topic_id": topic.topic_id,
            "topic_name": topic.focus,
            "source_title": _SOURCE_TITLE,
            "material_title": title,
            "source_url": "internal://geometry/project-authored-notes",
            "source_section": source_section,
            "license": _LICENSE,
            "attribution": _ATTRIBUTION,
            "source_mode": "project_owned_text_notes",
        }
        material = {
            "id": material_id,
            "topic_id": topic.topic_id,
            "subject_code": "geometry",
            "title": title,
            "content": text,
            "source": _SOURCE,
            "source_url": "internal://geometry/project-authored-notes",
            "source_section": source_section,
            "license": _LICENSE,
            "attribution": _ATTRIBUTION,
            "status": "draft_internal_source_notes",
        }
        chunk = {
            "id": f"geometry-internal-{topic.topic_id}-1",
            "material_id": material_id,
            "hash": _chunk_hash(material_id, text),
            "text": text,
            "embedding_json": "[]",
            "metadata_json": json.dumps(metadata, ensure_ascii=False),
        }
        materials.append(material)
        chunks.append(chunk)
        audit_rows.append(
            {
                "chunk_id": chunk["id"],
                "material_id": material_id,
                "material_title": title,
                "material_topic_id": topic.topic_id,
                "material_subject_code": "geometry",
                "metadata_json": chunk["metadata_json"],
            }
        )
    return {
        "mode": "geometry_internal_source_manifest",
        "subject": "geometry",
        "topic_count": len(materials),
        "source": _SOURCE,
        "license": _LICENSE,
        "production_mutation": False,
        "db_write": False,
        "rag_write": False,
        "promotion_allowed": False,
        "materials": materials,
        "chunks": chunks,
        "audit_rows": audit_rows,
    }


def write_manifest(path: Path) -> Path:
    manifest = build_geometry_internal_source_manifest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Geometry project-owned source notes manifest")
    parser.add_argument("--out", default="/tmp/ai-tutor-geometry-internal-source-manifest.json")
    args = parser.parse_args()
    out = write_manifest(Path(args.out))
    manifest = json.loads(out.read_text(encoding="utf-8"))
    print(json.dumps({"ok": True, "out": str(out), "topic_count": manifest["topic_count"], "source": manifest["source"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
