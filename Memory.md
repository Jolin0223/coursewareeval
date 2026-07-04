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
