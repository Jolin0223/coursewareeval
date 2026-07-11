#!/usr/bin/env python3
"""Small KPM generation runner for coursewareeval.

The Cloudflare Worker cannot reliably call KPM material-design from its edge
network. This runner keeps the website API shape the same while executing the
KPM generation chain from a normal Python network environment.
"""

from __future__ import annotations

import base64
import hmac
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from hashlib import sha1
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable


APP_ID = os.environ.get("KPM_APP_ID", "kpm-api").strip() or "kpm-api"
APP_SECRET = os.environ.get("KPM_APP_SECRET", "").strip()
KPM_BASE_URL = os.environ.get("KPM_BASE_URL", "https://box.xdf.cn").strip().rstrip("/")
RUNNER_TOKEN = os.environ.get("GENERATION_RUNNER_TOKEN", "").strip()
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8789"))
DESIGN_TIMEOUT_SECONDS = int(os.environ.get("MATERIAL_DESIGN_TIMEOUT_SECONDS", "600"))
CREATE_TIMEOUT_SECONDS = int(os.environ.get("MATERIAL_CREATE_TIMEOUT_SECONDS", "1800"))


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def build_design_content(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"【测评用例】{payload.get('caseName') or '课件生成效果测评'}",
            "",
            "【用户需求】",
            str(payload.get("userRequirement") or "").strip(),
            "",
            f"【本次测评的系统提示词版本】{payload.get('versionLabel') or ''}",
            str(payload.get("systemPrompt") or "").strip(),
            "",
            "【生成要求】",
            "请严格基于以上用户需求和本次测评的系统提示词版本生成一个可运行的互动课件。优先保证知识准确、教学适配、交互稳定和视觉完整。不要在成品中展示本段测评说明。",
        ]
    )


def generate_sign(timestamp: str) -> str:
    raw = timestamp + APP_SECRET
    digest = hmac.new(APP_SECRET.encode("utf-8"), raw.encode("utf-8"), sha1).digest()
    return base64.b64encode(digest).decode("utf-8")


def build_kpm_headers() -> dict[str, str]:
    if not APP_SECRET:
        raise RuntimeError("Missing environment variable: KPM_APP_SECRET")
    timestamp = str(int(time.time()))
    return {
        "X-App-Id": APP_ID,
        "X-Sign": generate_sign(timestamp),
        "X-Timestamp": timestamp,
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "text/event-stream; charset=utf-8",
        "User-Agent": "python-requests/2.32.3",
    }


def parse_sse_payload(line: str) -> dict[str, Any] | None:
    text = line.strip()
    if not text:
        return None
    if text.startswith("data:"):
        text = text[5:].strip()
    if not text or text == "[DONE]":
        return None
    try:
        event = json.loads(text)
    except json.JSONDecodeError:
        return None
    nested = event.get("text")
    if isinstance(nested, str):
        try:
            event["text"] = json.loads(nested)
        except json.JSONDecodeError:
            pass
    return event


def post_kpm_stream(
    path: str,
    payload: dict[str, Any],
    timeout_seconds: int,
    on_event: Callable[[dict[str, Any], int], None],
    stop_on_final: bool,
) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{KPM_BASE_URL}{path}",
        data=body,
        headers=build_kpm_headers(),
        method="POST",
    )
    context = ssl.create_default_context()
    conversation_id = ""
    final_result = None
    step_count = 0
    last_step_name = ""
    started = time.time()

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds, context=context) as response:
            for raw_line in response:
                if time.time() - started > timeout_seconds:
                    return {
                        "conversationId": conversation_id,
                        "finalResult": final_result,
                        "stepCount": step_count,
                        "lastStepName": last_step_name,
                        "timedOut": True,
                    }
                line = raw_line.decode("utf-8", errors="replace").strip()
                event = parse_sse_payload(line)
                if not event:
                    continue
                if event.get("code") and event.get("msg") and "text" not in event:
                    raise RuntimeError(f"KPM 接口业务错误 {event.get('code')}：{event.get('msg')}")
                conversation_id = event.get("conversationId") or conversation_id
                text = event.get("text")
                if isinstance(text, dict):
                    last_step_name = text.get("stepName") or last_step_name
                    final_result = text.get("finalResult") or final_result
                step_count += 1
                on_event(event, step_count)
                if stop_on_final and final_result:
                    break
    except urllib.error.HTTPError as error:
        preview = error.read(300).decode("utf-8", errors="replace").replace("\n", " ")
        raise RuntimeError(f"KPM 接口返回 {error.code}：{preview}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"KPM 接口连接失败：{error.reason}") from error

    return {
        "conversationId": conversation_id,
        "finalResult": final_result,
        "stepCount": step_count,
        "lastStepName": last_step_name,
        "timedOut": False,
    }


class RunnerHandler(BaseHTTPRequestHandler):
    server_version = "coursewareeval-generation-runner/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,X-Runner-Token")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_json({"ok": False, "message": "Not found"}, 404)
            return
        self.send_json(
            {
                "ok": True,
                "service": "coursewareeval-generation-runner",
                "kpmBaseUrl": KPM_BASE_URL,
                "hasKpmAppSecret": bool(APP_SECRET),
                "hasRunnerToken": bool(RUNNER_TOKEN),
            },
            200,
        )

    def do_POST(self) -> None:
        if self.path != "/api/generation-eval/run-prompt-version":
            self.send_json({"ok": False, "message": "Not found"}, 404)
            return
        if RUNNER_TOKEN and self.headers.get("X-Runner-Token", "") != RUNNER_TOKEN:
            self.send_json({"ok": False, "message": "Runner token invalid."}, 401)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except Exception as error:
            self.send_json({"ok": False, "message": f"请求体解析失败：{error}"}, 400)
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_cors_headers()
        self.end_headers()
        self.run_generation(payload)

    def send_json(self, payload: dict[str, Any], status: int) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def write_event(self, payload: dict[str, Any]) -> None:
        payload = {**payload, "runner": "python", "updatedAt": now_iso()}
        self.wfile.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
        self.wfile.flush()

    def run_generation(self, payload: dict[str, Any]) -> None:
        conversation_id = ""
        try:
            user_requirement = str(payload.get("userRequirement") or "").strip()
            system_prompt = str(payload.get("systemPrompt") or "").strip()
            if not user_requirement:
                raise RuntimeError("请先填写用户需求。")
            if not system_prompt:
                raise RuntimeError("请先填写系统提示词。")

            self.write_event({"ok": True, "status": "designing", "message": "runner 正在调用方案设计接口。"})
            design_content = build_design_content(payload)

            def on_design(event: dict[str, Any], step_count: int) -> None:
                nonlocal conversation_id
                conversation_id = event.get("conversationId") or conversation_id
                self.write_event(
                    {
                        "ok": True,
                        "status": "designing",
                        "conversationId": conversation_id,
                        "stepCount": step_count,
                        "message": "方案设计接口正在返回方案内容。",
                    }
                )

            design_result = post_kpm_stream(
                "/kpm-api/skill/material-design",
                {"content": design_content},
                DESIGN_TIMEOUT_SECONDS,
                on_design,
                stop_on_final=False,
            )
            conversation_id = design_result.get("conversationId") or conversation_id
            if not conversation_id:
                raise RuntimeError("方案设计接口没有返回 conversationId，无法继续创建课件。")
            if design_result.get("timedOut"):
                raise RuntimeError(f"方案设计超过 {DESIGN_TIMEOUT_SECONDS} 秒仍未结束。")

            self.write_event(
                {
                    "ok": True,
                    "status": "creating",
                    "conversationId": conversation_id,
                    "message": "方案设计完成，runner 正在调用素材创建接口。",
                }
            )

            def on_create(event: dict[str, Any], step_count: int) -> None:
                text = event.get("text") if isinstance(event.get("text"), dict) else {}
                final_result = text.get("finalResult") if isinstance(text, dict) else None
                self.write_event(
                    {
                        "ok": True,
                        "status": "done" if final_result else "progress",
                        "conversationId": conversation_id,
                        "stepCount": step_count,
                        "stepName": text.get("stepName") or "",
                        "stepType": text.get("stepType"),
                        "finalResult": final_result,
                        "fileUrl": (final_result or {}).get("fileUrl", ""),
                        "pushUrl": (final_result or {}).get("pushUrl", ""),
                        "snapshotId": (final_result or {}).get("snapshotId", ""),
                        "filePath": (final_result or {}).get("filePath", ""),
                        "message": "素材创建完成，预览链接已回填。" if final_result else f"素材创建进度：{text.get('stepName') or '处理中'}",
                    }
                )

            create_result = post_kpm_stream(
                "/kpm-api/skill/material-create",
                {"conversationId": conversation_id},
                CREATE_TIMEOUT_SECONDS,
                on_create,
                stop_on_final=True,
            )
            if create_result.get("timedOut") and not create_result.get("finalResult"):
                self.write_event(
                    {
                        "ok": False,
                        "status": "timeout",
                        "conversationId": conversation_id,
                        "stepCount": create_result.get("stepCount", 0),
                        "lastStepName": create_result.get("lastStepName", ""),
                        "message": f"素材创建仍在上游处理中，{CREATE_TIMEOUT_SECONDS} 秒内未收到最终完成信号。",
                    }
                )
            elif not create_result.get("finalResult"):
                raise RuntimeError("素材创建流程结束，但没有返回最终预览链接。")
        except Exception as error:
            self.write_event(
                {
                    "ok": False,
                    "status": "failed",
                    "conversationId": conversation_id,
                    "message": f"课件生成没有完成（generation-runner）：{error}",
                }
            )


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), RunnerHandler)
    print(f"coursewareeval generation runner listening on http://{HOST}:{PORT}")
    print(f"KPM base URL: {KPM_BASE_URL}")
    server.serve_forever()


if __name__ == "__main__":
    main()
