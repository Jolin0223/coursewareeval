export default {
    async fetch(request, env) {
        const url = new URL(request.url);

        // =========================================================
        // 1. 代理内部大模型请求 (拦截前端发往 /api/llm 的请求)
        // =========================================================
        if (url.pathname.startsWith('/api/llm')) {
            // 从 Cloudflare 环境变量读取真实 URL
            const targetUrl = `${env.LLM_BASE_URL}/chat/completions`;
            
            const newRequest = new Request(targetUrl, new Request(request));
            
            // 从 Cloudflare 环境变量读取真实 API-KEY 并注入
            newRequest.headers.set('Authorization', `Bearer ${env.LLM_API_KEY}`);
            newRequest.headers.set('Content-Type', 'application/json');
            
            return fetch(newRequest);
        }

        // =========================================================
        // 2. 代理 Supabase 数据库请求 (拦截前端发往 /api/supabase 的请求)
        // =========================================================
        if (url.pathname.startsWith('/api/supabase')) {
            // 从 Cloudflare 环境变量读取 Supabase 真实 URL
            const targetPath = url.pathname.replace('/api/supabase', '');
            const targetUrl = `${env.SUPABASE_URL}${targetPath}${url.search}`;
            
            const newRequest = new Request(targetUrl, new Request(request));
            
            // 从 Cloudflare 环境变量读取 Supabase 真实 Key 并注入
            newRequest.headers.set('apikey', env.SUPABASE_KEY);
            newRequest.headers.set('Authorization', `Bearer ${env.SUPABASE_KEY}`);
            
            return fetch(newRequest);
        }

        // =========================================================
        // 3. 放行所有正常的网页静态资源请求
        // =========================================================
        return env.ASSETS.fetch(request);
    }
}