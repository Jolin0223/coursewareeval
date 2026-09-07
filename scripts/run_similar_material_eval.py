#!/usr/bin/env python3
"""Run the fixed 30-query similar-courseware evaluation set.

The script intentionally writes only evaluation-safe data to the repository.
Teacher names and email addresses stay in the source files and are represented
by opaque references in the public seed. A protected attribution API can map
those references for authenticated users without exposing PII in static assets.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


DEFAULT_ENDPOINT = "/kpm-api/tool/similar-materials"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Top6 similar-courseware evaluation")
    parser.add_argument("--query-source", type=Path, required=True, help="annotated_cases.json containing case_rows")
    parser.add_argument("--resource-inventory", type=Path, required=True, help="published resource CSV used to map snapshot_id to material_id")
    parser.add_argument("--snapshot-inventory", type=Path, help="optional raw kpm_snapshot.csv used to fill historical snapshot mappings")
    parser.add_argument("--conversation-inventory", type=Path, help="optional kpm_conversation.csv used to resolve publisher references")
    parser.add_argument("--output", type=Path, default=Path("data/similar-material-eval-seed.json"))
    parser.add_argument(
        "--attribution-output",
        type=Path,
        help="optional protected teacher-attribution JSON; must point outside the repository",
    )
    parser.add_argument("--env-file", type=Path, default=Path.home() / ".config/box-pipeline/.env")
    parser.add_argument("--version-id", default="v1")
    parser.add_argument("--version-label", default="V1 第一版算法")
    parser.add_argument("--algorithm-note", default="RAG 相似课件推荐接口第一版")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--delay", type=float, default=0.25)
    return parser.parse_args()


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


OPAQUE_REF_MAPS: dict[str, dict[str, str]] = {}


def seed_opaque_refs(prefix: str, values: list[str]) -> None:
    registry = OPAQUE_REF_MAPS.setdefault(prefix, {})
    for value in sorted({item.strip().lower() for item in values if item.strip()}):
        if value not in registry:
            registry[value] = f"{prefix}-{len(registry) + 1:04d}"


def opaque_ref(prefix: str, value: str) -> str:
    if not value:
        return ""
    normalized = value.strip().lower()
    registry = OPAQUE_REF_MAPS.setdefault(prefix, {})
    if normalized not in registry:
        registry[normalized] = f"{prefix}-{len(registry) + 1:04d}"
    return registry[normalized]


def load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("case_rows") if isinstance(payload, dict) else payload
    if not isinstance(cases, list):
        raise ValueError("query source must contain a case_rows array")
    if len(cases) != 30:
        raise ValueError(f"expected exactly 30 queries, got {len(cases)}")
    subject_counts = Counter(str(item.get("subject") or "") for item in cases)
    expected = {"语文": 10, "数学": 10, "英语": 10}
    if subject_counts != expected:
        raise ValueError(f"subject distribution must be {expected}, got {dict(subject_counts)}")
    return cases


def load_resource_index(path: Path, snapshot_path: Path | None = None) -> tuple[dict[str, dict[str, str]], str]:
    index: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            for field in ("current_effective_snapshot_id", "first_publish_snapshot_id"):
                snapshot_id = str(row.get(field) or "").strip()
                if snapshot_id and snapshot_id not in index:
                    index[snapshot_id] = row
    if snapshot_path:
        with snapshot_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                snapshot_id = str(row.get("snapshot_id") or "").strip()
                if not snapshot_id:
                    continue
                if snapshot_id not in index:
                    index[snapshot_id] = {
                        **row,
                        "current_effective_snapshot_id": snapshot_id,
                        "first_publish_snapshot_id": snapshot_id,
                        "resource_name": row.get("resource_name") or "",
                        "subject_name": row.get("subject_name") or row.get("subject") or "",
                        "grade_name": row.get("grade_name") or row.get("grade") or "",
                        "source_material_id": "",
                        "publisher_email": "",
                        "publisher_name": "",
                    }
    inventory_dates = [path.stat().st_mtime]
    if snapshot_path:
        inventory_dates.append(snapshot_path.stat().st_mtime)
    as_of = datetime.fromtimestamp(max(inventory_dates), tz=timezone.utc).astimezone().date().isoformat()
    return index, as_of


def load_conversation_publishers(path: Path | None) -> dict[str, str]:
    if not path:
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {
            str(row.get("conversation_id") or "").strip(): str(row.get("user_email") or "").strip()
            for row in csv.DictReader(handle)
            if str(row.get("conversation_id") or "").strip()
        }


def request_results(
    session: requests.Session,
    url: str,
    query: str,
    headers: dict[str, str],
    timeout: float,
    max_attempts: int,
) -> tuple[list[dict[str, Any]], int]:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        started = time.perf_counter()
        try:
            response = session.post(url, headers=headers, json={"description": query}, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") != 200 or not isinstance(payload.get("data"), list):
                raise RuntimeError(f"business response code={payload.get('code')} message={payload.get('message') or payload.get('msg')}")
            results = payload["data"][:6]
            if len(results) != 6:
                raise RuntimeError(f"expected 6 results, got {len(results)}")
            cost_ms = int(payload.get("cost") or round((time.perf_counter() - started) * 1000))
            return results, cost_ms
        except Exception as error:  # noqa: BLE001 - retry boundary
            last_error = error
            if attempt < max_attempts:
                time.sleep(min(2 ** (attempt - 1), 4))
    raise RuntimeError(f"similar-materials request failed after {max_attempts} attempts: {last_error}")


def normalize_result(
    item: dict[str, Any],
    inventory: dict[str, dict[str, str]],
    conversation_publishers: dict[str, str],
    rank: int,
) -> dict[str, Any]:
    snapshot_id = str(item.get("snapshotId") or "").strip()
    resource = inventory.get(snapshot_id) or {}
    conversation_id = str(resource.get("conversation_id") or "").strip()
    publisher_value = str(
        resource.get("publisher_email")
        or conversation_publishers.get(conversation_id)
        or resource.get("publisher_name")
        or ""
    ).strip()
    family_value = str(
        resource.get("source_material_id")
        or resource.get("conversation_id")
        or resource.get("material_id")
        or snapshot_id
    ).strip()
    return {
        "rank": rank,
        "snapshotId": snapshot_id,
        "materialId": str(resource.get("material_id") or "").strip(),
        "resourceName": str(item.get("resourceName") or resource.get("resource_name") or "未命名课件").strip(),
        "description": str(item.get("description") or "").strip(),
        "subject": str(item.get("subjectName") or resource.get("subject_name") or "未说明").strip(),
        "grade": str(item.get("gradeName") or resource.get("grade_name") or "未说明").strip(),
        "score": round(float(item.get("score") or 0), 8),
        "previewUrl": str(item.get("pushUrl") or "").strip(),
        "publisherRef": opaque_ref("teacher", publisher_value),
        "publisherAttributionStatus": "matched-protected" if publisher_value else "unmatched",
        "familyKey": family_value,
        "materialMappingStatus": "matched" if resource.get("material_id") else "unmatched",
        "snapshotPublishStatus": str(resource.get("pub_status") or resource.get("latest_publish_snapshot_pub_status") or "").strip(),
    }


def add_family_labels(results: list[dict[str, Any]]) -> None:
    counts = Counter(item.get("familyKey") for item in results if item.get("familyKey"))
    family_order: dict[str, str] = {}
    for item in results:
        key = str(item.get("familyKey") or "")
        if key not in family_order:
            family_order[key] = f"F{len(family_order) + 1:02d}"
        item["familyRef"] = family_order[key]
        item["sameFamilyCount"] = counts.get(key, 1)
        item.pop("familyKey", None)


def build_case(case: dict[str, Any], version_id: str, results: list[dict[str, Any]], cost_ms: int) -> dict[str, Any]:
    teacher_value = str(case.get("teacher_email") or case.get("teacher_name") or "").strip()
    return {
        "id": str(case.get("case_id") or "").strip(),
        "subject": str(case.get("subject") or "未说明").strip(),
        "grade": str(case.get("query_grade") or "未说明").strip(),
        "category": str(case.get("category") or "").strip(),
        "query": str(case.get("query_text") or "").strip(),
        "queryMessageId": str(case.get("message_id") or "").strip(),
        "queryConversationId": str(case.get("query_conversation_id") or "").strip(),
        "queryTeacherRef": opaque_ref("teacher", teacher_value),
        "queryTeacherAttributionStatus": "matched-protected" if teacher_value else "unmatched",
        "runs": {
            version_id: {
                "costMs": cost_ms,
                "resultCount": len(results),
                "results": results,
            }
        },
    }


def merge_dataset(output: Path, version: dict[str, Any], new_cases: list[dict[str, Any]], inventory_as_of: str) -> dict[str, Any]:
    if output.exists():
        dataset = json.loads(output.read_text(encoding="utf-8"))
    else:
        dataset = {"schemaVersion": 1, "versions": [], "cases": []}

    version_id = version["id"]
    versions = [item for item in dataset.get("versions", []) if item.get("id") != version_id]
    versions.append(version)

    old_by_id = {item.get("id"): item for item in dataset.get("cases", [])}
    merged_cases: list[dict[str, Any]] = []
    for new_case in new_cases:
        existing = old_by_id.get(new_case["id"], {})
        merged = {
            **existing,
            **{key: value for key, value in new_case.items() if key != "runs"},
            "runs": {**existing.get("runs", {}), **new_case.get("runs", {})},
        }
        merged_cases.append(merged)

    generated_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    return {
        "schemaVersion": 1,
        "testSetId": "similar-courseware-recommendation-30",
        "generatedAt": generated_at,
        "latestVersionId": version_id,
        "source": {
            "endpoint": "box.test.xdf.cn /kpm-api/tool/similar-materials",
            "resultLimit": 6,
            "resourceInventoryAsOf": inventory_as_of,
            "attributionPolicy": "Teacher identities are resolved only by a protected authenticated data source; static seed stores opaque references.",
        },
        "versions": versions,
        "cases": merged_cases,
    }


def build_attribution_payload(
    dataset: dict[str, Any],
    source_cases: list[dict[str, Any]],
    inventory: dict[str, dict[str, str]],
    conversation_publishers: dict[str, str],
) -> dict[str, dict[str, dict[str, str]]]:
    source_by_id = {str(item.get("case_id") or "").strip(): item for item in source_cases}
    query_teachers: dict[str, dict[str, str]] = {}
    publishers: dict[str, dict[str, str]] = {}

    for case in dataset.get("cases", []):
        source = source_by_id.get(str(case.get("id") or "").strip(), {})
        teacher_ref = str(case.get("queryTeacherRef") or "").strip()
        teacher_name = str(source.get("teacher_name") or source.get("teacher_email") or "").strip()
        if teacher_ref and teacher_name:
            query_teachers[teacher_ref] = {"name": teacher_name}

        for run in (case.get("runs") or {}).values():
            for result in run.get("results") or []:
                publisher_ref = str(result.get("publisherRef") or "").strip()
                resource = inventory.get(str(result.get("snapshotId") or "").strip()) or {}
                conversation_id = str(resource.get("conversation_id") or "").strip()
                publisher_name = str(
                    resource.get("publisher_name")
                    or resource.get("publisher_email")
                    or conversation_publishers.get(conversation_id)
                    or ""
                ).strip()
                if publisher_ref and publisher_name:
                    publishers[publisher_ref] = {"name": publisher_name}

    return {"queryTeachers": query_teachers, "publishers": publishers}


def main() -> int:
    args = parse_args()
    attribution_target = args.attribution_output.resolve() if args.attribution_output else None
    repository_root = Path.cwd().resolve()
    if attribution_target and (attribution_target == repository_root or repository_root in attribution_target.parents):
        raise RuntimeError("protected attribution output must stay outside the repository")
    config = load_env(args.env_file)
    e2e = config.get("KPM_E2E_COOKIE", "").strip()
    e2mf = config.get("KPM_E2MF_COOKIE", "").strip()
    if not e2e or not e2mf:
        raise RuntimeError("KPM_E2E_COOKIE and KPM_E2MF_COOKIE are required")

    base_url = (config.get("KPM_BASE_URL") or config.get("BOX_API_BASE") or "https://box.test.xdf.cn").rstrip("/")
    endpoint_url = f"{base_url}{DEFAULT_ENDPOINT}"
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
        "Cookie": f"e2e={e2e}; e2mf={e2mf}",
    }
    cases = load_cases(args.query_source)
    inventory, inventory_as_of = load_resource_index(args.resource_inventory, args.snapshot_inventory)
    conversation_publishers = load_conversation_publishers(args.conversation_inventory)
    seed_opaque_refs("teacher", [
        *[str(item.get("teacher_email") or item.get("teacher_name") or "") for item in cases],
        *conversation_publishers.values(),
    ])

    session = requests.Session()
    completed: list[dict[str, Any]] = []
    run_started = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    for index, case in enumerate(cases, start=1):
        case_id = str(case.get("case_id") or f"Q{index:02d}")
        print(f"[{index:02d}/30] {case_id} {case.get('subject')}...", flush=True)
        raw_results, cost_ms = request_results(
            session,
            endpoint_url,
            str(case.get("query_text") or ""),
            headers,
            args.timeout,
            args.max_attempts,
        )
        results = [
            normalize_result(item, inventory, conversation_publishers, rank)
            for rank, item in enumerate(raw_results, start=1)
        ]
        add_family_labels(results)
        completed.append(build_case(case, args.version_id, results, cost_ms))
        if args.delay > 0:
            time.sleep(args.delay)

    version = {
        "id": args.version_id,
        "label": args.version_label,
        "algorithmNote": args.algorithm_note,
        "runAt": run_started,
        "queryCount": len(completed),
        "resultCount": sum(len(item["runs"][args.version_id]["results"]) for item in completed),
        "status": "complete",
    }
    dataset = merge_dataset(args.output, version, completed, inventory_as_of)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if attribution_target:
        attribution = build_attribution_payload(dataset, cases, inventory, conversation_publishers)
        attribution_target.parent.mkdir(parents=True, exist_ok=True)
        attribution_target.write_text(json.dumps(attribution, ensure_ascii=False) + "\n", encoding="utf-8")
        attribution_target.chmod(0o600)
        print(
            "Protected attribution prepared: "
            f"{len(attribution['queryTeachers'])} query teachers / {len(attribution['publishers'])} publishers"
        )
    print(f"Completed {version['queryCount']} queries / {version['resultCount']} results -> {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        raise SystemExit(130)
    except Exception as error:  # noqa: BLE001 - command line boundary
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
