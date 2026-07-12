"""Внутренняя утилита: та же логика, что в seed.py, но без CLI-обвязки.

Используется тестами и в seed-скрипте (для исключения дублирования).
"""
from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.subjects import models
from app.subjects.curriculum_7_class import CURRICULUM_7_CLASS


def seed_for_tests(db: Session, reset: bool = False) -> int:
    if reset:
        db.execute(delete(models.Question))
        db.execute(delete(models.LearningMaterial))
        db.execute(delete(models.Subtopic))
        db.execute(delete(models.Topic))
        db.execute(delete(models.Section))
        db.execute(delete(models.Subject))
        db.commit()

    created = 0
    for subj_data in CURRICULUM_7_CLASS:
        subject = models.Subject(
            code=subj_data["code"],
            name=subj_data["name"],
            description=subj_data["description"],
            color=subj_data.get("color"),
            icon=subj_data.get("icon"),
            recommended_grade=7,
            age_min=12,
            age_max=14,
            is_active=True,
        )
        db.add(subject)
        db.flush()
        created += 1

        for sec_idx, (sec_name, topics) in enumerate(subj_data["sections"]):
            section = models.Section(
                subject_id=subject.id, name=sec_name, order_index=sec_idx
            )
            db.add(section)
            db.flush()
            created += 1

            for topic_idx, (topic_name, difficulty, subtopics) in enumerate(topics):
                topic = models.Topic(
                    section_id=section.id,
                    name=topic_name,
                    difficulty=difficulty,
                    order_index=topic_idx,
                )
                db.add(topic)
                db.flush()
                created += 1

                for sub_idx, sub_name in enumerate(subtopics):
                    if not sub_name:
                        continue
                    db.add(
                        models.Subtopic(
                            topic_id=topic.id, name=sub_name, order_index=sub_idx
                        )
                    )
                    created += 1

    db.commit()
    return created