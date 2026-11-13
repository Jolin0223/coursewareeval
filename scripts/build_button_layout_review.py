# -*- coding: utf-8 -*-
"""Build the button-layout prompt package and append a preserved review round."""
from pathlib import Path
import argparse, json, hashlib, difflib, shutil, zipfile

ap=argparse.ArgumentParser();ap.add_argument('baseline',type=Path);ap.add_argument('output',type=Path)
args=ap.parse_args();base=args.baseline.resolve();pkg=args.output.resolve();root=Path(__file__).resolve().parent.parent
assert not pkg.exists(), 'Use a new output directory'
pkg.mkdir();(pkg/'prompts').mkdir()
prev=json.loads((root/'completion-intent-review/data.json').read_text())
common='普通操作按钮默认采用“左图标、右文字”，图标与文字作为一组整体居中；上一题采用“左箭头＋文字”，下一题采用“文字＋右箭头”。在1920×1080逻辑画布下，图标与文字组成的内容距按钮左右边缘各至少24px，图标与文字间距12–16px，并随舞台统一缩放。按钮宽度由实际字体、字号、最长状态文案、图标与留白共同决定；长文案优先加宽按钮并调整本区布局，不机械套用固定宽度，不让内容贴边、进入圆角区域或被裁切，不压缩图标。'
rules={
'prompt.material-design-learning-tablet':'规划按钮时，'+common+'上述规则用于实际需要的图标加文字按钮；用户明确指定优先，整图封面沿用原规则。',
'agent.architect.instruction':'在相关taskDetails中明确按钮顺序、内容留白与宽度自适应要求：'+common+'用户明确指定优先，整图封面沿用原规则。',
'agent.modify.architect.instruction':'仅本轮涉及按钮排版时，在相关taskDetails中落实：'+common+'只调整相关按钮及必要的本区布局，不改变文案含义、事件与题目流程；用户明确指定优先，整图封面沿用原规则。',
'agent.developer.instruction':'实现图标加文字按钮时，'+common+'按内容设置自适应宽度和内边距，文字保持单行，图标禁止flex收缩；不得用overflow裁切掩盖拥挤。用户明确指定优先，整图封面沿用原规则。',
'agent.modify.developer.instruction':'仅本轮涉及按钮排版时，'+common+'按内容设置自适应宽度和内边距，文字保持单行，图标禁止flex收缩，不用overflow裁切掩盖拥挤。保留相关按钮原有文案含义和事件，不扩改无关功能；用户明确指定优先，整图封面沿用原规则。',
'agent.reviewer.instruction':'审查实际需要的图标加文字按钮及其最长文案状态：'+common+'发现固定宽度、图标收缩或裁切导致拥挤时指出对应按钮；用户明确指定优先，整图封面沿用原规则。',
'agent.modify.reviewer.instruction':'仅审查本轮涉及的按钮排版及其最长文案状态：'+common+'同时核对未改变原有文案含义、事件与无关流程；用户明确指定优先，整图封面沿用原规则。',
'agent.fixer.instruction':'仅修复任务涉及按钮排版时，'+common+'在当前允许文件内修正相关布局，不扩改其他文件或无关功能，保留文案含义和事件；用户明确指定优先，整图封面沿用原规则。',
'agent.modify.fixer.instruction':'仅修复任务涉及按钮排版时，'+common+'在当前允许文件内修正相关布局，不扩改其他文件或无关功能，保留文案含义和事件；用户明确指定优先，整图封面沿用原规则。'
}
data={**prev,'title':'按钮留白与图标顺序 · 待研发确认','revision':'20261113-button-layout-v1','baseline':'改前：完成操作按场景版。改后：补充按钮自适应宽度、左右留白及图标顺序；其他既有规则保留。','compatibleBaseline':None,'removedChangeIds':[],'files':[],'changes':[],'issues':[], 'cases':{},'evidence':{},'history':'本轮为待研发确认候选，尚未更新服务端提示词或复测生成效果。历史课件HTML不会自动改变。','excluded':'不改字体、封面、图标资源和按钮动作；不改当前CSS资源，不批量修改历史课件。'}
evidence=[('01','Try again：文字偏长，两侧留白不足','1f3a07d8-dc43-42dc-bd39-96a87c039d8b'),('02','Try again：图标和文字贴近两侧圆角','2123c54a-5d9b-48d0-9635-547d62dd0d62'),('03','提交答案：文字贴左边，提交图标放在文字右侧','99bb57d9-912b-4c99-8faa-4210a622ed49'),('04','重新练习：文字接近右侧圆角','3fac6e9b-f57d-40d3-b39c-e0f7205a17cb')]
(pkg/'evidence').mkdir()
for n,title,uid in evidence:
 src=Path('/var/folders/lm/dz748v591f1_lh4rz2k9_k1r0000gn/T')/f'codex-clipboard-{uid}.png'
 shutil.copyfile(src,pkg/'evidence'/f'button-{n}.png')
 data['cases']['B'+n]={'title':title,'after':f'/button-layout-review/evidence/button-{n}.png'}
 data['evidence']['B'+n]='用户提供的真实课件截图：'+title+'。未据截图推定Query或会话ID。'
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def units(s):return len(s.encode('utf-16-le'))//2
raw=[]
for m in prev['files']:
 key=m['key'];old=(base/'prompts'/(key+'.txt')).read_text();assert old==m['revised'],key
 lines=old.splitlines(True);idx=next(i for i,l in enumerate(lines) if '可见短文案' in l and '`Retry`' in l)
 indent='    *   ' if key.startswith('prompt.') else ''
 lines.insert(idx+1,indent+rules[key]+'\n');new=''.join(lines)
 if key.startswith('prompt.'):
  new=new.replace('按钮宽度建议220-280px、高度建议88-96px','按钮宽度可从220-280px起按实际内容扩展（不是宽度上限），高度建议88-96px')
 (pkg/'prompts'/(key+'.txt')).write_text(new)
 ol=old.splitlines(True);nl=new.splitlines(True);changes=[]
 for tag,i,j,k,l in difflib.SequenceMatcher(None,ol,nl).get_opcodes():
  if tag=='equal':continue
  c={'id':f"BL{m['order']:02d}-{len(changes)+1}",'file':key,'title':'按钮按内容扩宽，补足留白并统一图文顺序','kind':'新增' if i==j else '替换','where':m['title']+' → 功能按钮规则','why':'长文案挤入圆角区域；提交答案图标顺序与普通操作不一致。原建议宽度不应被当作上限。','cases':list(data['cases']),'note':'24px与12–16px均为1920×1080逻辑画布尺寸，随舞台缩放；效果待测试环境验证。','requires':[],'old':''.join(ol[i:j]),'new':''.join(nl[k:l]),'start':units(''.join(ol[:i])),'end':units(''.join(ol[:j])),'line':i+1}
  changes.append(c);data['changes'].append(c)
 diff=''.join(difflib.unified_diff(ol,nl,fromfile='完成操作按场景/'+key+'.txt',tofile='按钮留白与顺序/'+key+'.txt'))
 raw.append({'file':key+'.txt','before':old,'after':new,'newRule':rules[key],'diff':diff})
 data['files'].append({**m,'original':old,'revised':new,'sourceSha256':sha(old),'revisedSha256':sha(new),'originalChars':units(old),'revisedChars':units(new),'changed':True,'changes':changes,'issues':[],'diff':[]})
data['devTasks']=[{'id':'BL-DEV1','title':'替换九份完整提示词','links':[],'cases':['B03'],'action':'按本轮完整TXT更新对应环节；任务协议、单文件修复范围保持不变。','done':'普通操作左图右文；上一题左箭头，下一题右箭头；未新增无关按钮。'},{'id':'BL-DEV2','title':'检查组件固定宽度是否覆盖布局','links':[],'cases':['B01','B02','B04'],'action':'现有CSS资源继续使用。生成课件应按真实内容设置宽度与内边距；若宿主组件存在强制固定宽度或max-width限制，由研发检查并消除与内容自适应的冲突，不要求本轮改CDN。','done':'在1920×1080画布下两侧至少24px，图文间距12–16px；舞台缩放后比例保持，最长状态文案不挤入圆角。'},{'id':'BL-DEV3','title':'部署后定向复测','links':[],'cases':list(data['cases']),'action':'复测Try again、重新练习、提交答案及上一题/下一题；检查长文案、图标顺序、缩放与原有点击动作。','done':'截图中的拥挤与顺序问题消除；按钮仍在画布内，事件和Retry/Try again范围保持。历史HTML不会自动修复，需另行指定后重新生成或定向修改。'}]
readme='''# 按钮留白与图标顺序｜待研发确认

基线：20261113-系统提示词候选-完成操作按场景。本包包含九份完整TXT，不是增量片段。

- 普通操作：左图标、右文字，作为一组居中；上一题左箭头，下一题右箭头。
- 1920×1080逻辑画布下，两侧至少24px，图文间距12–16px，随舞台整体缩放。
- 宽度按实际字体、最长文案、图标和留白自适应；220–280px只是起始参考，不是上限。优先加宽并调整本区布局，不压缩图标或裁切文字。
- 九环节按职责落实；修改与修复只处理本轮涉及范围，修复仍只修改当前允许文件。

原Retry/Try again、必要结束操作、字体随包、图标资源、封面与SDK规则保留。整图封面仍沿用原规则；用户明确指定优先。

研发：替换prompts内对应九份TXT，检查固定宽度是否覆盖自适应规则，部署后复测四张截图所示文案及方向导航按钮。CSS资源无需本轮重新上传，本包不携带CSS以避免覆盖独立资源更新。

当前仅发布评审候选；尚未更新服务端提示词或验证生成效果。历史HTML不会自动改变，定向修改或重新生成需另行指定。

evidence目录保留用户提供的四张问题截图；未推定其Query或会话ID。改动对比.diff为相对上述基线的精确差异。
'''
(pkg/'交付说明.md').write_text(readme)
(pkg/'评审数据.json').write_text(json.dumps({'title':data['title'],'baseline':base.name,'changes':raw},ensure_ascii=False,indent=2))
(pkg/'改动对比.diff').write_text('\n'.join(x['diff'] for x in raw))
(pkg/'SHA256.json').write_text(json.dumps({str(p.relative_to(pkg)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(pkg.rglob('*')) if p.is_file()},ensure_ascii=False,indent=2))
with zipfile.ZipFile(str(pkg)+'.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(pkg.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(pkg.parent))
out=root/'button-layout-review';out.mkdir(exist_ok=True)
(out/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
for folder in ['prompts','evidence']:shutil.copytree(pkg/folder,out/folder,dirs_exist_ok=True)
for a,b in [('交付说明.md','README.md'),('改动对比.diff','changes.diff')]:shutil.copyfile(pkg/a,out/b)
shutil.copyfile(str(pkg)+'.zip',out/'complete-prompts.zip')
overview='''function buttonLayoutOverview(){return `<div class="revision-note"><strong>按钮按内容扩宽，文字不再挤到圆角</strong><p>普通操作：左图标、右文字；上一题：← 文字；下一题：文字 →。</p><p>1920×1080逻辑画布下，内容左右各至少24px，图文间距12–16px，随舞台缩放。220–280px只是起始参考，不是宽度上限。</p><p>基于上一轮“完成操作按场景”的九份完整TXT，仅新增按钮排版约束并澄清原宽度建议；原有动作、字体、封面与图标资源规则保留。</p><p><a href="/button-layout-review/complete-prompts.zip">下载九份完整TXT＋说明＋问题截图</a> · <a href="/button-layout-review/changes.diff">下载精确diff</a></p></div><h2>本轮问题证据 · 用户提供的真实截图</h2><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px">${Object.entries(DATA.cases).map(([id,c])=>`<figure style="margin:0;padding:16px;background:white;border:1px solid #dbe5e7;border-radius:12px"><a href="${esc(c.after)}" target="_blank" rel="noopener"><img src="${esc(c.after)}" alt="${esc(c.title)}" style="max-width:100%;height:126px;object-fit:contain"></a><figcaption>${esc(id+' · '+c.title)}</figcaption></figure>`).join('')}</div><p>截图未附会话标识，不推定Query或会话ID。规则执行效果需部署后复测。</p><table class="overview"><thead><tr><th>环节</th><th>本轮改动</th><th>查看</th></tr></thead><tbody>${DATA.files.map(f=>`<tr><td>${f.order}. ${esc(f.title)}</td><td>${f.changes.length}处；按该环节职责落实排版</td><td><button data-file="${f.key}">原文 / 改后 ↗</button></td></tr>`).join('')}</tbody></table>${devGuide()}`}\n'''
for name in ['system-prompt-review.html','font-packaging-review.html','resource-contract-review.html']:
 p=root/name;s=p.read_text();assert 'button-layout-data' not in s
 s=s.replace('<button data-round="completion-intent">','<button data-round="button-layout">11月13日 按钮留白与图标顺序 · 最新候选</button><button data-round="completion-intent">',1)
 block='<script id="button-layout-data" type="application/json">'+json.dumps(data,ensure_ascii=False).replace('</','<\\/')+'</script>\n'
 s=s.replace('<script>const COMPLETION_INTENT_DATA=',block+'<script>const BUTTON_LAYOUT_DATA=JSON.parse(document.getElementById("button-layout-data").textContent);const COMPLETION_INTENT_DATA=',1)
 s=s.replace('const roundData={',"const roundData={'button-layout':BUTTON_LAYOUT_DATA,",1)
 if name=='system-prompt-review.html':s=s.replace("?requestedRound:'completion-intent';","?requestedRound:'button-layout';")
 s=s.replace('function renderOverview(){',overview+"function renderOverview(){if(round==='button-layout')return buttonLayoutOverview();",1)
 s=s.replace('function caseHtml(id){','function caseHtml(id){if(round===\'button-layout\')return `<a class="case-link" href="${esc(DATA.cases[id].after)}" target="_blank" rel="noopener">${esc(id)} · 问题截图 ↗</a>`;',1)
 s=s.replace("if(round==='completion-intent'){$('#round-label')", "if(round==='button-layout'){$('#round-label').textContent=DATA.title;$('#review-title').textContent='按钮留白与图标顺序';$('#review-intro').textContent=DATA.baseline;$('#export-candidate').textContent='下载9份完整候选 TXT';}\nif(round==='completion-intent'){$('#round-label')",1)
 s=s.replace("download(round==='completion-intent'?", "download(round==='button-layout'?(selectedOnly?'按钮留白与顺序_已采纳.zip':'按钮留白与顺序_九份完整候选.zip'):round==='completion-intent'?",1)
 p.write_text(s)
print('Built',pkg,'files:',len(data['files']),'changes:',len(data['changes']))
