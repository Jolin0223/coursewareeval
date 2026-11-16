# -*- coding: utf-8 -*-
from pathlib import Path
import json,shutil,difflib,hashlib,zipfile,argparse
ap=argparse.ArgumentParser();ap.add_argument('assets',type=Path);ap.add_argument('package',type=Path);args=ap.parse_args();assets=args.assets.resolve();pkg=args.package.resolve();root=Path(__file__).resolve().parent.parent
assert not pkg.exists();(pkg/'prompts').mkdir(parents=True)
prev=json.loads((root/'button-layout-review/data.json').read_text());data={**prev,'title':'按钮自适应与Q版反馈图标 · 待确认','date':'2026-11-16','revision':'20261116-feedback-icons-v2','baseline':'改前：11月13日按钮留白与顺序版。改后：明确解除固定宽度，新增按需使用的Q版反馈与工具图标。','files':[],'changes':[],'cases':{},'evidence':{},'issues':[],'history':'评审候选已整理；尚未更新业务CDN或服务端提示词。历史HTML不会自动重生成；覆盖同URL的CSS会影响动态引用的历史课件。','excluded':'字体、封面、SDK、Retry/Try again与必要完成操作规则保留。无关课件不增判分、星级或工具。'}
data['cases']={'宽度复测':{'after':'https://oss-xlss.test.xdf.cn/ig-kpm/multiple/2026-11/16-FjZqWkJVQpOYNRkHahvVOA/index.html'},'Q版反馈':{'after':'/feedback-icons-review/demo/#feedback'},'工具扩充':{'after':'/feedback-icons-review/demo/#tools'}}
data['evidence']={'宽度复测':'11月16日4例均未覆盖CDN的固定width:248px。CSS/DOM核对证据，非浏览器视觉通过。','Q版反馈':'用户要求对勾、叉号、星星更圆润Q版且亮眼；无外框默认、底座按需；仅规划需要时优先使用，允许主题定制。','工具扩充':'用户确认新增提示、画笔、橡皮擦、撤销；仅在相关功能已规划时使用。'}
policy='仅当规划需要正误判断或星级反馈时，优先复用对应圆润图标，不因图标库提供能力而新增判分、星级或奖励流程。星星数量、反馈文案和展示时机按用户意图与实际玩法决定；用户明确指定其他形式或主题需要定制时可使用相应素材。反馈默认无外框，直接嵌入选项或结果区；独立反馈需增强识别时才选用底座。反馈状态不是按钮，不加无意义点击。提示、画笔、橡皮擦、撤销也只在相应功能已规划时选用，撤销与重试不可混用。'
impl='反馈符号使用`cb-icon-correct`、`cb-icon-incorrect`、`cb-icon-star`、`cb-icon-star-empty`。正误用`cb-feedback`容器（答错加`cb-feedback--incorrect`），内部直接放`<span class="cb-icon cb-icon-correct" aria-hidden="true"></span>`；选项内可加`cb-feedback--inline`，需要底座才额外包`cb-feedback-symbol`。星级用`cb-stars`容器。容器提供可见文案或无障碍名称，不只靠颜色表达结果。反馈不套`cb`按钮基类。'
roles={
'prompt.material-design-learning-tablet':'规划反馈与工具时，'+policy,
'agent.architect.instruction':'在相关taskDetails中明确反馈是否需要、文案、时机、星级规则及是否需要底座，并选定对应图标；'+policy,
'agent.modify.architect.instruction':'仅本轮涉及反馈或工具时，在相关taskDetails中落实：'+policy+'不扩改无关评分、题目流程或工具功能。',
'agent.developer.instruction':'实现已规划反馈和工具时，'+policy+impl,
'agent.modify.developer.instruction':'仅实现本轮涉及的反馈或工具，'+policy+impl+'保留无关评分与题目流程。',
'agent.reviewer.instruction':'审查已规划反馈与工具：'+policy+'检查状态语义、实际动作和图标匹配，不能因有对应图标而要求所有课件都使用。',
'agent.modify.reviewer.instruction':'仅审查本轮涉及的反馈与工具：'+policy+'不因本次样式检查扩大到无关评分或流程。',
'agent.fixer.instruction':'仅修复任务涉及反馈或工具时，'+policy+'仍只修改当前允许文件，不新增无关功能或跨文件改动。',
'agent.modify.fixer.instruction':'仅修复任务涉及反馈或工具时，'+policy+'仍只修改当前允许文件，不新增无关功能或跨文件改动。'}
widths={
'prompt.material-design-learning-tablet':'文字按钮必须随内容扩宽，不能把组件的默认宽度当作固定尺寸；预留最长文案状态与图标所需空间。',
'agent.architect.instruction':'在相关taskDetails中明确文字按钮按内容自适应宽度，组件与页面样式均不得以固定width限制内容；不能仅通过padding或min-width处理拥挤，父布局也不得强制压缩内容。',
'agent.modify.architect.instruction':'本轮涉及按钮排版时，明确文字按钮按内容自适应宽度，组件与页面样式均不得以固定width限制内容；不能仅通过padding或min-width处理拥挤，父布局也不得强制压缩内容。',
'agent.developer.instruction':'文字按钮使用`width:max-content`或等效的内容自适应布局，确保组件与页面样式叠加后仍能随文字和图标扩宽；不得以固定width限制内容，也不能仅通过padding或min-width处理拥挤。父布局不得强制压缩内容。',
'agent.modify.developer.instruction':'本轮涉及文字按钮排版时，在当前文件职责内使用`width:max-content`或等效的内容自适应布局，确保组件与页面样式叠加后仍能随文字和图标扩宽；不得以固定width限制内容，也不能仅通过padding或min-width处理拥挤。父布局不得强制压缩内容。',
'agent.reviewer.instruction':'核对组件和本地样式叠加后的按钮宽度，而非只检查padding；仍继承固定width、或仅加min-width导致长文案拥挤时不能判通过。',
'agent.modify.reviewer.instruction':'仅本轮涉及文字按钮排版时，核对组件和本地样式叠加后的宽度，而非只检查padding；仍继承固定width、或仅加min-width导致拥挤时不能判通过。',
'agent.fixer.instruction':'修复涉及文字按钮宽度时，在当前允许文件内解除固定width对相关按钮的限制，按内容扩宽；不能只加padding或min-width，不扩改其他文件。',
'agent.modify.fixer.instruction':'修复涉及文字按钮宽度时，在当前允许文件内解除固定width对相关按钮的限制，按内容扩宽；不能只加padding或min-width，不扩改其他文件。'}
extra='；答对反馈→`cb-icon-correct`；答错反馈→`cb-icon-incorrect`；已得星→`cb-icon-star`；未得星→`cb-icon-star-empty`；提示→`cb-icon-hint`；画笔→`cb-icon-pencil`；橡皮擦→`cb-icon-eraser`；撤销上一步→`cb-icon-undo`'
raw=[]
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def units(s):return len(s.encode('utf-16-le'))//2
for m in prev['files']:
 key=m['key'];old=m['revised'];lines=old.splitlines(True);idx=next(i for i,l in enumerate(lines) if '内容距按钮左右边缘各至少24px' in l)
 lines[idx]=lines[idx].rstrip('\n')+widths[key]+'\n';indent='    *   ' if key.startswith('prompt.') else '';lines.insert(idx+1,indent+roles[key]+'\n');new=''.join(lines)
 if '图标调用清单（16个' in new:
  new=new.replace('图标调用清单（16个','图标调用清单（24个')
  anchor='完成状态或必要结束操作→`cb-icon-done`（仅在语义匹配时使用，不代表必须添加完成按钮）'
  assert new.count(anchor)==1;new=new.replace(anchor,anchor+extra)
 (pkg/'prompts'/(key+'.txt')).write_text(new)
 ol=old.splitlines(True);nl=new.splitlines(True);changes=[]
 for tag,i,j,k,l in difflib.SequenceMatcher(None,ol,nl).get_opcodes():
  if tag=='equal':continue
  before=''.join(ol[i:j]);after=''.join(nl[k:l]);catalog='图标调用清单（24个' in after
  c={'id':f"FI{m['order']:02d}-{len(changes)+1}",'file':key,'title':'扩充24项图标清单，按功能选用' if catalog else '解除固定宽度；按需使用Q版反馈与工具','kind':'替换' if before else '新增','where':m['title']+' → 组件/反馈规则','why':'16个功能图标缺少反馈与画写工具；用户已确认四个工具，反馈无外框按需使用。' if catalog else '复测中增加留白仍继承固定宽度；反馈需要更圆润，且不能强制所有课件新增正误或星级。','cases':['宽度复测','Q版反馈','工具扩充'],'note':'CSS需先在测试环境部署后再启用新增类名；本轮未替换业务CDN。','requires':[],'old':before,'new':after,'start':units(''.join(ol[:i])),'end':units(''.join(ol[:j])),'line':i+1};changes.append(c);data['changes'].append(c)
 diff=''.join(difflib.unified_diff(ol,nl,fromfile='按钮留白与顺序/'+key+'.txt',tofile='Q版反馈与自适应/'+key+'.txt'));raw.append(diff)
 data['files'].append({**m,'original':old,'revised':new,'sourceSha256':sha(old),'revisedSha256':sha(new),'originalChars':units(old),'revisedChars':units(new),'changed':True,'changes':changes,'issues':[],'diff':[]})
data['devTasks']=[{'id':'FI-DEV1','title':'先更新CSS测试资源，再接提示词','links':[],'cases':['Q版反馈','工具扩充'],'action':'本轮2.2.1候选CSS增加8个类名，原16类保持。先在测试环境上传并验证资源加载，再启用九份提示词。示例仍沿用现有正式资源URL，不能提前上线会引用尚不存在类名的提示词。','done':'24类名可用；反馈默认无底座，星级不自动生成；原按钮图标不回退。'},{'id':'FI-DEV2','title':'组件自适应与宿主布局检查','links':[],'cases':['宽度复测'],'action':'cb-text默认width:max-content、min-width:248px、左右28px、gap16px。检查模型本地样式与宿主布局是否仍写死width；仅修改组件不能覆盖所有高优先级错误样式。','done':'实际字体下Try again、提交答案、重新练习及更长文案完整可读，原事件不变。'},{'id':'FI-DEV3','title':'历史资源影响与回归','links':[],'cases':['宽度复测','Q版反馈'],'action':'先以版本化测试资源验证。覆盖原CDN同URL会改变动态引用它的历史课件按钮尺寸；打包旧CSS的课件不会自动升级。确认迁移范围与回滚后再发布业务资源。','done':'检查固定集、长按钮、反馈与真实支持端；不能把DOM/源码核对当作实屏通过。'}]
out=root/'feedback-icons-review';out.mkdir();(out/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2));shutil.copytree(pkg/'prompts',out/'prompts');(pkg/'评审数据.json').write_text(json.dumps(data,ensure_ascii=False,indent=2));(pkg/'改动对比.diff').write_text('\n'.join(raw));(out/'changes.diff').write_text('\n'.join(raw))
readme='# Q版反馈与按钮自适应｜待确认\n\n基于11月13日按钮留白与顺序版修订，九份完整TXT与精确diff已附。\n\n1. 解除固定宽度，不能只加padding/min-width。\n2. 反馈仅在规划需要时优先复用，不自动新增判分、星级或奖励；默认无外框，主题定制可用其他素材。\n3. 四个工具图标已获确认，按已规划功能使用。\n4. 九环节按职责区分，修改和修复保持任务边界；字体、封面、SDK、Retry/Try again规则保留。\n\n研发先上传测试CSS，再启用新增类名。业务CDN尚未替换；同URL覆盖会影响动态引用的旧课件，先版本化测试再决定发布范围。CSS另包交付，不混入TXT包。\n'
(pkg/'交付说明.md').write_text(readme);(out/'README.md').write_text(readme)
with zipfile.ZipFile(str(pkg)+'.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in pkg.rglob('*'):
  if p.is_file():z.write(p,p.relative_to(pkg.parent))
shutil.copyfile(str(pkg)+'.zip',out/'complete-prompts.zip')
(out/'css').mkdir();shutil.copyfile(assets/'icon.css',out/'css/standard-icon.css');shutil.copyfile(assets/'manifest.json',out/'css/manifest.json');shutil.copyfile(assets/'README.md',out/'css/README.md');shutil.copytree(assets/'svg',out/'css/svg')
with zipfile.ZipFile(out/'icon-css-2.2.1.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in (out/'css').rglob('*'):
  if p.is_file():z.write(p,p.relative_to(out/'css'))
shutil.copyfile(out/'icon-css-2.2.1.zip',assets/'icon-css-2.2.1.zip')
demo=out/'demo';demo.mkdir()
for n in ['index.html','review.js','icon.css','README.md','changes.diff']:shutil.copyfile(assets/n,demo/n)
shutil.copytree(assets/'fonts',demo/'fonts')
overview='''function feedbackIconsOverview(){return `<div class="revision-note"><strong>按钮宽度从组件修正，反馈只按规划需要使用</strong><p>①解除固定width，不能只加padding。②正误与星星更圆润、明亮，默认无外框。③新增提示、画笔、橡皮擦、撤销，按已规划功能选用。④不自动增加判分、奖励或工具，允许主题定制。</p><p>基线是上一轮“按钮留白与顺序”；下方逐项显示原文与改后内容，九份TXT完整可下载。</p><p><a href="/feedback-icons-review/demo/" target="_blank">打开组件视觉与交互评审 ↗</a> · <a href="/feedback-icons-review/css/standard-icon.css" download>下载CSS</a> · <a href="/feedback-icons-review/icon-css-2.2.1.zip">下载CSS开发包</a> · <a href="/feedback-icons-review/complete-prompts.zip">下载九份完整TXT</a></p></div><table class="overview"><thead><tr><th>环节</th><th>修改</th><th>对比</th></tr></thead><tbody>${DATA.files.map(f=>`<tr><td>${f.order}. ${esc(f.title)}</td><td>${f.changes.length}处：宽度落实、反馈边界${f.revised.includes('图标调用清单（24个')?'、图标清单':''}</td><td><button data-file="${f.key}">原文 / 改后 ↗</button></td></tr>`).join('')}</tbody></table><p>${esc(DATA.history)}</p>${devGuide()}`}\n'''
for name in ['system-prompt-review.html','font-packaging-review.html','resource-contract-review.html']:
 p=root/name;s=p.read_text();assert 'feedback-icons-data' not in s
 s=s.replace('<button data-round="button-layout">','<button data-round="feedback-icons">11月16日 Q版反馈与按钮自适应 · 最新候选</button><button data-round="button-layout">',1).replace('11月13日 按钮留白与图标顺序 · 最新候选','11月13日 按钮留白与图标顺序 · 上一轮')
 block='<script id="feedback-icons-data" type="application/json">'+json.dumps(data,ensure_ascii=False).replace('</','<\\/')+'</script>\n'
 s=s.replace('<script>const BUTTON_LAYOUT_DATA=',block+'<script>const FEEDBACK_ICONS_DATA=JSON.parse(document.getElementById("feedback-icons-data").textContent);const BUTTON_LAYOUT_DATA=',1).replace('const roundData={',"const roundData={'feedback-icons':FEEDBACK_ICONS_DATA,",1)
 if name=='system-prompt-review.html':s=s.replace("?requestedRound:'button-layout';","?requestedRound:'feedback-icons';")
 s=s.replace('function renderOverview(){',overview+"function renderOverview(){if(round==='feedback-icons')return feedbackIconsOverview();",1)
 s=s.replace('function caseHtml(id){','function caseHtml(id){if(round===\'feedback-icons\')return `<a class="case-link" href="${esc(DATA.cases[id].after)}" target="_blank" rel="noopener">${esc(id)} ↗</a>`;',1)
 s=s.replace("if(round==='button-layout'){$('#round-label')", "if(round==='feedback-icons'){$('#round-label').textContent=DATA.title;$('#review-title').textContent='Q版反馈与按钮自适应';$('#review-intro').textContent=DATA.baseline;$('#export-candidate').textContent='下载9份完整候选 TXT';}\nif(round==='button-layout'){$('#round-label')",1)
 s=s.replace("download(round==='button-layout'?", "download(round==='feedback-icons'?(selectedOnly?'Q版反馈_已采纳.zip':'Q版反馈_九份完整候选.zip'):round==='button-layout'?",1);p.write_text(s)
print('Built',len(data['files']),'files',len(data['changes']),'changes')
