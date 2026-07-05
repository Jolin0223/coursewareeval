# Memory.md - Courseware Evaluation Site

## 2026-06-28

- GitHub repo: `https://github.com/Jolin0223/coursewareeval`
- Local git checkout: `/Users/jolin/Desktop/部署到github上的项目/coursewareeval`
- Previous loose local folder `/Users/jolin/Desktop/部署到github上的项目/eval-site` is not a git repo and should be treated as a backup/reference only.
- Runtime issue after Supabase config update: dashboard snapshot failed with `task.feedbacks[email].trim is not a function`.
- Root cause: `feedbacks` contains non-rater system fields such as `failure_reasons`, whose value is an object. Dashboard NLP and export code assumed every `feedbacks` entry was a string keyed by an email.
- Fix direction: filter rater keys through `isRaterEmail()` and normalize feedback values through `normalizeFeedbackText()`, so non-string/system feedback fields no longer crash dashboard rendering or Excel export.

## 2026-07-03

- Product positioning changed from a courseware comparison score page to an AI interactive courseware evaluation platform.
- First rebuilt frontend milestone focuses on two P0 workflows:
  - `画面风格测评`: imported `7月2日调整画面风格-效果测试 (1).xlsx` into structured style/version data, covering 19 base styles and Prompt V1-V5 records.
  - `一键同款 vs 套用玩法`: imported `7月1日 一键同款&套用模板效果测试.xlsx` into material-level comparison cases.
- New frontend stores screenshots, scores, issue notes, status, winner, and reason tags in browser localStorage for fast IA validation. Multi-user sharing still needs Supabase tables plus Supabase Storage.
- Old single-file evaluation page remains in `legacy.html` as a reference copy; the root `index.html` is now based on that admin shell again.

## 2026-07-04

- User decided the main product should be based on the old Ant Design-like admin shell, not a separate custom workspace shell.
- Main navigation now separates `效果自评` for internal product iteration evaluation from `竞品测评` for external vertical competitor comparison.
- Current self-evaluation submenu priorities: `课件生成效果`, `画面风格调整`, `套用玩法`, `一键同款`.
- `画面风格调整` should work as an iteration workbench: always show the latest version first, keep historical versions below, allow screenshot/link/score/problem capture, generate and manually edit next-version reference prompts, export developer-facing Excel, and reserve a future one-click style-library update hook.
- `套用玩法` should use only the 16 audit-approved rows from `灵感推荐区_最终全量表及制作节奏.xlsx` / sheet `【审核版】6月30日版本上线入库使用表-开发使用，勿动` as the developer-facing source format. The second column `id` is the `templateId` for the prompt update API `/api/update-inspiration-template-prompt/{templateId}`, proxied to `http://box.test.xdf.cn/kpm-api/tool/update-inspiration-template-prompt/{templateId}`.
- `画面风格调整` should avoid low-action metrics such as screenshot count. The summary should focus on review decisions like `可入库风格` and `待处理问题`; latest effect evidence supports multiple screenshots as a carousel and an embedded link preview with an open-link fallback. New dropdowns in the workbench should use the custom Ant-like menu, not native browser `<select>` controls.
- Each of the 19 base styles in `data/style-eval-seed.json` has a `referenceImageUrl` in the same order as the style list. The style workbench should show the image as a compact left-list thumbnail only; clicking the thumbnail opens a large preview modal. Avoid adding a separate large reference-image module in the selected style detail.
- Self-evaluation summary metric cards were removed from `画面风格调整` and `套用玩法` because they did not drive reviewer action. Keep these pages focused on search, list selection, evidence preview, issue notes, prompt revision, export, and入库 actions.
- `套用玩法` list items should show the audit sheet cover image from `新增字段-coverurl`; clicking the cover opens the same image preview modal. The selected template detail should not show heavy category/age summary cards.
- Effect URLs should not render a separate embedded preview card. Keep the action beside the URL input as a compact `打开` button. Screenshot upload controls should use custom lightweight buttons, not the browser's default file input chrome.
- The `生成下一版` action belongs beside the latest issue/problem field because it uses the previous/latest problem and solution notes to overwrite the next-version prompt draft. Do not place this action inside the next prompt textarea header.
- `套用玩法` detail should stay focused on run evidence, score/status, issue, solution, prompt and入库. Do not show `卡片描述`, `适用标签`, or `玩法流程` blocks in the detail panel.
- `画面风格调整` seed data has been updated from the July 2 CSV to Prompt V1-V6 for all 19 base styles. V6 is the current final candidate for developer入库, and the developer Excel export must use only the latest final-candidate prompt, not the local “下一版本参考提示词” draft.
- `画面风格调整` developer export follows the provided workbook template exactly: `styleCode`, `displayName`, `userDescription`, `recommendedUse`, `图片URL地址`, `风格提示词` on `Sheet1`.
- `套用玩法` current prompts are the 16 Markdown files under `03-套用模板提示词/正在调试的提示词-V4版本`, not the old short Excel adaptation notes or earlier `正在调试的提示词` directory. `data/inspiration-template-seed.json` stores the full Markdown prompt in `adaptationText` plus `promptSourceFile` and `promptSourceHash`. The page, one-click入库, copy fallback, and Excel export should use `getTemplateCurrentPrompt()` so stale localStorage drafts do not override newer source prompts unless their source hash matches.
- UI polish rule: do not use browser-native `title` tooltips, `alert/confirm/prompt`, native `<select>` dropdowns, or default file-upload chrome for user-facing interactions. Use custom Ant-like components such as `ce-has-tooltip`, custom modals, custom dropdowns, custom toast, and custom upload buttons.
- `画面风格调整` 的“跑最新版效果”自动化必须走 Cloudflare Worker 代理 `/api/style-eval/run-latest`。Worker 先校验 Supabase 登录用户是管理员，再用 Cloudflare 环境变量 `KPM_APP_SECRET` 代签名调用 `box.xdf.cn` 的一键同款和素材修改接口。不要把 KPM app secret 写入前端、仓库或静态 JSON。当前自动回填效果链接；截图自动回填还需要单独接入截图 runner 或浏览器渲染服务。
- `material-modify` 返回 `text/event-stream`，不要在 Cloudflare Worker 请求里同步 `response.text()` 等完整生成流结束，否则登录后真实生成可能被 Cloudflare 中断成原生 502。当前做法是等待一键同款创建会话和素材修改接口接收请求后立即回填预览链接，长流只在后台 drain；后续更稳方案应改成队列/任务表/截图 runner 的异步任务架构。
- `跑最新版效果` 不能只 fire-and-forget 素材修改，也不能收到 `material-modify` 响应头后立即 cancel SSE body；该接口需要保持 `text/event-stream` 长连接才会真正生成第二版。当前临时方案是读取 SSE 到 `finalResult` 或 600 秒超时，成功后才回填链接；长期更稳方案仍应改成后端任务队列/状态表/截图 runner。
- `跑最新版效果` 的 KPM 基础地址应使用用户提供的正式域名 `http://box.xdf.cn`。如果 Cloudflare 环境变量误设为 `box.test.xdf.cn`，该测试域名可能触发 Cloudflare DNS/local IP 类错误，导致线上按钮 502；Worker 当前会对 `box.test.xdf.cn` 做保护性改写到正式域名。
- KPM 实测必须用 `https://box.xdf.cn`：`http://box.xdf.cn/kpm-api/...` 会出现 connection reset，容易导致 Cloudflare Worker 原生 502。即使文档示例写 `BASE_URL = "http://box.xdf.cn"`，站点 Worker 也要规范化为 HTTPS。
- 一键同款接口文档示例写成功 `code: 0`，但 2026-07-05 实测 `https://box.xdf.cn/kpm-api/skill/create-same-by-one-click` 成功返回 `code: 200` 且包含 `data.conversationId`。Worker 判断成功必须兼容 `0` 和 `200`，否则会把成功误判为 502。
- 2026-07-05 用户线上实测“跑最新版效果”从 502 变为 504，原因是前台请求同步等待 `material-modify` SSE 到 `finalResult`，10 分钟仍未完成就由 Worker 返回 `MATERIAL_MODIFY_TIMEOUT`。改为异步任务形态：`run-latest` 创建一键同款会话后立即返回 `202 + runId + previewUrl`，Worker 通过 `ctx.waitUntil` 后台继续 drain `material-modify` SSE，并把状态写入 Cloudflare Cache；前端通过 `/api/style-eval/run-status/{runId}` 轮询 `created/modifying/done/timeout/failed`。这能避免前台 504，但若 Cloudflare 后台任务被平台提前中止，仍需要升级到真正的队列/持久化 runner。
- 2026-07-05 继续实测发现 `ctx.waitUntil` 后台 drain 也不能保证 KPM 第二版真正生成，用户打开链接仍是“一键同款第一版”。当前改成 `/api/style-eval/run-latest` 直接返回 `application/x-ndjson` 流式进度：Worker 一边调用一键同款和 `material-modify`，一边把 `creating/created/progress/done/timeout/failed/heartbeat` 推给前端。用户需要保持页面打开直到 `done`，但这个形态能持续保持浏览器、Worker、KPM SSE 三方连接，比后台任务更可靠。若这仍失败，下一步才是独立常驻 runner/队列。
- 2026-07-05 用户反馈流式版线上仍出现“接口返回 502”。将 `/api/style-eval/run-latest` 的响应实现从 `new ReadableStream({ async start() {} })` 改为 Cloudflare 更稳的 `TransformStream + writer + ctx.waitUntil(streamJob)`，避免 Pages 边缘层把长上游流打成 502；同时前端非 JSON 错误会展示响应体摘要，`material-modify` 非 200 也会带上上游正文摘要。
- 2026-07-05 用户反馈最后一轮请求等待后仍显示 `素材修改仍在上游处理中，600 秒内未收到最终完成信号`。这说明需要区分“旧 localStorage timeout 残留”和“新请求确实连上 material-modify 但没收到 finalResult”。新增诊断字段：`chunkCount`、`stepCount`、`unparsedLineCount`、`rawPreview`，并在 `material-modify` HTTP 200 后立即推送 `素材修改接口已连接`。后续判断以这些字段为准：`chunkCount=0` 是上游不推流；`chunkCount>0 stepCount=0 rawPreview 有内容` 是解析格式不匹配；`stepCount>0` 才说明真正进入 KPM 生成步骤。
- 2026-07-05 诊断原始片段为 `{"code":401,"data":"https://box.test.xdf.cn/","msg":"未登录或登录已过期，请重新登录"}`，说明 `/kpm-api/api/material-modify` 是网页登录态接口，不适合 Worker app-sign 调用。素材修改必须改用 app-sign 风格路径 `/kpm-api/skill/material-modify`，并且如果上游返回业务 JSON 错误，要立即失败展示，不应等 600 秒。
- 2026-07-05 用户反馈 `This ReadableStream only supports a single pending read request at a time.` Root cause: `readMaterialModifyStream()` used `Promise.race([reader.read(), timeout])`; when timeout won, the previous `reader.read()` stayed pending and the next loop started a second read. Fix: use one sequential `reader.read()` and cancel the reader with a timeout timer.
- 2026-07-05 因一键同款支持自定义 `materialName` 和 `zipUrl`，`画面风格调整` 的最新版效果证据必须按 `materialName` 分组展示。每个素材 tab 独立保存效果链接、截图、评分、状态、问题、解决方法、下一版参考提示词和生成状态，避免不同源素材的测评结果互相覆盖。旧的单条 `latest` 本地记录需要自动迁移成默认素材 tab。
- `画面风格调整` 的最新版截图维护要支持多入口上传：点击截图占位区、点击自定义上传按钮、拖拽图片到截图区、复制截图后在截图区粘贴；同一次操作可上传多张，并保留轮播查看。不要退回浏览器默认文件上传控件。
- 2026-07-05 已从 `/Users/jolin/Downloads/7月2日调整画面风格-效果测试 (2).csv` 的 `风格提示词7` 列入库 19 个基础风格的 V7 提示词。`data/style-eval-seed.json` 中 V7 是当前最终候选，V6 及之前版本保留为历史过程版；页面缓存版本为 `20260705-style-v7`。
