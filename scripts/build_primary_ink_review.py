from pathlib import Path
import json,hashlib,difflib,shutil
R=Path(__file__).resolve().parent.parent
B=Path('/Users/jolin/Documents/互动课件AI Agent/Obsidian Vault/03-AI互动课件制作')
source=B/'20261117-主按钮前景色修复';base=B/'20261116-系统提示词完整复核/prompts';out=R/'primary-ink-review';out.mkdir(exist_ok=True)
meta=json.loads((R/'prompt-final-audit-review/data.json').read_text())
d={k:meta[k] for k in ['title','date','baseline','revision','compatibleBaseline','removedChangeIds','history','excluded']}
d.update(title='主按钮前景色 · 6份最小同步',date='2026-11-17',baseline='改前：11月16日完整复核交付稿；改后：11月17日主按钮前景色修复包。仅解决浅色主按钮被固定成白字的问题。',revision='20261117-primary-ink',compatibleBaseline=None,removedChangeIds=[],history='提示词花括号、变量与输出协议未改。评审网站已更新不代表业务CSS或测试环境提示词已部署；实屏与新一轮生成仍待验收。',excluded='24个图标定义、普通/选中/禁用规则不改；方案设计及两个修复智能体原样保留。')
d.update(files=[],changes=[],issues=[],cases={'M01':{'after':'https://oss-xlss.test.xdf.cn/ig-kpm/multiple/2026-11/17-swcipPQXR-KNCa_pV8FdIw/index.html'}},evidence={'M01':'将下一题改为浅蓝色后，cb-primary仍固定白色；--cb-ink的深灰设置没有生效。消息41492，快照dffcf595acb64b27907ea476ab0bcc4a。'})
units=lambda s:len(s.encode('utf-16-le'))//2
for f in meta['files']:
 name=f['key']+'.txt';old=(base/name).read_text();new=(source/'prompts'/name).read_text();cs=[]
 if old!=new:
  # Single contiguous edit per file: exclude unchanged prose so review is compact.
  start=0
  while old[start]==new[start]:start+=1
  tail=0
  while old[-tail-1]==new[-tail-1]:tail+=1
  end=len(old)-tail;ne=len(new)-tail
  kind='architect' if 'architect' in name else 'developer' if 'developer' in name else 'reviewer'
  title={'architect':'主按钮规划同时给出前景色','developer':'主按钮按底色设置文字与图标颜色','reviewer':'审查实际配色，不再默认必须白字'}[kind]
  why={'architect':'让代码任务拿到主按钮专用前景色，避免只给普通按钮变量。','developer':'现有白字规定与浅色背景冲突；改用组件支持的前景色变量。','reviewer':'审查原文仍假定主操作白字，需同步避免把深色前景误改回白色。'}[kind]
  c=dict(id=f"PI{f['order']:02d}",file=f['key'],title=title,kind='替换',where=f['title']+' · 按钮主题色',why=why,cases=['M01'],note='其余完整原文保留；无新增CSS花括号。需先部署支持该变量的CSS。',requires=[],old=old[start:end],new=new[start:ne],start=units(old[:start]),end=units(old[:end]),line=old[:start].count('\n')+1)
  cs=[c];d['changes'].append(c)
 d['files'].append({**{k:f[k] for k in ['key','title','phase','purpose','order']},'original':old,'revised':new,'newline':'LF','sourceSha256':hashlib.sha256(old.encode()).hexdigest(),'revisedSha256':hashlib.sha256(new.encode()).hexdigest(),'originalChars':units(old),'revisedChars':units(new),'changed':bool(cs),'changes':cs,'issues':[],'diff':[],'unchangedReason':'本轮无须调整，逐字保留11月16日完整复核文本。'})
d['devTasks']=[{'id':'PI-CSS','title':'公共组件新增前景色变量','links':['PI02','PI03','PI04','PI06','PI07','PI08'],'cases':['M01'],'action':'cb-primary的color由white改为var(--cb-primary-ink,#fff)。先隔离测试再替换共用CDN及刷新缓存；仅需上传standard-icon.css，manifest不是运行依赖。','done':'未配置变量保留白字；浅底设置深色变量后文字/图标同步变色，普通与禁用按钮不回退。'}, {'id':'PI-LOCAL','title':'处理课件自身颜色覆盖','links':[],'cases':['M01'],'action':'已有浅底白字课件需在目标按钮或实际容器设置--cb-primary-ink。局部高优先级固定白色样式须改为读取变量；仅换CSS不会自动为旧课件选色。','done':'实际计算前景色生效；不批量重写历史HTML，数学验证副本JS未改。'}, {'id':'PI-QA','title':'测试环境生成与修改验收','links':[],'cases':[],'action':'9份完整TXT先经真实模板引擎解析，再测试浅底深字、深底浅字、普通及禁用状态。当前只完成静态与隔离检查。','done':'生成和修改两条流程及实屏通过；不把浏览器超时视作通过。'}]
(out/'data.json').write_text(json.dumps(d,ensure_ascii=False,indent=2));(source/'评审数据.json').write_text(json.dumps(d,ensure_ascii=False,indent=2))
for src,dst in [('complete-prompts.zip','complete-prompts.zip'),('icon-css-2.2.3.zip','icon-css-2.2.3.zip'),('主按钮前景色修复-最终交付.zip','delivery.zip'),('交付说明.md','README.md'),('改动对比.diff','changes.diff'),('验收页.html','component-check.html'),('组件校验.json','component-checks.json'),('交付校验.json','package-checks.json')]:shutil.copy(source/src,out/dst)
shutil.copytree(source/'prompts',out/'prompts',dirs_exist_ok=True);shutil.copytree(source/'css',out/'css',dirs_exist_ok=True)
# Render-only fixture is enough online; keep the full copied courseware in downloadable ZIP.
p=out/'component-check.html';s=p.read_text().replace('href="example/数学修改验证/index.html"','href="delivery.zip"').replace('打开数学修改验证副本 ↗','下载含数学验证副本的交付包').replace('href="交付说明.md"','href="README.md"');p.write_text(s)
p=R/'system-prompt-review.html';s=p.read_text();assert 'primary-ink-data' not in s
s=s.replace('<button data-round="final-audit">','<button data-round="primary-ink">11月17日 主按钮前景色 · 当前交付</button><button data-round="final-audit">',1).replace('11月16日 完整文本复核 · 当前交付','11月16日 完整文本复核')
block='<script id="primary-ink-data" type="application/json">'+json.dumps(d,ensure_ascii=False).replace('</','<\\/')+'</script>\n'
s=s.replace('<script>const FINAL_AUDIT_DATA=',block+'<script>const PRIMARY_INK_DATA=JSON.parse(document.getElementById("primary-ink-data").textContent);const FINAL_AUDIT_DATA=',1)
s=s.replace('const roundData={',"const roundData={'primary-ink':PRIMARY_INK_DATA,",1).replace("?requestedRound:'final-audit'","?requestedRound:'primary-ink'",1)
s=s.replace('function caseHtml(id){', '''function caseHtml(id){if(round==='primary-ink')return `<a class="case-link" href="${esc(DATA.cases[id].after)}" target="_blank" rel="noopener">${esc(id)} · 原问题课件 ↗</a>`;''',1)
overview='''if(round==='primary-ink')return `<div class="revision-note"><strong>主按钮支持深浅前景色：6份提示词最小同步，3份原样保留</strong><p>${esc(DATA.baseline)}</p><p><a href="/primary-ink-review/delivery.zip">下载最终交付包</a> · <a href="/primary-ink-review/complete-prompts.zip">9份完整TXT</a> · <a href="/primary-ink-review/icon-css-2.2.3.zip">CSS组件包</a> · <a href="/primary-ink-review/component-check.html" target="_blank">真实组件配色对比 ↗</a></p></div><h2>对应问题：浅蓝按钮仍是白色文字和箭头</h2><p>${esc(DATA.evidence.M01)} ${caseHtml('M01')} · <a href="https://box.test.xdf.cn/kpm/5e0bac516f914efdb6fa23cb553c5e3d" target="_blank">测试环境会话 ↗</a></p><p>静态与隔离检查：浅蓝底配白色对比度1.72，配深灰后7.36；浏览器实屏及新一轮生成待验收。</p><h2>提示词环节 · 点击查看原文与改后</h2><table class="overview"><tbody>${DATA.files.map(f=>`<tr><td><button data-file="${f.key}">${esc(f.title)} ↗</button></td><td>${f.changed?'1处最小改动':'原样保留'}</td><td>${esc(f.changed?f.changes[0].title:f.unchangedReason)}</td></tr>`).join('')}</tbody></table><h2>CSS独立改动 · 不放入系统提示词</h2><div class="diff"><section class="diff-side"><h3>改前</h3><pre class="before"><span class="del-mark">color: white;</span></pre></section><section class="diff-side"><h3>改后</h3><pre class="after"><span class="add-mark">color: var(--cb-primary-ink, #fff);</span></pre></section></div><p>未指定变量时保留白字；普通按钮继续使用 --cb-ink。只变更这一条声明，24个图标定义及其他状态规则不变。若课件局部样式固定白色，仍需同步修正。<a href="/primary-ink-review/changes.diff">查看完整diff</a></p>${devGuide()}`;'''
s=s.replace('function renderOverview(){','function renderOverview(){'+overview,1)
s=s.replace("if(round==='final-audit'){$('#round-label')","if(round==='primary-ink'){$('#round-label').textContent=DATA.title;$('#review-title').textContent='主按钮前景色 · 最小修复';$('#review-intro').textContent=DATA.baseline;$('#export-candidate').textContent='下载9份完整TXT';}\nif(round==='final-audit'){$('#round-label')",1)
s=s.replace('function exportZip(selectedOnly){',"function exportZip(selectedOnly){if(round==='primary-ink'&&!selectedOnly){location.href='/primary-ink-review/complete-prompts.zip';return;}",1)
p.write_text(s)
print('Built',len(d['files']),'files',len(d['changes']),'review cards')
