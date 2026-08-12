#!/usr/bin/env python3
"""Run a fixed Box test set through generate.py with resumable progress."""

from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
import json
import os
import re
import subprocess
import sys


TEST_BASE_URL = "https://box.test.xdf.cn"
PRODUCTION_BASE_URL = "https://box.xdf.cn"
EXPECTED_COUNT = 28
GENERATE_MARKER = "GENERATE_RESULT:"
CONVERSATION_LINE = re.compile(r"(?:会话ID|conversationId)\s*[:：]\s*([A-Za-z0-9_-]{12,})")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, payload):
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)


def parse_generate_result(output):
    for line in reversed(output.splitlines()):
        if GENERATE_MARKER not in line:
            continue
        raw = line.split(GENERATE_MARKER, 1)[1].strip()
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return {"error": "invalid_generate_result"}
        return value if isinstance(value, dict) else {"error": "invalid_generate_result"}
    conversation_matches = CONVERSATION_LINE.findall(output)
    return {
        "error": "missing_generate_result",
        "conversationId": conversation_matches[-1] if conversation_matches else "",
    }


def run_case(
    case,
    index,
    skill_dir,
    output_dir,
    base_url,
):
    case_dir = output_dir / case["id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["KPM_BASE_URL"] = base_url
    env["BOX_CREATE_MAX_ATTEMPTS"] = "1"
    wrapper = (
        "import json,sys;"
        "sys.path.insert(0,sys.argv[1]);"
        "from generate import generate;"
        "result=generate(sys.argv[2],sys.argv[3]);"
        f"print('{GENERATE_MARKER}'+json.dumps(result,ensure_ascii=False));"
        "raise SystemExit(0 if result.get('fileUrl') and result.get('pushUrl') else 1)"
    )
    command = [
        sys.executable,
        "-c",
        wrapper,
        str(skill_dir / "scripts"),
        case["prompt"],
        str(case_dir),
    ]
    command_cwd = skill_dir
    started_at = now_iso()
    try:
        completed = subprocess.run(
            command,
            cwd=str(command_cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=2400,
            check=False,
        )
        output = "\n".join(part for part in [completed.stdout, completed.stderr] if part)
        (case_dir / "generation.log").write_text(output, encoding="utf-8")
        generated = parse_generate_result(output)
        success = bool(generated.get("fileUrl") and generated.get("pushUrl"))
        error = "" if success else str(generated.get("error") or f"exit_code_{completed.returncode}")
    except subprocess.TimeoutExpired as exc:
        output = "\n".join(
            part.decode("utf-8", errors="replace") if isinstance(part, bytes) else str(part or "")
            for part in [exc.stdout, exc.stderr]
        )
        (case_dir / "generation.log").write_text(output, encoding="utf-8")
        generated = {}
        success = False
        error = "timeout_after_2400_seconds"

    return {
        "id": case["id"],
        "index": index,
        "prompt": case["prompt"],
        "subject": case["subject"],
        "grade": case["grade"],
        "interaction": case["interaction"],
        "keyChecks": case["keyChecks"],
        "status": "success" if success else "failed",
        "error": error,
        "conversationId": generated.get("conversationId") or "",
        "fileUrl": generated.get("fileUrl") or "",
        "pushUrl": generated.get("pushUrl") or "",
        "fileName": generated.get("fileName") or "",
        "snapshotId": generated.get("snapshotId") or "",
        "startedAt": started_at,
        "finishedAt": now_iso(),
        "published": False,
        "evaluated": False,
    }


def build_summary(test_set, results, base_url, started_at, generation_method):
    ordered = sorted(results, key=lambda item: item["index"])
    return {
        "testSetId": test_set["testSetId"],
        "testSetVersion": test_set["version"],
        "generatedAt": started_at,
        "updatedAt": now_iso(),
        "kpmBaseUrl": base_url,
        "generationMethod": generation_method,
        "requestedCount": len(test_set["cases"]),
        "successCount": sum(item["status"] == "success" for item in ordered),
        "failureCount": sum(item["status"] == "failed" for item in ordered),
        "pendingCount": len(test_set["cases"]) - len(ordered),
        "evaluatedCount": 0,
        "publishedCount": 0,
        "results": ordered,
    }


def main():
    parser = ArgumentParser()
    parser.add_argument("--requests-file", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--skill-dir",
        default="/Users/jolin/.codex/skills/box-pipeline",
    )
    parser.add_argument("--base-url", default=TEST_BASE_URL)
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Required when --base-url points to the Box production environment.",
    )
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument(
        "--case-id",
        action="append",
        default=[],
        help="Run only the specified case ID. May be repeated; completed results remain resumable.",
    )
    args = parser.parse_args()

    requests_file = Path(args.requests_file).resolve()
    output_dir = Path(args.output_dir).resolve()
    skill_dir = Path(args.skill_dir).resolve()
    base_url = args.base_url.rstrip("/")
    if base_url not in {TEST_BASE_URL, PRODUCTION_BASE_URL}:
        raise SystemExit("Only the configured Box test and production environments are accepted.")
    if base_url == PRODUCTION_BASE_URL and not args.allow_production:
        raise SystemExit("Production generation requires --allow-production.")
    generation_method = "box-pipeline-generate-only"

    test_set = load_json(requests_file)
    cases = test_set.get("cases") or []
    policy = test_set.get("executionPolicy") or {}
    if len(cases) != EXPECTED_COUNT:
        raise SystemExit(f"Expected {EXPECTED_COUNT} fixed cases, got {len(cases)}.")
    if policy.get("mode") != "generate-only" or any(
        policy.get(key) for key in ("evaluate", "iterate", "publish")
    ):
        raise SystemExit("The fixed set must be configured as generate-only.")
    selected_case_ids = set(args.case_id)
    known_case_ids = {case["id"] for case in cases}
    unknown_case_ids = selected_case_ids - known_case_ids
    if unknown_case_ids:
        raise SystemExit(f"Unknown case IDs: {', '.join(sorted(unknown_case_ids))}")

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "requests.json").write_text(
        json.dumps(test_set, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary_path = output_dir / "generation-summary.json"
    existing = load_json(summary_path) if summary_path.exists() else {}
    started_at = existing.get("generatedAt") or now_iso()
    existing_results = existing.get("results", [])
    results_by_id = {item["id"]: item for item in existing_results}
    pending = [
        (index, case)
        for index, case in enumerate(cases, start=1)
        if not (
            results_by_id.get(case["id"], {}).get("status") == "success"
            and results_by_id.get(case["id"], {}).get("fileUrl")
            and results_by_id.get(case["id"], {}).get("pushUrl")
        )
        and (not selected_case_ids or case["id"] in selected_case_ids)
    ]
    lock = Lock()

    def persist():
        summary = build_summary(
            test_set,
            list(results_by_id.values()),
            base_url,
            started_at,
            generation_method,
        )
        write_json(summary_path, summary)
        return summary

    persist()
    print(f"Fixed generation: {len(results_by_id)} complete, {len(pending)} pending")
    if pending:
        preflight_index, preflight_case = pending.pop(0)
        preflight_result = run_case(
            preflight_case,
            preflight_index,
            skill_dir,
            output_dir,
            base_url,
        )
        with lock:
            results_by_id[preflight_result["id"]] = preflight_result
            summary = persist()
        print(
            f"[{preflight_result['id']}] {preflight_result['status']} | "
            f"success={summary['successCount']} failed={summary['failureCount']} "
            f"pending={summary['pendingCount']}",
            flush=True,
        )
        if preflight_result["status"] != "success":
            print("Preflight generation failed; remaining cases were not started.")
            raise SystemExit(2)

    if pending:
        with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 3))) as executor:
            futures = {
                executor.submit(
                    run_case,
                    case,
                    index,
                    skill_dir,
                    output_dir,
                    base_url,
                ): case["id"]
                for index, case in pending
            }
            for future in as_completed(futures):
                result = future.result()
                with lock:
                    results_by_id[result["id"]] = result
                    summary = persist()
                print(
                    f"[{result['id']}] {result['status']} | "
                    f"success={summary['successCount']} failed={summary['failureCount']} "
                    f"pending={summary['pendingCount']}",
                    flush=True,
                )

    summary = persist()
    print("BATCH_GENERATION_RESULT:" + json.dumps(summary, ensure_ascii=False))
    if selected_case_ids:
        successful_ids = {
            item["id"]
            for item in summary["results"]
            if item.get("status") == "success"
        }
        if not selected_case_ids.issubset(successful_ids):
            raise SystemExit(2)
    elif summary["successCount"] != EXPECTED_COUNT:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
