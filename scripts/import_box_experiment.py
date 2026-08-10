#!/usr/bin/env python3
"""Append a verified Box test run to the experiment side of the website seed."""

from argparse import ArgumentParser
from copy import deepcopy
from pathlib import Path
import json


TEST_BASE_URL = "https://box.test.xdf.cn"
EXPECTED_COUNT = 12


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def compact_issues(deficiencies):
    severity_order = {"high": 0, "medium": 1, "low": 2}
    ordered = sorted(
        deficiencies or [],
        key=lambda item: severity_order.get(str(item.get("severity", "")).lower(), 3),
    )
    lines = []
    for item in ordered:
        description = str(item.get("description") or "").strip()
        if not description:
            continue
        severity = str(item.get("severity") or "未分级").upper()
        lines.append(f"[{severity}] {description}")
        if len(lines) == 4:
            break
    return "\n".join(lines)


def evaluation_summary(result):
    scores = result.get("scores") or {}
    return (
        f"AI四维评测：知识准确性 {scores.get('d1', '-')}，"
        f"教学适配性 {scores.get('d2', '-')}，"
        f"系统健壮性 {scores.get('d3', '-')}，"
        f"视觉美观度 {scores.get('d4', '-')}；"
        f"加权综合分 {result.get('composite', '-')}/5。"
    )


def main():
    parser = ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--seed-file", required=True)
    parser.add_argument("--version-id", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    seed_file = Path(args.seed_file).resolve()
    requests = load_json(run_dir / "requests.json")
    generation = load_json(run_dir / "generation-summary.json")
    evaluation = load_json(run_dir / "evaluation-summary.json")
    seed = load_json(seed_file)

    if len(requests) != EXPECTED_COUNT or len(seed.get("cases", [])) != EXPECTED_COUNT:
        raise SystemExit("The request list and website seed must both contain exactly 12 cases.")
    if generation.get("kpmBaseUrl") != TEST_BASE_URL:
        raise SystemExit("Only the Box test environment may be imported.")
    if generation.get("generationMethod") != "raw-user-requirement-only":
        raise SystemExit("Only raw user requirements may be imported.")
    if generation.get("successCount") != EXPECTED_COUNT or generation.get("finalResultCount") != EXPECTED_COUNT:
        raise SystemExit("Generation must have 12 complete preview and ZIP results.")
    if generation.get("publishedCount") != 0:
        raise SystemExit("Published runs cannot be imported into this experiment.")
    if evaluation.get("successCount") != EXPECTED_COUNT or evaluation.get("failureCount") != 0:
        raise SystemExit("Evaluation must succeed for all 12 cases.")

    generation_by_index = {int(item["index"]): item for item in generation["results"]}
    evaluation_by_index = {int(item["index"]): item for item in evaluation["results"]}
    request_by_index = {int(item["index"]): item for item in requests}
    baselines_before = [deepcopy(item.get("baseline")) for item in seed["cases"]]

    for case in seed["cases"]:
        index = int(case["index"])
        request = request_by_index[index]
        generated = generation_by_index[index]
        evaluated = evaluation_by_index[index]
        prompt = str(request["prompt"])

        if generated.get("prompt") != prompt or evaluated.get("prompt") != prompt:
            raise SystemExit(f"Prompt mismatch for case {index:02d}.")
        if not generated.get("fileUrl") or not generated.get("pushUrl"):
            raise SystemExit(f"Missing output URLs for case {index:02d}.")

        version = {
            "id": args.version_id,
            "label": args.label,
            "group": "实验组",
            "taskId": f"box_test_{index:02d}_{args.version_id}",
            "conversationId": generated.get("conversationId", ""),
            "fileUrl": generated["fileUrl"],
            "pushUrl": generated["pushUrl"],
            "fileName": generated.get("fileName", ""),
            "snapshotId": generated.get("snapshotId", ""),
            "finishedAt": generated.get("finishedAt", ""),
            "status": "success",
            "prompt": prompt,
            "promptType": "raw-user-requirement",
            "environment": TEST_BASE_URL,
            "generationMethod": "raw-user-requirement-only",
            "published": False,
            "evaluation": {
                "scores": evaluated.get("scores", {}),
                "composite": evaluated.get("composite"),
                "passed": evaluated.get("passed"),
                "priority": evaluated.get("priority"),
                "browserVerified": bool(evaluated.get("browserTest", {}).get("success")),
                "issues": compact_issues(evaluated.get("deficiencies", [])),
                "summary": evaluation_summary(evaluated),
                "decision": "todo",
            },
        }
        versions = [item for item in case.get("versions", []) if item.get("id") != args.version_id]
        versions.append(version)
        case["versions"] = versions

    if baselines_before != [item.get("baseline") for item in seed["cases"]]:
        raise SystemExit("Baseline data changed unexpectedly; import aborted.")

    seed["generatedAt"] = generation.get("generatedAt")
    seed["source"] = "Codex box-pipeline test run"
    seed["latestRun"] = {
        "environment": TEST_BASE_URL,
        "versionId": args.version_id,
        "label": args.label,
        "generatedCount": EXPECTED_COUNT,
        "evaluatedCount": EXPECTED_COUNT,
        "publishedCount": 0,
    }
    temp_file = seed_file.with_suffix(seed_file.suffix + ".tmp")
    temp_file.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp_file.replace(seed_file)
    print(f"Imported {EXPECTED_COUNT} experiment results as {args.label}; baselines unchanged.")


if __name__ == "__main__":
    main()
