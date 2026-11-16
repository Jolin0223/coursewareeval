# -*- coding: utf-8 -*-
from pathlib import Path
from urllib.parse import quote
import json,shutil,difflib,hashlib,zipfile
project=Path('/Users/jolin/Documents/互动课件AI Agent');root=project/'.tmp/coursewareeval-icons-font-20261112';business=project/'Obsidian Vault/03-AI互动课件制作';assets=business/'20261116-按钮自适应与反馈图标候选';pkg=business/'20261116-反馈图标接入修复-2.2.2';assert not pkg.exists();(pkg/'css').mkdir(parents=True);(pkg/'prompts').mkdir()
base=(assets/'baseline-icon.css').read_text();css=base.replace('Release 2.1.2-css.','Candidate 2.2.2-css.').replace('.cb-text{width:248px;height:92px;border-radius:46px}', '.cb-text{width:max-content;min-width:248px;height:auto;min-height:92px;padding:22px 28px;gap:16px;border-radius:46px;white-space:nowrap}.cb-text>span{flex-shrink:0}')
# Standalone base deliberately precedes optional container enhancements. No regex mutation of compound selectors.
css+='''\n/* Every cb-icon renders independently; containers only enhance layout/color. */
.cb-icon{display:inline-block;box-sizing:border-box;width:64px;height:64px;flex-shrink:0;vertical-align:middle;background-color:currentColor;-webkit-mask:var(--cb-icon) center/contain no-repeat;mask:var(--cb-icon) center/contain no-repeat;pointer-events:none}
.cb-icon-correct{color:var(--cb-feedback-correct,#31b956)}
.cb-icon-incorrect{color:var(--cb-feedback-incorrect,#ed626d)}
.cb-icon-star{color:var(--cb-star-earned,#ffbc24)}
.cb-icon-star-empty{color:var(--cb-star-empty,#abb9a0)}
.cb-feedback{--cb-feedback-ink:#31b956;--cb-feedback-light:#6bd44d;--cb-feedback-bg:#e8f6db;display:inline-flex;align-items:center;gap:18px;color:var(--cb-feedback-ink);font-family:inherit;font-size:40px;font-weight:600;line-height:1.3;vertical-align:middle}
.cb-feedback--incorrect{--cb-feedback-ink:#ed626d;--cb-feedback-light:#ff9292;--cb-feedback-bg:#fff0ec}
.cb-feedback-symbol{width:96px;height:96px;border-radius:50%;background:var(--cb-feedback-bg);display:inline-flex;align-items:center;justify-content:center;flex-shrink:0}
.cb-feedback .cb-icon{width:64px;height:64px;background-color:var(--cb-feedback-ink);background-image:linear-gradient(145deg,var(--cb-feedback-light,var(--cb-feedback-ink)),var(--cb-feedback-ink));filter:drop-shadow(0 2px 0 rgba(35,86,40,.12))}
.cb-stars{--cb-star-earned:#ffbc24;--cb-star-light:#ffe164;--cb-star-empty:#abb9a0;display:inline-flex;align-items:center;gap:12px;vertical-align:middle;line-height:0}
.cb-stars .cb-icon{width:64px;height:64px}
.cb-stars .cb-icon-star{color:var(--cb-star-earned);background-image:linear-gradient(145deg,var(--cb-star-light,var(--cb-star-earned)),var(--cb-star-earned));filter:drop-shadow(0 2px 0 rgba(161,105,0,.16))}
.cb-stars .cb-icon-star-empty{color:var(--cb-star-empty)}
.cb-feedback--inline{display:inline-flex;gap:8px;vertical-align:middle}.cb-feedback--inline .cb-icon{width:36px;height:36px;filter:none}
/* Button symbols inherit button ink, including disabled and primary states. */
.cb .cb-icon{color:inherit}
'''
for p in sorted((assets/'svg').glob('*.svg')):css+='\n.cb-icon-'+p.stem+'{--cb-icon:url("data:image/svg+xml,'+quote(p.read_text(),safe='')+'")}\n'
(pkg/'css/standard-icon.css').write_text(css);shutil.copytree(assets/'svg',pkg/'css/svg');m=json.loads((assets/'manifest.json').read_text());m.update(version='2.2.2-css-candidate',status='独立图标渲染修复候选；业务CDN未替换');(pkg/'css/manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2));(pkg/'css/changes.diff').write_text(''.join(difflib.unified_diff((assets/'icon.css').read_text().splitlines(True),css.splitlines(True),fromfile='2.2.1',tofile='2.2.2')))
prev=json.loads((root/'feedback-icons-review/data.json').read_text());data={**prev,'title':'反馈图标接入修复 · 2.2.2待确认','revision':'20261116-feedback-fix-v1','baseline':'改前：Q版反馈与按钮自适应最终措辞版。改后：图标独立显示、尺寸与间距明确、选项反馈无底座、撤销与清空分清。','files':[],'changes':[],'history':'本轮CSS和提示词为评审候选，业务CDN与服务端未替换。基于现有4例做局部组件验证，不等于模型重新生成或实屏通过。','evidence':{'F01正误':'数学题对勾缺少基础渲染结构，且出现圆底。','F02尺寸':'英语课件正误缺容器；星星font-size为200px，实际宽高64px。','F03间距':'绘画按钮同时使用gap16px和margin-right16px。','F04清空':'颜色探索将撤销上一步图标用于清空全部。'},'cases':{},'issues':[]}
urls=['16-kV2JDEn5T2KzCjcSauyjjA','16-QfhQv6npQDqEW4sAD0VqIw','16-w9JU2vcvTYeNnvyfMUksVg','16-8Bc7IyL2QCuXWNtaANK0Ug']
for k,u in zip(data['evidence'],urls):data['cases'][k]={'after':'https://oss-xlss.test.xdf.cn/ig-kpm/multiple/2026-11/'+u+'/index.html'}
oldimpl='反馈符号使用`cb-icon-correct`、`cb-icon-incorrect`、`cb-icon-star`、`cb-icon-star-empty`。正误用`cb-feedback`容器（答错加`cb-feedback--incorrect`），内部直接放`<span class="cb-icon cb-icon-correct" aria-hidden="true"></span>`；选项内可加`cb-feedback--inline`，需要底座才额外包`cb-feedback-symbol`。星级用`cb-stars`容器。容器提供可见文案或无障碍名称，不只靠颜色表达结果。反馈不套`cb`按钮基类。'
newimpl='反馈符号可独立使用`<span class="cb-icon cb-icon-correct" aria-hidden="true"></span>`，答错、已得星、未得星分别换为`cb-icon-incorrect`、`cb-icon-star`、`cb-icon-star-empty`。`cb-feedback`与`cb-stars`只用于组织布局和配色，不是显示图标的必要条件；需要独立反馈底座时才使用`cb-feedback-symbol`。通过`width`和`height`设置图标实际尺寸，不用`font-size`代替；例如放大星星使用`.cb-stars .cb-icon{width:120px;height:120px}`。为反馈提供可见文案或无障碍名称，不只靠颜色表达结果，不套`cb`按钮基类。'
tech='图标是CSS图形，尺寸由width/height控制，不能仅设置font-size；图标与文字间距只用gap或单侧margin之一，不重复叠加。'
role={
'prompt.material-design-learning-tablet':'选项内正误符号直接嵌入，不额外套圆底、边框或阴影；独立反馈确需增强识别时才规划底座。撤销只恢复上一步，清空全部是另一动作，不用撤销图标表示清空。',
'agent.architect.instruction':'在相关taskDetails中写明选项反馈不加底座、图标实际宽高和图文间距；撤销只恢复上一步，清空全部不使用撤销图标。'+tech,
'agent.modify.architect.instruction':'仅本轮涉及时，在taskDetails中写明选项反馈不加底座、图标实际宽高和图文间距；撤销只恢复上一步，清空全部不使用撤销图标。'+tech,
'agent.developer.instruction':tech+'选项内正误符号不额外套圆底、边框或阴影；撤销仅恢复上一步，清空全部不使用`cb-icon-undo`，按真实动作选择图标，库中没有时采用同风格SVG。',
'agent.modify.developer.instruction':'本轮涉及相关样式或动作时，'+tech+'选项内正误符号不额外套圆底、边框或阴影；撤销仅恢复上一步，清空全部不使用`cb-icon-undo`，缺少匹配图标时用同风格SVG，不改无关逻辑。',
'agent.reviewer.instruction':'检查正误符号在实际结构中具有可见尺寸、颜色及遮罩，不能仅凭类名判通过；'+tech+'选项内反馈不额外套底座；`cb-icon-undo`只能表示撤销上一步，不表示清空全部。',
'agent.modify.reviewer.instruction':'仅审查本轮涉及部分：正误符号须有可见尺寸、颜色及遮罩，不能仅凭类名判通过；'+tech+'选项内反馈不额外套底座；撤销上一步不能替代清空全部。',
'agent.fixer.instruction':'仅修复任务涉及时，在当前允许文件内补齐图标显示与width/height，清除重复图文间距和选项内多余底座；`cb-icon-undo`不用于清空全部。保留无关逻辑，不跨文件修改。',
'agent.modify.fixer.instruction':'仅修复任务涉及时，在当前允许文件内补齐图标显示与width/height，清除重复图文间距和选项内多余底座；`cb-icon-undo`不用于清空全部。保留无关逻辑，不跨文件修改。'}
def units(s):return len(s.encode('utf-16-le'))//2
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
diffs=[]
for f in prev['files']:
 old=f['revised'];new=old.replace(oldimpl,newimpl);lines=new.splitlines(True);i=next(i for i,l in enumerate(lines) if '仅当规划需要正误判断或星级反馈时' in l);lines[i]=lines[i].rstrip('\n')+role[f['key']]+'\n';new=''.join(lines);ol=old.splitlines(True);nl=new.splitlines(True);cs=[]
 for tag,i,j,k,l in difflib.SequenceMatcher(None,ol,nl).get_opcodes():
  if tag=='equal':continue
  c={'id':f"FX{f['order']:02d}-{len(cs)+1}",'file':f['key'],'title':'反馈可独立显示，明确尺寸、间距与动作语义','kind':'替换','where':f['title']+' → 反馈图标规则','why':'专项测试暴露正误空白、星星放大无效、间距叠加及撤销错用清空。','cases':list(data['cases']),'note':'需要先部署2.2.2组件测试资源，再启用这轮提示词。无关玩法不新增反馈。','requires':[],'old':''.join(ol[i:j]),'new':''.join(nl[k:l]),'start':units(''.join(ol[:i])),'end':units(''.join(ol[:j])),'line':i+1};cs.append(c);data['changes'].append(c)
 data['files'].append({**f,'original':old,'revised':new,'sourceSha256':sha(old),'revisedSha256':sha(new),'originalChars':units(old),'revisedChars':units(new),'changes':cs});(pkg/'prompts'/(f['key']+'.txt')).write_text(new);diffs.append(''.join(difflib.unified_diff(ol,nl,fromfile='反馈按需/'+f['key']+'.txt',tofile='接入修复/'+f['key']+'.txt')))
data['devTasks']=[{'id':'FX-DEV1','title':'先部署CSS 2.2.2测试资源','links':[],'cases':['F01正误','F02尺寸'],'action':'cb-icon独立带尺寸、背景及mask；容器仅增强配色和布局；从SVG源文件重建定义，修正对勾选择器拼接。24类名称保持。','done':'不带cb/cb-feedback/cb-stars容器的图标可独立显示；原按钮和带容器用法保持正常。'},{'id':'FX-DEV2','title':'提示词与组件一同验收','links':[],'cases':list(data['cases']),'action':'替换九份完整TXT后重新跑生成：检查选项反馈无圆底、图标用width/height控制、gap与margin不叠加、撤销只撤上一步。','done':'真实浏览器与目标端通过。局部DOM验证不能代替新一轮模型生成与实屏验收。'},{'id':'FX-DEV3','title':'历史资源边界','links':[],'cases':[],'action':'先测试新版本资源；原CDN覆盖会影响动态引用的历史课件。现有HTML中额外圆底、font-size和错误图标语义不会仅靠CSS全部自动修复。','done':'发布前明确影响范围；本轮没有自动改写历史HTML或业务CDN。'}]
readme='''# 反馈图标接入修复 2.2.2

本包为待确认候选；业务CDN与服务端提示词未替换。

- cb-icon自带默认64px宽高、背景和mask，可独立显示。正误与星星有默认颜色；工具继承文字颜色。容器仅增强布局、配色，原24类名与图形保持。
- 修复了CSS生成过程中的对勾选择器拼接问题；图标定义从源SVG重新生成，不再正则拼接复合选择器。
- 大小用width/height，不用font-size；间距只用gap或单侧margin，不叠加。
- 选项正误默认无底座；独立反馈按需。撤销只恢复上一步，清空不能使用undo。
- 不强制新增判分、星级或工具；主题定制仍按用户意图。修改和修复只处理当前任务范围。

开发先在测试环境部署css/standard-icon.css，再应用prompts九份完整TXT。CDN覆盖会影响动态引用的旧HTML；已打包CSS不会自动变更。已有额外底座、尺寸误用、语义错配需要另行改HTML，不能承诺只换CSS全部解决。

本轮提供源码/隔离DOM检查，非浏览器实屏或全量生成通过。manifest是交付清单，不是浏览器依赖。SVG已内嵌CSS。
'''
(pkg/'README.md').write_text(readme);(pkg/'css/README.md').write_text(readme);(pkg/'评审数据.json').write_text(json.dumps(data,ensure_ascii=False,indent=2));(pkg/'改动对比.diff').write_text('\n'.join(diffs))
out=root/'feedback-fix-review';out.mkdir();shutil.copytree(pkg/'prompts',out/'prompts');shutil.copytree(pkg/'css',out/'css');(out/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2));(out/'README.md').write_text(readme);(out/'changes.diff').write_text('\n'.join(diffs))
for name,folder in [('complete-prompts.zip',pkg/'prompts'),('icon-css-2.2.2.zip',pkg/'css')]:
 with zipfile.ZipFile(out/name,'w',zipfile.ZIP_DEFLATED) as z:
  for p in folder.rglob('*'):
   if p.is_file():z.write(p,p.relative_to(folder))
  if name=='complete-prompts.zip':z.writestr('README.md',readme)
 shutil.copyfile(out/name,pkg/name)
# keep the approved visual demo, point it to the repaired library
shutil.copytree(root/'feedback-icons-review/demo',out/'demo');(out/'demo/icon.css').write_text(css)
p=out/'demo/index.html';s=p.read_text().replace('2.2.1','2.2.2').replace('本地候选评审','修复候选评审');s=s.replace('<section id="feedback">','<section class="panel"><h2>独立图标接入检查</h2><p>下面没有反馈父容器；图标本身应直接显示。</p><div style="display:flex;gap:24px;align-items:center"><span class="cb-icon cb-icon-correct" role="img" aria-label="答对"></span><span class="cb-icon cb-icon-incorrect" role="img" aria-label="答错"></span><span class="cb-icon cb-icon-star" role="img" aria-label="已得星"></span><span class="cb-icon cb-icon-star-empty" role="img" aria-label="未得星"></span></div></section><section id="feedback">');p.write_text(s)
overview='''function feedbackFixOverview(){return `<div class="revision-note"><strong>修复图标接入，而不是继续堆视觉形容词</strong><p>图标可独立显示；大小用width/height；间距不叠加；选项反馈无底座；撤销不当清空。仅在玩法需要时优先复用，保留主题定制。</p><p><a href="/feedback-fix-review/demo/" target="_blank">组件预览</a> · <a href="/feedback-fix-review/css/standard-icon.css" download>下载2.2.2 CSS</a> · <a href="/feedback-fix-review/icon-css-2.2.2.zip">CSS开发包</a> · <a href="/feedback-fix-review/complete-prompts.zip">九份完整TXT</a></p></div><table class="overview"><thead><tr><th>环节</th><th>对比</th></tr></thead><tbody>${DATA.files.map(f=>`<tr><td>${f.order}. ${esc(f.title)}</td><td><button data-file="${f.key}">原文 / 改后 ↗</button></td></tr>`).join('')}</tbody></table><p>${esc(DATA.history)}</p>${devGuide()}`}\n'''
for n in ['system-prompt-review.html','font-packaging-review.html','resource-contract-review.html']:
 p=root/n;s=p.read_text();assert 'feedback-fix-data' not in s;s=s.replace('<button data-round="feedback-icons">','<button data-round="feedback-fix">11月16日 反馈接入修复 · 最新候选</button><button data-round="feedback-icons">',1).replace('11月16日 Q版反馈与按钮自适应 · 最新候选','11月16日 Q版反馈与按钮自适应 · 上一轮')
 block='<script id="feedback-fix-data" type="application/json">'+json.dumps(data,ensure_ascii=False).replace('</','<\\/')+'</script>\n';s=s.replace('<script>const FEEDBACK_ICONS_DATA=',block+'<script>const FEEDBACK_FIX_DATA=JSON.parse(document.getElementById("feedback-fix-data").textContent);const FEEDBACK_ICONS_DATA=',1).replace('const roundData={',"const roundData={'feedback-fix':FEEDBACK_FIX_DATA,",1)
 if n=='system-prompt-review.html':s=s.replace("?requestedRound:'feedback-icons';","?requestedRound:'feedback-fix';")
 s=s.replace('function renderOverview(){',overview+"function renderOverview(){if(round==='feedback-fix')return feedbackFixOverview();",1).replace("if(round==='feedback-icons')return `<a class=", "if(round==='feedback-icons'||round==='feedback-fix')return `<a class=",1)
 s=s.replace("if(round==='feedback-icons'){$('#round-label')", "if(round==='feedback-fix'){$('#round-label').textContent=DATA.title;$('#review-title').textContent='反馈图标接入修复';$('#review-intro').textContent=DATA.baseline;$('#export-candidate').textContent='下载9份完整候选 TXT';}\nif(round==='feedback-icons'){$('#round-label')",1).replace("download(round==='feedback-icons'?", "download(round==='feedback-fix'?(selectedOnly?'反馈接入修复_已采纳.zip':'反馈接入修复_九份完整.zip'):round==='feedback-icons'?",1);p.write_text(s)
print(pkg,len(data['changes']))
