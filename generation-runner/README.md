# Courseware Generation Runner

`material-design` from KPM returns `566` when called from Cloudflare Worker, while the same request succeeds from a normal Python runtime. This runner keeps the website UI unchanged and moves the KPM generation chain to a non-Cloudflare environment.

## Environment

Required:

```bash
export KPM_APP_SECRET="replace-with-real-secret"
```

Optional:

```bash
export KPM_APP_ID="kpm-api"
export KPM_BASE_URL="https://box.xdf.cn"
export HOST="127.0.0.1"
export PORT="8789"
export GENERATION_RUNNER_TOKEN="shared-token-between-worker-and-runner"
```

## Run

```bash
python3 generation-runner/server.py
```

Or create `generation-runner/.env` from `.env.example`, fill `KPM_APP_SECRET`, then run:

```bash
bash generation-runner/start-local.sh
```

Health check:

```bash
curl http://127.0.0.1:8789/health
```

## Local Website Button Mode

For fast testing, open the preview website and keep this runner running on the same Mac. The page will first try:

```text
http://127.0.0.1:8789/api/generation-eval/run-prompt-version
```

If the local runner is reachable, the website button uses it directly and avoids Cloudflare Worker calling KPM.

Default allowed browser origins:

```text
https://coursewareeval.chenjialing.cn
https://codex-generation-prompt-eval.courseware-eval.pages.dev
```

To add more preview domains:

```bash
export GENERATION_RUNNER_ALLOWED_ORIGINS="https://coursewareeval.chenjialing.cn,https://codex-generation-prompt-eval.courseware-eval.pages.dev"
```

## Connect Cloudflare Worker

Configure these variables in the Cloudflare Pages test environment:

```bash
GENERATION_RUNNER_URL=https://your-runner-domain.example.com
GENERATION_RUNNER_TOKEN=shared-token-between-worker-and-runner
```

After that, the existing website button still calls:

```text
/api/generation-eval/run-prompt-version
```

The Worker validates the admin user first, then proxies the generation stream to this runner.
