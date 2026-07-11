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

const MATERIAL_MODIFY_TIMEOUT_MS = 600000;
const MATERIAL_DESIGN_TIMEOUT_MS = 600000;
const MATERIAL_CREATE_TIMEOUT_MS = 1800000;
const STYLE_RUN_STATUS_TTL_SECONDS = 60 * 60 * 6;
const PROMPT_OPTIMIZER_ALLOWED_MODELS = new Set(['xdf-glm-5.2', 'doubao-seed-2.1-turbo', 'xdf-kimi-k2.6']);
const WORKER_BUILD_ID = 'generation-eval-20260711-kpm-diagnose';

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

function buildKpmStreamHeaders(authHeaders) {
    return {
        ...authHeaders,
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'text/event-stream; charset=utf-8'
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

function parseMaterialModifyEventLine(line) {
    const trimmed = line.trim();
    if (!trimmed || trimmed === 'data: [DONE]') return null;
    const payload = trimmed.startsWith('data:') ? trimmed.slice(5).trim() : trimmed;
    if (!payload || payload === '[DONE]') return null;
    try {
        const event = JSON.parse(payload);
        let text = event.text;
        if (typeof text === 'string') {
            try { text = JSON.parse(text); } catch (error) {}
        }
        return { ...event, text };
    } catch (error) {
        return null;
    }
}

async function readMaterialModifyStream(response, maxDurationMs, onEvent) {
    if (!response.body) return { finalResult: null, stepCount: 0, lastStepName: '', timedOut: false, chunkCount: 0, unparsedLineCount: 0, rawPreview: '' };
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let stepCount = 0;
    let lastStepName = '';
    let finalResult = null;
    let chunkCount = 0;
    let unparsedLineCount = 0;
    let rawPreview = '';
    let timedOut = false;
    const timeoutTimer = setTimeout(() => {
        timedOut = true;
        try { reader.cancel(); } catch (error) {}
    }, maxDurationMs);

    async function handleLine(line) {
        const event = parseMaterialModifyEventLine(line);
        if (!event) {
            if (line.trim()) unparsedLineCount += 1;
            return false;
        }
        if (event.code && event.msg && !event.text) {
            const error = new Error(`素材修改接口业务错误 ${event.code}：${event.msg}`);
            error.upstream = event;
            throw error;
        }
        stepCount += 1;
        lastStepName = event.text?.stepName || event.stepName || lastStepName;
        if (onEvent) {
            await onEvent({ event, stepCount, lastStepName, chunkCount, unparsedLineCount, rawPreview });
        }
        if (event.text?.finalResult) {
            finalResult = event.text.finalResult;
            return true;
        }
        return false;
    }

    while (!timedOut) {
        let result;
        try {
            result = await reader.read();
        } catch (error) {
            if (timedOut) break;
            throw error;
        }
        if (result.done) break;

        const chunkText = decoder.decode(result.value, { stream: true });
        chunkCount += 1;
        if (rawPreview.length < 500) rawPreview += chunkText;
        buffer += chunkText;
        const lines = buffer.split(/\r?\n/);
        buffer = lines.pop() || '';
        for (const line of lines) {
            if (await handleLine(line)) {
                clearTimeout(timeoutTimer);
                try { await reader.cancel(); } catch (error) {}
                return { finalResult, stepCount, lastStepName, timedOut: false, chunkCount, unparsedLineCount, rawPreview };
            }
        }
    }

    clearTimeout(timeoutTimer);
    if (buffer.trim()) {
        if (await handleLine(buffer)) {
            clearTimeout(timeoutTimer);
            try { await reader.cancel(); } catch (error) {}
            return { finalResult, stepCount, lastStepName, timedOut: false, chunkCount, unparsedLineCount, rawPreview };
        }
    }

    try { await reader.cancel(); } catch (error) {}
    return { finalResult, stepCount, lastStepName, timedOut, chunkCount, unparsedLineCount, rawPreview };
}

async function runMaterialModify(baseUrl, authHeaders, conversationId, prompt, onEvent) {
    const response = await fetchWithTimeout(`${baseUrl}/kpm-api/skill/material-modify`, {
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
    if (!response.ok) {
        let errorPreview = '';
        try {
            errorPreview = (await response.text()).replace(/\s+/g, ' ').slice(0, 200);
        } catch (error) {}
        throw new Error(`素材修改接口返回 ${response.status}${errorPreview ? `：${errorPreview}` : ''}`);
    }
    if (onEvent) {
        await onEvent({
            event: {
                text: {
                    stepName: '素材修改接口已连接',
                    stepType: 0,
                    finalResult: null
                }
            },
            stepCount: 0,
            lastStepName: '素材修改接口已连接',
            chunkCount: 0,
            unparsedLineCount: 0,
            rawPreview: ''
        });
    }
    return readMaterialModifyStream(response, MATERIAL_MODIFY_TIMEOUT_MS, onEvent);
}

function streamJsonLine(controller, payload) {
    controller.enqueue(new TextEncoder().encode(`${JSON.stringify({
        ...payload,
        updatedAt: new Date().toISOString()
    })}\n`));
}

async function writeJsonLine(writer, payload) {
    await writer.write(new TextEncoder().encode(`${JSON.stringify({
        ...payload,
        updatedAt: new Date().toISOString()
    })}\n`));
}

function buildStyleRunStatusKey(origin, runId) {
    return new Request(`${origin.replace(/\/+$/, '')}/api/style-eval/run-status/${encodeURIComponent(runId)}`);
}

async function putStyleRunStatus(origin, runId, status) {
    if (!globalThis.caches?.default) return;
    try {
        await caches.default.put(
            buildStyleRunStatusKey(origin, runId),
            new Response(JSON.stringify({
                ...status,
                runId,
                updatedAt: new Date().toISOString()
            }, null, 2), {
                status: 200,
                headers: {
                    'Content-Type': 'application/json; charset=utf-8',
                    'Cache-Control': `public, max-age=${STYLE_RUN_STATUS_TTL_SECONDS}`
                }
            })
        );
    } catch (error) {
        console.warn('style run status cache put failed', error);
    }
}

async function readStyleRunStatus(request, env) {
    if (request.method !== 'GET') {
        return jsonResponse({ error: 'METHOD_NOT_ALLOWED', message: 'Only GET is supported.' }, 405);
    }
    const adminCheck = await verifyAdminUser(request, env);
    if (!adminCheck.ok) return adminCheck.response;

    const url = new URL(request.url);
    const runId = decodeURIComponent(url.pathname.replace('/api/style-eval/run-status/', '')).trim();
    if (!runId) {
        return jsonResponse({ error: 'MISSING_RUN_ID', message: '缺少运行任务 ID。' }, 400);
    }
    if (!globalThis.caches?.default) {
        return jsonResponse({
            error: 'RUN_STATUS_UNAVAILABLE',
            message: '当前运行环境不支持后台状态缓存。'
        }, 404);
    }

    const cached = await caches.default.match(buildStyleRunStatusKey(url.origin, runId));
    if (!cached) {
        return jsonResponse({
            error: 'RUN_STATUS_NOT_FOUND',
            message: '没有找到这个生成任务的后台状态，可能任务已过期或部署节点已切换。'
        }, 404);
    }
    const response = new Response(cached.body, cached);
    response.headers.set('Cache-Control', 'no-store');
    return response;
}

async function drainMaterialModifyJob(origin, runId, baseUrl, authHeaders, conversationId, prompt) {
    try {
        await putStyleRunStatus(origin, runId, {
            status: 'modifying',
            conversationId,
            previewUrl: `${baseUrl.replace(/^http:/, 'https:')}/kpm/${conversationId}`,
            message: '素材修改接口已接收，正在等待最终生成结果。'
        });
        const modifyResult = await runMaterialModify(baseUrl, authHeaders, conversationId, prompt);
        if (modifyResult.timedOut && !modifyResult.finalResult) {
            await putStyleRunStatus(origin, runId, {
                status: 'timeout',
                conversationId,
                previewUrl: `${baseUrl.replace(/^http:/, 'https:')}/kpm/${conversationId}`,
                stepCount: modifyResult.stepCount,
                lastStepName: modifyResult.lastStepName,
                message: `素材修改仍在上游处理中，${Math.round(MATERIAL_MODIFY_TIMEOUT_MS / 1000)} 秒内未收到最终完成信号。`
            });
            return;
        }
        await putStyleRunStatus(origin, runId, {
            status: 'done',
            conversationId,
            previewUrl: `${baseUrl.replace(/^http:/, 'https:')}/kpm/${conversationId}`,
            finalResult: modifyResult.finalResult || null,
            stepCount: modifyResult.stepCount,
            lastStepName: modifyResult.lastStepName,
            message: '已完成一键同款和素材修改，预览链接已回填。截图自动回填还需要接入独立截图服务。'
        });
    } catch (error) {
        await putStyleRunStatus(origin, runId, {
            status: 'failed',
            conversationId,
            previewUrl: `${baseUrl.replace(/^http:/, 'https:')}/kpm/${conversationId}`,
            message: `一键同款已创建，但素材修改没有完成：${error.message || String(error)}`
        });
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
    const url = new URL(request.url);

    const adminCheck = await verifyAdminUser(request, env);
    if (!adminCheck.ok) return adminCheck.response;

    const payload = await request.json();
    const prompt = String(payload.prompt || '').trim();
    const styleName = String(payload.styleName || payload.styleId || '画面风格').trim();
    const materialName = String(payload.materialName || '彩虹气球派对').trim();
    const zipUrl = String(payload.zipUrl || 'https://aigc-cdn.xdf.cn/material/openapi/xa-ig-kpm/dfe0dceea6b646a09f6abeed586c27e5/package.zip').trim();
    if (!prompt) {
        return jsonResponse({ error: 'MISSING_PROMPT', message: '最新版提示词为空，不能运行。' }, 400);
    }
    if (!materialName || !/^https?:\/\//i.test(zipUrl)) {
        return jsonResponse({ error: 'MISSING_CREATE_SAME_PARAMS', message: '请填写素材名称和有效的 ZIP 文件 URL。' }, 400);
    }

    const configuredBaseUrl = String(env.KPM_BASE_URL || 'https://box.xdf.cn').replace(/\/+$/, '');
    const normalizedBaseUrl = configuredBaseUrl
        .replace(/^http:\/\/box\.xdf\.cn/i, 'https://box.xdf.cn');
    const baseUrl = normalizedBaseUrl.includes('box.test.xdf.cn') ? 'https://box.xdf.cn' : normalizedBaseUrl;
    const authHeaders = await buildKpmAuthHeaders(env);

    const { readable, writable } = new TransformStream();
    const writer = writable.getWriter();
    const streamJob = (async () => {
        const heartbeat = setInterval(() => {
            writeJsonLine(writer, {
                status: 'heartbeat',
                message: '素材修改仍在生成中，请保持页面打开。'
            }).catch(() => {});
        }, 15000);

        let conversationId = '';
        let previewUrl = '';
        const runId = crypto.randomUUID();
        try {
            await writeJsonLine(writer, {
                ok: true,
                status: 'creating',
                runId,
                styleName,
                message: '正在创建一键同款会话。'
            });
            const createResponse = await fetchWithTimeout(`${baseUrl}/kpm-api/skill/create-same-by-one-click`, {
                method: 'POST',
                headers: {
                    ...authHeaders,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    creatorEmail: 'chenjialing12@xdf.cn',
                    materialName,
                    zipUrl
                })
            }, 25000);
            const createText = await createResponse.text();
            let createBody = {};
            try { createBody = createText ? JSON.parse(createText) : {}; } catch (error) { createBody = { raw: createText }; }
            const createSuccess = createBody.code === 0 || createBody.code === 200;
            if (!createResponse.ok || !createSuccess || !createBody.data?.conversationId) {
                await writeJsonLine(writer, {
                    ok: false,
                    status: 'failed',
                    error: 'CREATE_SAME_FAILED',
                    message: createBody.msg || createBody.message || `一键同款接口返回 ${createResponse.status}`,
                    upstream: createBody
                });
                return;
            }

            conversationId = createBody.data.conversationId;
            previewUrl = `${baseUrl.replace(/^http:/, 'https:')}/kpm/${conversationId}`;
            await putStyleRunStatus(url.origin, runId, {
                status: 'created',
                styleName,
                conversationId,
                previewUrl,
                message: '已创建一键同款会话，正在启动素材修改。'
            });
            await writeJsonLine(writer, {
                ok: true,
                status: 'created',
                runId,
                styleName,
                conversationId,
                previewUrl,
                message: '已创建一键同款会话，正在启动素材修改。'
            });

            const modifyResult = await runMaterialModify(baseUrl, authHeaders, conversationId, prompt, async ({ event, stepCount, lastStepName, chunkCount, unparsedLineCount, rawPreview }) => {
                const text = event.text || {};
                const status = text.finalResult ? 'done' : 'progress';
                const statusBody = {
                    status,
                    styleName,
                    conversationId,
                    previewUrl,
                    stepCount,
                    stepName: text.stepName || lastStepName,
                    stepType: text.stepType || null,
                    finalResult: text.finalResult || null,
                    chunkCount,
                    unparsedLineCount,
                    rawPreview: rawPreview ? rawPreview.replace(/\s+/g, ' ').slice(0, 240) : '',
                    message: text.finalResult ? '素材修改已完成。' : `素材修改进度：${text.stepName || lastStepName || '处理中'}`
                };
                await putStyleRunStatus(url.origin, runId, statusBody);
                await writeJsonLine(writer, { ok: true, runId, ...statusBody });
            });

            if (modifyResult.timedOut && !modifyResult.finalResult) {
                const timeoutBody = {
                    status: 'timeout',
                    styleName,
                    conversationId,
                    previewUrl,
                    stepCount: modifyResult.stepCount,
                    lastStepName: modifyResult.lastStepName,
                    chunkCount: modifyResult.chunkCount,
                    unparsedLineCount: modifyResult.unparsedLineCount,
                    rawPreview: modifyResult.rawPreview ? modifyResult.rawPreview.replace(/\s+/g, ' ').slice(0, 240) : '',
                    message: `素材修改仍在上游处理中，${Math.round(MATERIAL_MODIFY_TIMEOUT_MS / 1000)} 秒内未收到最终完成信号。已收到 ${modifyResult.chunkCount} 个流片段，成功解析 ${modifyResult.stepCount} 个步骤。${modifyResult.rawPreview ? ` 原始片段：${modifyResult.rawPreview.replace(/\s+/g, ' ').slice(0, 120)}` : ''}`
                };
                await putStyleRunStatus(url.origin, runId, timeoutBody);
                await writeJsonLine(writer, { ok: false, runId, ...timeoutBody });
                return;
            }

            const doneBody = {
                status: 'done',
                styleName,
                conversationId,
                previewUrl,
                finalResult: modifyResult.finalResult || null,
                stepCount: modifyResult.stepCount,
                lastStepName: modifyResult.lastStepName,
                screenshotUrl: null,
                message: '已完成一键同款和素材修改，预览链接已回填。截图自动回填还需要接入独立截图服务。'
            };
            await putStyleRunStatus(url.origin, runId, doneBody);
            await writeJsonLine(writer, { ok: true, runId, ...doneBody });
        } catch (error) {
            const failedBody = {
                status: 'failed',
                styleName,
                conversationId,
                previewUrl,
                message: `自动生成没有完成：${error.message || String(error)}`
            };
            await putStyleRunStatus(url.origin, runId, failedBody);
            await writeJsonLine(writer, { ok: false, runId, ...failedBody });
        } finally {
            clearInterval(heartbeat);
            await writer.close();
        }
    })();

    if (ctx?.waitUntil) {
        ctx.waitUntil(streamJob);
    } else {
        streamJob.catch(error => console.warn('style run stream failed', error));
    }

    return new Response(readable, {
        status: 200,
        headers: {
            'Content-Type': 'application/x-ndjson; charset=utf-8',
            'Cache-Control': 'no-store',
            'X-Accel-Buffering': 'no'
        }
    });
}

function normalizeKpmBaseUrl(env) {
    const configuredBaseUrl = String(env.KPM_BASE_URL || 'https://box.xdf.cn').replace(/\/+$/, '');
    const normalizedBaseUrl = configuredBaseUrl
        .replace(/^http:\/\/box\.xdf\.cn/i, 'https://box.xdf.cn');
    return normalizedBaseUrl.includes('box.test.xdf.cn') ? 'https://box.xdf.cn' : normalizedBaseUrl;
}

function buildGenerationDesignContent(payload) {
    return [
        `【测评用例】${payload.caseName || '课件生成效果测评'}`,
        '',
        '【用户需求】',
        payload.userRequirement,
        '',
        `【本次测评的系统提示词版本】${payload.versionLabel || ''}`,
        payload.systemPrompt,
        '',
        '【生成要求】',
        '请严格基于以上用户需求和本次测评的系统提示词版本生成一个可运行的互动课件。优先保证知识准确、教学适配、交互稳定和视觉完整。不要在成品中展示本段测评说明。'
    ].join('\n');
}

async function readKpmEventStream(response, maxDurationMs, onEvent, options = {}) {
    if (!response.body) return { conversationId: '', finalResult: null, stepCount: 0, lastStepName: '', timedOut: false, chunkCount: 0, rawPreview: '' };
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let conversationId = '';
    let finalResult = null;
    let stepCount = 0;
    let lastStepName = '';
    let chunkCount = 0;
    let rawPreview = '';
    let timedOut = false;
    const stopOnFinal = options.stopOnFinal !== false;
    const timeoutTimer = setTimeout(() => {
        timedOut = true;
        try { reader.cancel(); } catch (error) {}
    }, maxDurationMs);

    async function handleLine(line) {
        const event = parseMaterialModifyEventLine(line);
        if (!event) return false;
        if (event.code && event.msg && !event.text) {
            throw new Error(`KPM 接口业务错误 ${event.code}：${event.msg}`);
        }
        conversationId = event.conversationId || conversationId;
        stepCount += 1;
        const text = event.text;
        if (text && typeof text === 'object') {
            lastStepName = text.stepName || lastStepName;
            if (text.finalResult) finalResult = text.finalResult;
        }
        if (onEvent) {
            await onEvent({
                event,
                conversationId,
                finalResult,
                stepCount,
                lastStepName,
                chunkCount,
                rawPreview
            });
        }
        return Boolean(stopOnFinal && finalResult);
    }

    while (!timedOut) {
        let result;
        try {
            result = await reader.read();
        } catch (error) {
            if (timedOut) break;
            throw error;
        }
        if (result.done) break;
        const chunkText = decoder.decode(result.value, { stream: true });
        chunkCount += 1;
        if (rawPreview.length < 500) rawPreview += chunkText;
        buffer += chunkText;
        const lines = buffer.split(/\r?\n/);
        buffer = lines.pop() || '';
        for (const line of lines) {
            if (await handleLine(line)) {
                clearTimeout(timeoutTimer);
                try { await reader.cancel(); } catch (error) {}
                return { conversationId, finalResult, stepCount, lastStepName, timedOut: false, chunkCount, rawPreview };
            }
        }
    }

    clearTimeout(timeoutTimer);
    if (buffer.trim()) {
        if (await handleLine(buffer)) {
            try { await reader.cancel(); } catch (error) {}
            return { conversationId, finalResult, stepCount, lastStepName, timedOut: false, chunkCount, rawPreview };
        }
    }
    try { await reader.cancel(); } catch (error) {}
    return { conversationId, finalResult, stepCount, lastStepName, timedOut, chunkCount, rawPreview };
}

async function runGenerationPromptVersion(request, env, ctx) {
    if (request.method !== 'POST') {
        return jsonResponse({ error: 'METHOD_NOT_ALLOWED', message: 'Only POST is supported.' }, 405);
    }
    const adminCheck = await verifyAdminUser(request, env);
    if (!adminCheck.ok) return adminCheck.response;

    const payload = await request.json();
    const caseName = String(payload.caseName || '课件生成效果测评').trim();
    const userRequirement = String(payload.userRequirement || '').trim();
    const versionLabel = String(payload.versionLabel || '提示词版本').trim();
    const systemPrompt = String(payload.systemPrompt || '').trim();
    if (!userRequirement) {
        return jsonResponse({ error: 'MISSING_USER_REQUIREMENT', message: '请先填写用户需求。' }, 400);
    }
    if (!systemPrompt) {
        return jsonResponse({ error: 'MISSING_SYSTEM_PROMPT', message: '请先填写系统提示词。' }, 400);
    }

    const baseUrl = normalizeKpmBaseUrl(env);
    const authHeaders = await buildKpmAuthHeaders(env);
    const designContent = buildGenerationDesignContent({ caseName, userRequirement, versionLabel, systemPrompt });

    const { readable, writable } = new TransformStream();
    const writer = writable.getWriter();
    const streamJob = (async () => {
        const heartbeat = setInterval(() => {
            writeJsonLine(writer, {
                status: 'heartbeat',
                message: '课件生成仍在处理中，请保持页面打开。'
            }).catch(() => {});
        }, 15000);
        let conversationId = '';
        try {
            await writeJsonLine(writer, {
                ok: true,
                status: 'designing',
                message: '正在调用方案设计接口。'
            });
            const designRequestBody = JSON.stringify({ content: designContent });
            const designFetch = await fetchKpmStreamWithFallback(baseUrl, '/kpm-api/skill/material-design', authHeaders, designRequestBody, '方案设计');
            const designResponse = designFetch.response;
            const designResult = await readKpmEventStream(designResponse, MATERIAL_DESIGN_TIMEOUT_MS, async ({ event, conversationId: currentConversationId, stepCount }) => {
                if (currentConversationId) conversationId = currentConversationId;
                await writeJsonLine(writer, {
                    ok: true,
                    status: 'designing',
                    conversationId,
                    stepCount,
                    attempt: designFetch.attempt,
                    message: event.text && typeof event.text === 'string' ? '方案设计接口正在返回方案内容。' : '方案设计处理中。'
                });
            }, { stopOnFinal: false });
            conversationId = designResult.conversationId || conversationId;
            if (!conversationId) {
                throw new Error('方案设计接口没有返回 conversationId，无法继续创建课件。');
            }
            if (designResult.timedOut) {
                throw new Error(`方案设计超过 ${Math.round(MATERIAL_DESIGN_TIMEOUT_MS / 1000)} 秒仍未结束。`);
            }

            await writeJsonLine(writer, {
                ok: true,
                status: 'creating',
                conversationId,
                message: '方案设计完成，正在调用素材创建接口。'
            });
            const createRequestBody = JSON.stringify({ conversationId });
            const createFetch = await fetchKpmStreamWithFallback(baseUrl, '/kpm-api/skill/material-create', authHeaders, createRequestBody, '素材创建');
            const createResponse = createFetch.response;
            const createResult = await readKpmEventStream(createResponse, MATERIAL_CREATE_TIMEOUT_MS, async ({ event, finalResult, stepCount, lastStepName }) => {
                const text = event.text && typeof event.text === 'object' ? event.text : {};
                await writeJsonLine(writer, {
                    ok: true,
                    status: finalResult ? 'done' : 'progress',
                    conversationId,
                    stepCount,
                    stepName: text.stepName || lastStepName || '',
                    stepType: text.stepType || null,
                    attempt: createFetch.attempt,
                    finalResult: finalResult || null,
                    fileUrl: finalResult?.fileUrl || '',
                    pushUrl: finalResult?.pushUrl || '',
                    snapshotId: finalResult?.snapshotId || '',
                    filePath: finalResult?.filePath || '',
                    message: finalResult ? '素材创建完成，预览链接已回填。' : `素材创建进度：${text.stepName || lastStepName || '处理中'}`
                });
            }, { stopOnFinal: true });

            if (createResult.timedOut && !createResult.finalResult) {
                await writeJsonLine(writer, {
                    ok: false,
                    status: 'timeout',
                    conversationId,
                    stepCount: createResult.stepCount,
                    lastStepName: createResult.lastStepName,
                    message: `素材创建仍在上游处理中，${Math.round(MATERIAL_CREATE_TIMEOUT_MS / 1000)} 秒内未收到最终完成信号。`
                });
                return;
            }
            if (!createResult.finalResult) {
                throw new Error('素材创建流程结束，但没有返回最终预览链接。');
            }
        } catch (error) {
            await writeJsonLine(writer, {
                ok: false,
                status: 'failed',
                conversationId,
                message: `课件生成没有完成：${error.message || String(error)}`
            });
        } finally {
            clearInterval(heartbeat);
            await writer.close();
        }
    })();

    if (ctx?.waitUntil) {
        ctx.waitUntil(streamJob);
    } else {
        streamJob.catch(error => console.warn('generation run stream failed', error));
    }

    return new Response(readable, {
        status: 200,
        headers: {
            'Content-Type': 'application/x-ndjson; charset=utf-8',
            'Cache-Control': 'no-store',
            'X-Accel-Buffering': 'no'
        }
    });
}

function stripJsonFence(value) {
    return String(value || '')
        .replace(/^```json\s*/i, '')
        .replace(/^```\s*/i, '')
        .replace(/```$/i, '')
        .trim();
}

async function suggestNextGenerationPrompt(request, env) {
    if (request.method !== 'POST') {
        return jsonResponse({ error: 'METHOD_NOT_ALLOWED', message: 'Only POST is supported.' }, 405);
    }
    const adminCheck = await verifyAdminUser(request, env);
    if (!adminCheck.ok) return adminCheck.response;

    const payload = await request.json();
    const model = String(payload.model || '').trim();
    if (!PROMPT_OPTIMIZER_ALLOWED_MODELS.has(model)) {
        return jsonResponse({ error: 'UNSUPPORTED_MODEL', message: '请选择页面内允许的提示词优化模型。' }, 400);
    }
    const baseUrl = String(env.PROMPT_OPTIMIZER_BASE_URL || env.LLM_BASE_URL || '').replace(/\/+$/, '');
    const apiKey = String(env.PROMPT_OPTIMIZER_API_KEY || env.LLM_API_KEY || '');
    assertEnv('PROMPT_OPTIMIZER_BASE_URL or LLM_BASE_URL', baseUrl);
    assertEnv('PROMPT_OPTIMIZER_API_KEY or LLM_API_KEY', apiKey);

    const userRequirement = String(payload.userRequirement || '').trim();
    const previousPrompt = String(payload.previousPrompt || '').trim();
    const issues = String(payload.issues || '').trim();
    const solution = String(payload.solution || '').trim();
    const scores = payload.scores || {};
    if (!userRequirement || !previousPrompt) {
        return jsonResponse({ error: 'MISSING_PROMPT_INPUT', message: '缺少用户需求或上一版提示词。' }, 400);
    }

    const response = await fetchWithTimeout(`${baseUrl}/chat/completions`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            model,
            temperature: 0.2,
            response_format: { type: 'json_object' },
            messages: [
                {
                    role: 'system',
                    content: '你是互动课件系统提示词优化专家。你需要根据上一版课件的测评问题，提炼可复用的改进经验，并输出下一版完整系统提示词。只返回 JSON。'
                },
                {
                    role: 'user',
                    content: [
                        '请基于以下信息生成下一版系统提示词。',
                        '',
                        '输出 JSON 格式：',
                        '{"analysis":"简要说明从问题中总结出的优化原则","nextPrompt":"完整的下一版系统提示词"}',
                        '',
                        '【用户需求】',
                        userRequirement,
                        '',
                        '【上一版系统提示词】',
                        previousPrompt,
                        '',
                        '【上一版测评问题】',
                        issues || '未填写',
                        '',
                        '【期望解决方向】',
                        solution || '未填写',
                        '',
                        '【四维评分】',
                        JSON.stringify(scores || {}, null, 2)
                    ].join('\n')
                }
            ]
        })
    }, 90000);
    const responseText = await response.text();
    let responseBody = {};
    try { responseBody = responseText ? JSON.parse(responseText) : {}; } catch (error) { responseBody = { raw: responseText }; }
    if (!response.ok) {
        return jsonResponse({
            error: 'PROMPT_OPTIMIZER_UPSTREAM_ERROR',
            message: responseBody.error?.message || responseBody.message || `提示词优化接口返回 ${response.status}`
        }, 502);
    }
    const content = responseBody.choices?.[0]?.message?.content || responseBody.output_text || responseBody.raw || '';
    let parsed = {};
    try {
        parsed = JSON.parse(stripJsonFence(content));
    } catch (error) {
        parsed = { analysis: '', nextPrompt: String(content || '').trim() };
    }
    return jsonResponse({
        ok: true,
        model,
        analysis: String(parsed.analysis || '').trim(),
        nextPrompt: String(parsed.nextPrompt || parsed.prompt || '').trim()
    }, 200);
}

async function readResponsePreview(response, maxChars = 500) {
    const contentType = response.headers.get('content-type') || '';
    let preview = '';
    try {
        if (!response.body) {
            preview = (await response.text()).replace(/\s+/g, ' ').slice(0, maxChars);
        } else {
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            const result = await reader.read();
            if (result.value) preview = decoder.decode(result.value, { stream: true });
            try { await reader.cancel(); } catch (error) {}
            preview = preview.replace(/\s+/g, ' ').slice(0, maxChars);
        }
    } catch (error) {
        preview = `READ_PREVIEW_FAILED: ${error.message || String(error)}`;
    }
    return { contentType, preview };
}

async function probeKpmMaterialDesign(name, url, headers) {
    const startedAt = Date.now();
    try {
        const body = JSON.stringify({ content: 'probe：请仅返回一句话方案，不要生成课件。' });
        const response = await fetchWithTimeout(url, {
            method: 'POST',
            headers,
            body
        }, 25000);
        const preview = await readResponsePreview(response, 600);
        return {
            name,
            ok: response.ok,
            status: response.status,
            statusText: response.statusText,
            contentType: preview.contentType,
            bodyLength: body.length,
            durationMs: Date.now() - startedAt,
            preview: preview.preview
        };
    } catch (error) {
        return {
            name,
            ok: false,
            error: error.message || String(error),
            durationMs: Date.now() - startedAt
        };
    }
}

async function fetchKpmStreamWithFallback(baseUrl, path, authHeaders, body, label) {
    const normalizedBase = baseUrl.replace(/\/+$/, '');
    const attempts = [
        {
            name: 'https-stream-headers',
            url: `${normalizedBase}${path}`,
            headers: buildKpmStreamHeaders(authHeaders)
        },
        {
            name: 'https-json-headers',
            url: `${normalizedBase}${path}`,
            headers: {
                ...authHeaders,
                'Content-Type': 'application/json; charset=utf-8'
            }
        },
        {
            name: 'http-stream-headers',
            url: `${normalizedBase.replace(/^https:/, 'http:')}${path}`,
            headers: buildKpmStreamHeaders(authHeaders)
        }
    ];
    const failures = [];
    for (const attempt of attempts) {
        let response;
        try {
            response = await fetchWithTimeout(attempt.url, {
                method: 'POST',
                headers: attempt.headers,
                body
            }, 25000);
        } catch (error) {
            failures.push({
                attempt: attempt.name,
                error: error.message || String(error)
            });
            continue;
        }
        if (response.ok) {
            return { response, attempt: attempt.name };
        }
        const preview = await readResponsePreview(response, 260);
        failures.push({
            attempt: attempt.name,
            status: response.status,
            statusText: response.statusText,
            contentType: preview.contentType,
            preview: preview.preview
        });
        if (response.status === 401 || response.status === 403) break;
    }
    const detail = failures.map(item => {
        if (item.status) return `${item.attempt}: ${item.status} ${item.contentType || '-'} ${item.preview || ''}`;
        return `${item.attempt}: ${item.error || '请求失败'}`;
    }).join(' | ');
    throw new Error(`${label}接口多路请求均未成功，bodyLength=${body.length}：${detail}`);
}

async function diagnoseKpmGeneration(request, env) {
    if (request.method !== 'GET' && request.method !== 'POST') {
        return jsonResponse({ error: 'METHOD_NOT_ALLOWED', message: 'Only GET/POST is supported.' }, 405);
    }
    const adminCheck = await verifyAdminUser(request, env);
    if (!adminCheck.ok) return adminCheck.response;

    const baseUrl = normalizeKpmBaseUrl(env);
    const authHeaders = await buildKpmAuthHeaders(env);
    const designPath = '/kpm-api/skill/material-design';
    const httpsDesignUrl = `${baseUrl}${designPath}`;
    const httpDesignUrl = `${baseUrl.replace(/^https:/, 'http:')}${designPath}`;
    const jsonHeaders = {
        ...authHeaders,
        'Content-Type': 'application/json; charset=utf-8'
    };
    const streamHeaders = buildKpmStreamHeaders(authHeaders);

    const probes = [];
    probes.push(await probeKpmMaterialDesign('https-stream-headers', httpsDesignUrl, streamHeaders));
    probes.push(await probeKpmMaterialDesign('https-json-headers', httpsDesignUrl, jsonHeaders));
    probes.push(await probeKpmMaterialDesign('http-stream-headers', httpDesignUrl, streamHeaders));

    return jsonResponse({
        ok: true,
        buildId: WORKER_BUILD_ID,
        baseUrl,
        env: {
            hasKpmAppSecret: Boolean(env.KPM_APP_SECRET),
            kpmAppSecretLength: String(env.KPM_APP_SECRET || '').length,
            kpmAppId: env.KPM_APP_ID || 'kpm-api',
            hasKpmBaseUrl: Boolean(env.KPM_BASE_URL)
        },
        probes
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

        if (url.pathname.startsWith('/api/style-eval/run-status/')) {
            try {
                return await readStyleRunStatus(request, env);
            } catch (error) {
                error.code = error.code || 'STYLE_RUN_STATUS_ERROR';
                return apiErrorResponse(error, error.status || 502);
            }
        }

        // =========================================================
        // 5. 课件生成效果：提示词版本对比
        // =========================================================
        if (url.pathname === '/api/generation-eval/run-prompt-version') {
            try {
                return await runGenerationPromptVersion(request, env, ctx);
            } catch (error) {
                error.code = error.code || 'GENERATION_RUN_ERROR';
                return apiErrorResponse(error, error.status || 502);
            }
        }

        if (url.pathname === '/api/generation-eval/suggest-next-prompt') {
            try {
                return await suggestNextGenerationPrompt(request, env);
            } catch (error) {
                error.code = error.code || 'GENERATION_PROMPT_OPTIMIZER_ERROR';
                return apiErrorResponse(error, error.status || 502);
            }
        }

        if (url.pathname === '/api/generation-eval/diagnose-kpm') {
            try {
                return await diagnoseKpmGeneration(request, env);
            } catch (error) {
                error.code = error.code || 'GENERATION_KPM_DIAGNOSE_ERROR';
                return apiErrorResponse(error, error.status || 502);
            }
        }

        // =========================================================
        // 6. 放行所有正常的网页静态资源请求
        // =========================================================
        return env.ASSETS.fetch(request);
    }
}
