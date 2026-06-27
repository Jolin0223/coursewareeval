# Memory.md - Courseware Evaluation Site

## 2026-06-28

- GitHub repo: `https://github.com/Jolin0223/coursewareeval`
- Local git checkout: `/Users/jolin/Desktop/部署到github上的项目/coursewareeval`
- Previous loose local folder `/Users/jolin/Desktop/部署到github上的项目/eval-site` is not a git repo and should be treated as a backup/reference only.
- Runtime issue after Supabase config update: dashboard snapshot failed with `task.feedbacks[email].trim is not a function`.
- Root cause: `feedbacks` contains non-rater system fields such as `failure_reasons`, whose value is an object. Dashboard NLP and export code assumed every `feedbacks` entry was a string keyed by an email.
- Fix direction: filter rater keys through `isRaterEmail()` and normalize feedback values through `normalizeFeedbackText()`, so non-string/system feedback fields no longer crash dashboard rendering or Excel export.
