#!/usr/bin/env python3
"""Build the website seed for the fixed 28-case generation test set."""

from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path
import json


TEST_BASE_URL = "https://box.test.xdf.cn"
PRODUCTION_BASE_URL = "https://box.xdf.cn"
EXPECTED_AUTOMATIC_COUNT = 28
EXPECTED_MANUAL_COUNT = 2


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def same_generated_result(left, right):
    fields = (
        "id",
        "conversationId",
        "fileUrl",
        "pushUrl",
        "snapshotId",
        "status",
        "environment",
    )
    return all(left.get(field, "") == right.get(field, "") for field in fields)


def append_version(previous_case, version):
    previous_versions = list((previous_case or {}).get("versions") or [])
    duplicate = next(
        (item for item in previous_versions if item.get("id") == version["id"]),
        None,
    )
    if duplicate:
        if not same_generated_result(duplicate, version):
            raise SystemExit(
                f"Version {version['id']} already exists with different generation results."
            )
        previous_versions = [
            item for item in previous_versions if item.get("id") != version["id"]
        ]
    previous_versions.append(version)
    return previous_versions


def parse_version_relabels(values):
    relabels = {}
    for value in values:
        version_id, separator, label = value.partition("=")
        version_id = version_id.strip()
        label = label.strip()
        if not separator or not version_id or not label:
            raise SystemExit(
                "--relabel-version must use VERSION_ID=DISPLAY_LABEL."
            )
        relabels[version_id] = label
    return relabels


def main():
    parser = ArgumentParser()
    parser.add_argument("--requests-file", required=True)
    parser.add_argument("--manual-requests-file", required=True)
    parser.add_argument("--generation-summary", required=True)
    parser.add_argument("--production-summary")
    parser.add_argument("--previous-seed")
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--version-id", default="box-test-v1.1-20260811")
    parser.add_argument("--version-label", default="测试环境 · 首次生成")
    parser.add_argument(
        "--relabel-version",
        action="append",
        default=[],
        help="Rename a preserved version label without changing its internal ID.",
    )
    args = parser.parse_args()

    test_set = load_json(Path(args.requests_file).resolve())
    manual_test_set = load_json(Path(args.manual_requests_file).resolve())
    generation = load_json(Path(args.generation_summary).resolve())
    production = load_json(Path(args.production_summary).resolve()) if args.production_summary else None
    previous_seed = load_json(Path(args.previous_seed).resolve()) if args.previous_seed else None
    version_relabels = parse_version_relabels(args.relabel_version)
    for previous_case in (previous_seed or {}).get("cases", []):
        for previous_version in previous_case.get("versions") or []:
            if previous_version.get("id") in version_relabels:
                previous_version["label"] = version_relabels[previous_version["id"]]
    cases = test_set.get("cases") or []
    manual_cases = manual_test_set.get("cases") or []
    if len(cases) != EXPECTED_AUTOMATIC_COUNT:
        raise SystemExit(f"Expected {EXPECTED_AUTOMATIC_COUNT} automatic cases.")
    if len(manual_cases) != EXPECTED_MANUAL_COUNT:
        raise SystemExit(f"Expected {EXPECTED_MANUAL_COUNT} manual cases.")
    if not manual_test_set.get("manualOnly") or not manual_test_set.get("doNotUseWithRegularSkill"):
        raise SystemExit("The manual test set must explicitly forbid regular skill execution.")
    if generation.get("kpmBaseUrl") != TEST_BASE_URL:
        raise SystemExit("Only Box test-environment results may be imported.")
    if generation.get("generationMethod") != "box-pipeline-generate-only":
        raise SystemExit("Only generate-only results may be imported.")
    if generation.get("evaluatedCount") != 0 or generation.get("publishedCount") != 0:
        raise SystemExit("Evaluated or published results cannot be imported for this run.")
    if (
        generation.get("successCount") != EXPECTED_AUTOMATIC_COUNT
        or generation.get("failureCount") != 0
        or generation.get("pendingCount") != 0
    ):
        raise SystemExit("The test-environment generation run must have 28 complete successes.")
    if production:
        if production.get("kpmBaseUrl") != PRODUCTION_BASE_URL:
            raise SystemExit("The production summary must come from Box production.")
        if production.get("generationMethod") not in {
            "box-pipeline-generate-only",
            "box-web-ui-generate-only",
        }:
            raise SystemExit("Only generate-only production results may be imported.")
        if production.get("evaluatedCount") != 0 or production.get("publishedCount") != 0:
            raise SystemExit("Evaluated or published production results cannot be imported.")

    results = {item["id"]: item for item in generation.get("results", [])}
    production_results = {item["id"]: item for item in (production or {}).get("results", [])}
    previous_cases = {
        item["id"]: item for item in (previous_seed or {}).get("cases", [])
    }
    output_cases = []
    for index, case in enumerate(cases, start=1):
        result = results.get(case["id"], {})
        if result and result.get("prompt") != case["prompt"]:
            raise SystemExit(f"Prompt mismatch for {case['id']}.")
        production_result = production_results.get(case["id"], {})
        if production_result and production_result.get("prompt") != case["prompt"]:
            raise SystemExit(f"Production prompt mismatch for {case['id']}.")
        test_variant = {
            "id": args.version_id,
            "label": args.version_label,
            "group": "固定测试集",
            "taskId": f"fixed_{case['id']}_{args.version_id}",
            "conversationId": result.get("conversationId", ""),
            "fileUrl": result.get("fileUrl", ""),
            "pushUrl": result.get("pushUrl", ""),
            "fileName": result.get("fileName", ""),
            "snapshotId": result.get("snapshotId", ""),
            "finishedAt": result.get("finishedAt", ""),
            "status": result.get("status", "pending"),
            "error": result.get("error", ""),
            "prompt": case["prompt"],
            "promptType": "raw-user-requirement",
            "environment": TEST_BASE_URL,
            "generationMethod": "box-pipeline-generate-only",
            "published": False,
            "evaluated": False,
        }
        previous_case = previous_cases.get(case["id"], {})
        if previous_case and previous_case.get("requirement") != case["prompt"]:
            raise SystemExit(f"Previous seed prompt mismatch for {case['id']}.")
        previous_baseline = previous_case.get("baseline") or {}
        if not production_result and previous_baseline.get("fileUrl"):
            production_result = previous_baseline
        output_cases.append({
            "id": case["id"],
            "index": index,
            "requirement": case["prompt"],
            "subject": case["subject"],
            "grade": case["grade"],
            "mainInteraction": case["interaction"],
            "keyChecks": case["keyChecks"],
            "generationMode": "automatic",
            "baseline": {
                "id": "baseline",
                "label": "线上现状" if production_result.get("fileUrl") else "线上现状 · 待补跑",
                "group": "正式环境" if production_result.get("fileUrl") else "线上占位",
                "status": production_result.get("status", "placeholder"),
                "conversationId": production_result.get("conversationId", ""),
                "fileUrl": production_result.get("fileUrl", ""),
                "pushUrl": production_result.get("pushUrl", ""),
                "fileName": production_result.get("fileName", ""),
                "snapshotId": production_result.get("snapshotId", ""),
                "finishedAt": production_result.get("finishedAt", ""),
                "error": production_result.get("error", ""),
                "prompt": case["prompt"],
                "promptType": "raw-user-requirement",
                "environment": PRODUCTION_BASE_URL,
                "published": False,
                "evaluated": False,
            },
            "versions": append_version(previous_case, test_variant),
        })

    for case in manual_cases:
        index = len(output_cases) + 1
        previous_case = previous_cases.get(case["id"])
        if previous_case:
            if previous_case.get("requirement") != case["prompt"]:
                raise SystemExit(f"Manual prompt mismatch for {case['id']}.")
            preserved_case = dict(previous_case)
            preserved_case["index"] = index
            output_cases.append(preserved_case)
            continue
        manual_variant = {
            "id": "manual-pending-v1.0",
            "label": "手动专项 · 待生成",
            "group": "手动专项",
            "taskId": f"manual_{case['id']}",
            "conversationId": "",
            "fileUrl": "",
            "pushUrl": "",
            "fileName": "",
            "snapshotId": "",
            "finishedAt": "",
            "status": "manual_pending",
            "error": "",
            "prompt": case["prompt"],
            "promptType": "raw-user-requirement",
            "environment": "manual-only",
            "generationMethod": "manual-only",
            "manualOnly": True,
            "published": False,
            "evaluated": False,
        }
        output_cases.append({
            "id": case["id"],
            "index": index,
            "requirement": case["prompt"],
            "subject": case["subject"],
            "grade": case["grade"],
            "mainInteraction": case.get("capability") or "音频与语音专项",
            "keyChecks": case["keyChecks"],
            "generationMode": "manual",
            "baseline": {
                "id": "baseline",
                "label": "线上现状 · 待补跑",
                "group": "线上占位",
                "status": "placeholder",
                "fileUrl": "",
                "pushUrl": "",
                "prompt": case["prompt"],
                "promptType": "raw-user-requirement",
                "environment": PRODUCTION_BASE_URL,
                "published": False,
                "evaluated": False,
            },
            "versions": [manual_variant],
        })

    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "schemaVersion": 2,
        "testSetId": test_set["testSetId"],
        "testSetVersion": test_set["version"],
        "manualTestSetId": manual_test_set["testSetId"],
        "manualTestSetVersion": manual_test_set["version"],
        "generatedAt": generated_at,
        "source": "Fixed 28-case Box test and production generation" if production else "Fixed 28-case Box test generation",
        "runPolicy": {
            "environment": TEST_BASE_URL,
            "generatedOnly": True,
            "evaluated": False,
            "published": False,
            "productionBaselineStatus": "generated" if production and production.get("successCount") == EXPECTED_AUTOMATIC_COUNT else "partial" if production else "placeholder",
            "productionGeneratedCount": production.get("successCount", 0) if production else 0,
            "automaticCaseCount": EXPECTED_AUTOMATIC_COUNT,
            "manualCaseCount": EXPECTED_MANUAL_COUNT,
            "manualCasesGenerated": False,
        },
        "cases": output_cases,
    }
    output_path = Path(args.output_file).resolve()
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(output_path)
    print(
        f"Built {len(output_cases)} cases: "
        f"test success={generation.get('successCount', 0)}, "
        f"manual pending={EXPECTED_MANUAL_COUNT}, "
        f"production generated={production.get('successCount', 0) if production else 0}, "
        f"production placeholders={EXPECTED_MANUAL_COUNT + (EXPECTED_AUTOMATIC_COUNT - (production.get('successCount', 0) if production else 0))}, "
        "evaluations=0."
    )


if __name__ == "__main__":
    main()
