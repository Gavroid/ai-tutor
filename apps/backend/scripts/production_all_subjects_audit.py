"""Fail-closed audit for all-subject production readiness payloads."""
from __future__ import annotations

import argparse
import json
import ssl
import urllib.request
from typing import Any, cast


def audit_subjects_payload(subjects: list[dict[str, Any]], *, expected_subject_count: int = 12) -> dict[str, object]:
    problems: list[str] = []
    if len(subjects) != expected_subject_count:
        problems.append(f"subject_count_mismatch:{len(subjects)}!={expected_subject_count}")
    total_topics = 0
    for subject in subjects:
        code = str(subject.get("code") or "unknown")
        topic_count = int(cast(Any, subject.get("topic_count") or 0))
        route_count = int(cast(Any, subject.get("route_topic_count") or 0))
        source_count = int(cast(Any, subject.get("source_topic_count") or 0))
        practice_count = int(cast(Any, subject.get("practice_topic_count") or 0))
        total_topics += topic_count
        if subject.get("mvp_status") != "mvp_ready":
            problems.append(f"{code}:not_mvp_ready")
        for key in ("route_ready", "rag_ready", "practice_ready"):
            if subject.get(key) is not True:
                problems.append(f"{code}:{key}_false")
        if topic_count <= 0:
            problems.append(f"{code}:no_topics")
        if not (topic_count == route_count == source_count == practice_count):
            problems.append(
                f"{code}:count_mismatch:topic={topic_count}:route={route_count}:source={source_count}:practice={practice_count}"
            )
    return {
        "ok": not problems,
        "subject_count": len(subjects),
        "total_topics": total_topics,
        "problems": problems,
    }


def _fetch_subjects(base_url: str, *, insecure: bool = False) -> list[dict[str, Any]]:
    context = ssl._create_unverified_context() if insecure else None
    with urllib.request.urlopen(f"{base_url.rstrip('/')}/api/v1/subjects", timeout=20, context=context) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise ValueError("subjects endpoint must return a list")
    return cast(list[dict[str, Any]], payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit production all-subject readiness")
    parser.add_argument("--base-url", default="https://192.168.1.86")
    parser.add_argument("--input-json")
    parser.add_argument("--insecure", action="store_true", help="Allow self-signed TLS for LAN checks")
    parser.add_argument("--expected-subject-count", type=int, default=12)
    args = parser.parse_args()
    if args.input_json:
        subjects = json.loads(open(args.input_json, encoding="utf-8").read())
        if not isinstance(subjects, list):
            raise ValueError("input JSON must be a list")
    else:
        subjects = _fetch_subjects(args.base_url, insecure=args.insecure)
    result = audit_subjects_payload(cast(list[dict[str, Any]], subjects), expected_subject_count=args.expected_subject_count)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
