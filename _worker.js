function jsonResponse(body, status = 500) {
    return new Response(JSON.stringify(body, null, 2), {
        status,
        headers: {
            'Content-Type': 'application/json; charset=utf-8',
            'Cache-Control': 'no-store'
        }
    });
}

function assertEnv(name, value) {
    if (!value || typeof value !== 'string') {
        throw new Error(`Missing Cloudflare environment variable: ${name}`);
    }
}

function apiErrorResponse(error, fallbackStatus = 500) {
    return jsonResponse({
        error: error.code || 'WORKER_ERROR',
        message: error.message || '接口运行失败，请查看 Cloudflare Worker 日志。'
    }, error.status || fallbackStatus);
}

function buildTargetUrl(baseUrl, targetPath, search) {
    const normalizedBase = baseUrl.replace(/\/+$/, '');
    const parsedBase = new URL(normalizedBase);
    return `${parsedBase.origin}${targetPath}${search}`;
}

function base64FromArrayBuffer(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    bytes.forEach(byte => { binary += String.fromCharCode(byte); });
    return btoa(binary);
}

async function generateKpmSign(timestamp, appSecret) {
    const key = await crypto.subtle.importKey(
        'raw',
        new TextEncoder().encode(appSecret),
        { name: 'HMAC', hash: 'SHA-1' },
        false,
        ['sign']
    );
    const raw = `${timestamp}${appSecret}`;
    const signature = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(raw));
    return base64FromArrayBuffer(signature);
}

async function buildKpmAuthHeaders(env) {
    assertEnv('KPM_APP_SECRET', env.KPM_APP_SECRET);
    const timestamp = String(Math.floor(Date.now() / 1000));
    return {
        'X-App-Id': env.KPM_APP_ID || 'kpm-api',
        'X-Sign': await generateKpmSign(timestamp, env.KPM_APP_SECRET),
        'X-Timestamp': timestamp
    };
}

async function fetchWithTimeout(url, options, timeoutMs) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        return await fetch(url, { ...options, signal: controller.signal });
    } finally {
        clearTimeout(timer);
    }
}

async function startMaterialModify(baseUrl, authHeaders, conversationId, prompt) {
    const response = await fetchWithTimeout(`${baseUrl}/kpm-api/api/material-modify`, {
        method: 'POST',
        headers: {
            ...authHeaders,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            conversationId,
            content: prompt
        })
    }, 25000);
    if (response.body) {
        try {
            await response.body.cancel();
        } catch (error) {}
    }
    if (!response.ok) {
        throw new Error(`素材修改接口返回 ${response.status}`);
    }
}

async function verifyAdminUser(request, env) {
    if (!env.SUPABASE_URL || typeof env.SUPABASE_URL !== 'string') {
        return {
            ok: false,
            response: jsonResponse({
                error: 'MISSING_ENV',
                message: '线上缺少 Cloudflare 环境变量：SUPABASE_URL'
            }, 500)
        };
    }
    if (!env.SUPABASE_KEY || typeof env.SUPABASE_KEY !== 'string') {
        return {
            ok: false,
            response: jsonResponse({
                error: 'MISSING_ENV',
                message: '线上缺少 Cloudflare 环境变量：SUPABASE_KEY'
            }, 500)
        };
    }
    const authorization = request.headers.get('Authorization') || '';
    if (!authorization.startsWith('Bearer ')) {
        return {
            ok: false,
            response: jsonResponse({
                error: 'MISSING_AUTH',
                message: '请先登录管理员账号再运行自动生成。'
            }, 401)
        };
    }

    const targetUrl = `${env.SUPABASE_URL.replace(/\/+$/, '')}/auth/v1/user`;
    let response;
    try {
        response = await fetch(targetUrl, {
            headers: {
                apikey: env.SUPABASE_KEY,
                Authorization: authorization
            }
        });
    } catch (error) {
        return {
            ok: false,
            response: jsonResponse({
                error: 'AUTH_UPSTREAM_ERROR',
                message: `Supabase 登录态校验请求失败：${error.message}`
            }, 502)
        };
    }
    if (!response.ok) {
        return {
            ok: false,
            response: jsonResponse({
                error: 'INVALID_AUTH',
                message: '登录态校验失败，请重新登录。'
            }, 401)
        };
    }
    const user = await response.json();
    const allowedEmails = (env.STYLE_RUN_ALLOWED_EMAILS || 'chenjialing12@xdf.cn')
        .split(',')
        .map(item => item.trim().toLowerCase())
        .filter(Boolean);
    const email = String(user.email || '').toLowerCase();
    if (!allowedEmails.includes(email)) {
        return {
            ok: false,
            response: jsonResponse({
                error: 'FORBIDDEN_USER',
                message: '当前账号没有运行自动生成的权限。'
            }, 403)
        };
    }
    return { ok: true, user };
}

function extractJsonObjectsFromEventStream(text) {
    const results = [];
    text.split(/\r?\n/).forEach(line => {
        const trimmed = line.trim();
        if (!trimmed || trimmed === 'data: [DONE]') return;
        const payload = trimmed.startsWith('data:') ? trimmed.slice(5).trim() : trimmed;
        if (!payload || payload === '[DONE]') return;
        try {
            results.push(JSON.parse(payload));
        } catch (error) {}
    });
    return results;
}

async function runStyleLatestEffect(request, env, ctx) {
    if (request.method !== 'POST') {
        return jsonResponse({ error: 'METHOD_NOT_ALLOWED', message: 'Only POST is supported.' }, 405);
    }

    const adminCheck = await verifyAdminUser(request, env);
    if (!adminCheck.ok) return adminCheck.response;

    const payload = await request.json();
    const prompt = String(payload.prompt || '').trim();
    const styleName = String(payload.styleName || payload.styleId || '画面风格').trim();
    if (!prompt) {
        return jsonResponse({ error: 'MISSING_PROMPT', message: '最新版提示词为空，不能运行。' }, 400);
    }

    const baseUrl = (env.KPM_BASE_URL || 'http://box.xdf.cn').replace(/\/+$/, '');
    const authHeaders = await buildKpmAuthHeaders(env);

    const createResponse = await fetchWithTimeout(`${baseUrl}/kpm-api/skill/create-same-by-one-click`, {
        method: 'POST',
        headers: {
            ...authHeaders,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            creatorEmail: 'chenjialing12@xdf.cn',
            materialName: '彩虹气球派对',
            zipUrl: 'https://aigc-cdn.xdf.cn/material/openapi/xa-ig-kpm/dfe0dceea6b646a09f6abeed586c27e5/package.zip'
        })
    }, 25000);
    const createText = await createResponse.text();
    let createBody = {};
    try { createBody = createText ? JSON.parse(createText) : {}; } catch (error) { createBody = { raw: createText }; }
    if (!createResponse.ok || createBody.code !== 0 || !createBody.data?.conversationId) {
        return jsonResponse({
            error: 'CREATE_SAME_FAILED',
            message: createBody.msg || createBody.message || `一键同款接口返回 ${createResponse.status}`,
            upstream: createBody
        }, 502);
    }

    const conversationId = createBody.data.conversationId;
    const modifyPromise = startMaterialModify(baseUrl, authHeaders, conversationId, prompt).catch(error => {
        console.warn('material-modify background start failed', error);
    });
    if (ctx?.waitUntil) {
        ctx.waitUntil(modifyPromise);
    }

    return jsonResponse({
        ok: true,
        styleName,
        conversationId,
        previewUrl: `${baseUrl.replace(/^http:/, 'https:')}/kpm/${conversationId}`,
        finalResult: null,
        stepCount: null,
        screenshotUrl: null,
        message: '已创建一键同款会话，素材修改已在后台发起，预览链接已回填。生成完成需要等待上游处理；截图自动回填还需要接入独立截图服务。'
    }, 200);
}

export default {
    async fetch(request, env, ctx) {
        const url = new URL(request.url);

        // =========================================================
        // 1. 代理内部大模型请求 (拦截前端发往 /api/llm 的请求)
        // =========================================================
        if (url.pathname.startsWith('/api/llm')) {
            try {
                assertEnv('LLM_BASE_URL', env.LLM_BASE_URL);
                assertEnv('LLM_API_KEY', env.LLM_API_KEY);

                // 从 Cloudflare 环境变量读取真实 URL
                const targetUrl = `${env.LLM_BASE_URL.replace(/\/+$/, '')}/chat/completions`;

                const newRequest = new Request(targetUrl, new Request(request));

                // 从 Cloudflare 环境变量读取真实 API-KEY 并注入
                newRequest.headers.set('Authorization', `Bearer ${env.LLM_API_KEY}`);
                newRequest.headers.set('Content-Type', 'application/json');

                return fetch(newRequest);
            } catch (error) {
                return jsonResponse({
                    error: 'LLM_PROXY_ERROR',
                    message: error.message
                }, 502);
            }
        }

        // =========================================================
        // 2. 代理 Supabase 数据库请求 (拦截前端发往 /api/supabase 的请求)
        // =========================================================
        if (url.pathname.startsWith('/api/supabase')) {
            try {
                assertEnv('SUPABASE_URL', env.SUPABASE_URL);
                assertEnv('SUPABASE_KEY', env.SUPABASE_KEY);

                // 从 Cloudflare 环境变量读取 Supabase 真实 URL
                const targetPath = url.pathname.replace('/api/supabase', '') || '/';
                const targetUrl = buildTargetUrl(env.SUPABASE_URL, targetPath, url.search);

                const newRequest = new Request(targetUrl, new Request(request));

                // 从 Cloudflare 环境变量读取 Supabase 真实 Key 并注入
                newRequest.headers.set('apikey', env.SUPABASE_KEY);
                newRequest.headers.set('Authorization', `Bearer ${env.SUPABASE_KEY}`);

                const response = await fetch(newRequest);
                const contentType = response.headers.get('content-type') || '';

                if (!response.ok && contentType.includes('text/html')) {
                    const upstreamText = await response.text();
                    return jsonResponse({
                        error: 'SUPABASE_UPSTREAM_HTML_ERROR',
                        message: 'Supabase upstream returned an HTML error page. Check Cloudflare SUPABASE_URL and Supabase project status.',
                        upstreamStatus: response.status,
                        upstreamStatusText: response.statusText,
                        upstreamHost: new URL(targetUrl).host,
                        upstreamBodyPreview: upstreamText.slice(0, 300)
                    }, 502);
                }

                const proxiedResponse = new Response(response.body, response);
                proxiedResponse.headers.set('Cache-Control', 'no-store');
                proxiedResponse.headers.set('X-Supabase-Upstream-Host', new URL(targetUrl).host);
                return proxiedResponse;
            } catch (error) {
                return jsonResponse({
                    error: 'SUPABASE_PROXY_ERROR',
                    message: error.message
                }, 502);
            }
        }

        // =========================================================
        // 3. 代理灵感推荐区模板提示词入库请求
        // =========================================================
        if (url.pathname.startsWith('/api/update-inspiration-template-prompt/')) {
            try {
                const templateId = decodeURIComponent(url.pathname.replace('/api/update-inspiration-template-prompt/', ''));
                if (!templateId) {
                    return jsonResponse({ error: 'MISSING_TEMPLATE_ID', message: 'Missing template id.' }, 400);
                }

                const targetUrl = `http://box.test.xdf.cn/kpm-api/tool/update-inspiration-template-prompt/${encodeURIComponent(templateId)}`;
                const newRequest = new Request(targetUrl, new Request(request));
                newRequest.headers.set('Content-Type', request.headers.get('Content-Type') || 'application/json');

                const response = await fetch(newRequest);
                const proxiedResponse = new Response(response.body, response);
                proxiedResponse.headers.set('Cache-Control', 'no-store');
                proxiedResponse.headers.set('Access-Control-Allow-Origin', '*');
                proxiedResponse.headers.set('X-Upstream-Template-Id', templateId);
                return proxiedResponse;
            } catch (error) {
                return jsonResponse({
                    error: 'TEMPLATE_PROMPT_PROXY_ERROR',
                    message: error.message
                }, 502);
            }
        }

        // =========================================================
        // 4. 自动运行画面风格最新版效果
        // =========================================================
        if (url.pathname === '/api/style-eval/run-latest') {
            try {
                return await runStyleLatestEffect(request, env, ctx);
            } catch (error) {
                error.code = error.code || 'STYLE_RUN_LATEST_ERROR';
                return apiErrorResponse(error, error.status || 502);
            }
        }

        // =========================================================
        // 5. 放行所有正常的网页静态资源请求
        // =========================================================
        return env.ASSETS.fetch(request);
    }
}
