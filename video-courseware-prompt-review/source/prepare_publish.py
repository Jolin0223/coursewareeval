# -*- coding: utf-8 -*-
from pathlib import Path
import json,re,shutil,zipfile,hashlib,runpy,html
R=Path(__file__).resolve().parent;O=R.parent/'20261116-完整审查与正文收口提示词评审'
REPO=Path('/Users/jolin/Documents/互动课件AI Agent/.tmp/eval-video-r13-1118');W=REPO/'video-courseware-prompt-review'
D=json.loads((R/'review-data.json').read_text());P=R/'视频互动课件_完整提示词包_20261118_r13_联动候选'
shutil.copy2(P/'11_发布前校验/校验结果.json',R/'校验结果.json')
manifest={str(x.relative_to(P)):hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(P.rglob('*')) if x.is_file() and x.name!='MANIFEST-SHA256.json'}
(P/'MANIFEST-SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
with zipfile.ZipFile(R/D['zip'],'w',zipfile.ZIP_DEFLATED) as z:
 for x in sorted(P.rglob('*')):
  if x.is_file():z.write(x,x.relative_to(P.parent))
# Archive r12 with its own exact previous/dev/full text data.
c=runpy.run_path(str(R/'build_review.py'))['compare']
old=json.loads((O/'review-data.json').read_text());hist=json.loads((R/'history-index.json').read_text())
for f in old['files']:f['diffDev']=c(f['dev'],f['final']);f['diffPrevious']=c(f['previous'],f['final'])
old['zip']='complete-prompts.zip'
H=W/'history/r12';H.mkdir(exist_ok=True)
tabs=''.join('<a href="'+('../../' if x['id']=='r13' else '../'+x['id']+'/')+'">'+html.escape(x['title'])+'</a>' for x in hist)
archive='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>视频提示词历史 · r12</title><style>body{font:15px/1.8 system-ui,sans-serif;margin:28px;color:#193638;background:#f3f7f5}nav{display:flex;flex-wrap:wrap;gap:8px}a,button,select{padding:9px;border:1px solid #cbdad4;background:white;color:#24594d;border-radius:5px}h1{font-size:26px}.diff{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:1px;background:#cadbd4;border:1px solid #cadbd4;margin-top:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.9 system-ui;background:white;margin:0;padding:20px}.del-mark{background:#ffd9dc;color:#8e2632;text-decoration:line-through}.add-mark{background:#c9efd5;color:#145432}.tools{display:flex;flex-wrap:wrap;gap:10px}@media(max-width:800px){body{margin:16px}.diff{grid-template-columns:1fr}}</style><nav>__TABS__</nav><h1>11月16日 完整审查 · r12历史交付</h1><p>保留当轮全文与差异，仅供追溯。用户反馈星期一部署后问题仍存在；实际生效内容需开发版本hash核对。当前联动候选请回到r13。</p><div class="tools"><select id="stage" aria-label="环节"></select><select id="baseline" aria-label="对照基线"><option value="diffDev">开发(3).md → r12</option><option value="diffPrevious">r11 → r12</option></select><button id="txt">下载本环节TXT</button><a href="complete-prompts.zip">当轮完整包</a></div><p id="reason"></p><div class="diff"><div><strong>改前全文 · 红色删除</strong><pre id="old"></pre></div><div><strong>r12全文 · 绿色新增</strong><pre id="new"></pre></div></div><script id="data" type="application/json">__DATA__</script><script>const D=JSON.parse(document.querySelector('#data').textContent),S=document.querySelector('#stage'),B=document.querySelector('#baseline');D.files.forEach((f,i)=>S.add(new Option(f.id+' '+f.name,i)));function render(){const f=D.files[+S.value],d=f[B.value];document.querySelector('#old').innerHTML=d.old;document.querySelector('#new').innerHTML=d.new;document.querySelector('#reason').textContent=f.reason}S.onchange=B.onchange=render;document.querySelector('#txt').onclick=()=>{const f=D.files[+S.value],a=document.createElement('a'),u=URL.createObjectURL(new Blob([f.final],{type:'text/plain;charset=utf-8'}));a.href=u;a.download=f.filename;a.click();setTimeout(()=>URL.revokeObjectURL(u),2000)};render()</script></html>'''
(H/'index.html').write_text(archive.replace('__TABS__',tabs).replace('__DATA__',json.dumps(old,ensure_ascii=False).replace('<','\\u003c')))
(H/'data.json').write_text(json.dumps(old,ensure_ascii=False,indent=2))
shutil.copy2(O/'视频互动课件_完整提示词包_20261116_r12.zip',H/'complete-prompts.zip')
for n in ['index.html','history-index.json','效果问题与改动清单.md','开发接入与保护边界.md','校验结果.json',D['zip']]:shutil.copy2(R/n,W/n)
shutil.copy2(R/D['zip'],W/'prompt-package.zip')
(W/'README.md').write_text('# 视频互动课件提示词评审\n\n当前为11月18日r13联动候选。入口index.html；正文及差异在source/review-data.json；包内README为接入边界。\n\n本次未部署Box配置、后端或历史快照。M1候选第2/4/5条需与运行层及检查器联动。\n')
for f in D['files']:
 (W/'prompts'/f['filename']).write_text(f['final'])
source=W/'source';source.mkdir(exist_ok=True)
for n in ['build_candidate.py','build_delivery.py','build_review.py','prepare_publish.py','review-data.json','exact-patches.json']:
 shutil.copy2(R/n,source/n)
shutil.copy2(P/'11_发布前校验/preflight.py',source/'preflight.py')
(W/'发布版本.json').write_text(json.dumps(dict(revision=D['revision'],date='2026-11-18',scope='review_site_and_candidate_only',package=D['zip'],packageSha256=hashlib.sha256((W/D['zip']).read_bytes()).hexdigest(),historyRounds=len(hist),changedAgainstR12=[f['id'] for f in D['files'] if f['previous']!=f['final']],boxDeployment='not_performed'),ensure_ascii=False,indent=2))
print(json.dumps({'ready':str(W),'zipBytes':(W/D['zip']).stat().st_size,'history':len(hist)},ensure_ascii=False))
