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
- `套用玩法` current prompts are the 16 Markdown files under `03-套用模板提示词/正在调试的提示词`, not the old short Excel adaptation notes. `data/inspiration-template-seed.json` stores the full Markdown prompt in `adaptationText` plus `promptSourceFile` and `promptSourceHash`. The page, one-click入库, copy fallback, and Excel export should use `getTemplateCurrentPrompt()` so stale localStorage drafts do not override newer source prompts unless their source hash matches.
- UI polish rule: do not use browser-native `title` tooltips, `alert/confirm/prompt`, native `<select>` dropdowns, or default file-upload chrome for user-facing interactions. Use custom Ant-like components such as `ce-has-tooltip`, custom modals, custom dropdowns, custom toast, and custom upload buttons.
- `画面风格调整` 的“跑最新版效果”自动化必须走 Cloudflare Worker 代理 `/api/style-eval/run-latest`。Worker 先校验 Supabase 登录用户是管理员，再用 Cloudflare 环境变量 `KPM_APP_SECRET` 代签名调用 `box.xdf.cn` 的一键同款和素材修改接口。不要把 KPM app secret 写入前端、仓库或静态 JSON。当前自动回填效果链接；截图自动回填还需要单独接入截图 runner 或浏览器渲染服务。
- `material-modify` 返回 `text/event-stream`，不要在 Cloudflare Worker 请求里同步 `response.text()` 等完整生成流结束，否则登录后真实生成可能被 Cloudflare 中断成原生 502。当前做法是等待一键同款创建会话和素材修改接口接收请求后立即回填预览链接，长流只在后台 drain；后续更稳方案应改成队列/任务表/截图 runner 的异步任务架构。
