## Project Notes

- This repository is the source of truth for the courseware evaluation site deployed at `https://coursewareeval.chenjialing.cn/`.
- Maintain changes in this git checkout, then push to GitHub so Cloudflare Pages can deploy the same code users run.
- The app is a static `index.html` plus a Cloudflare Worker proxy in `_worker.js`.
- Explain technical decisions in product terms: what problem is being solved and how users are affected.
