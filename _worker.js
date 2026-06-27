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

function buildTargetUrl(baseUrl, targetPath, search) {
    const normalizedBase = baseUrl.replace(/\/+$/, '');
    const parsedBase = new URL(normalizedBase);
    return `${parsedBase.origin}${targetPath}${search}`;
}

export default {
    async fetch(request, env) {
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
        // 3. 放行所有正常的网页静态资源请求
        // =========================================================
        return env.ASSETS.fetch(request);
    }
}
