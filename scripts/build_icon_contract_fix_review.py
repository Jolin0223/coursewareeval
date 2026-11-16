from pathlib import Path
import json,difflib,hashlib,zipfile,re,shutil
project=Path.cwd();biz=project/'Obsidian Vault/03-AI互动课件制作';repo=project/'.tmp/coursewareeval-icons-font-20261112';base=biz/'20261116-反馈图标接入修复-2.2.2';pkg=biz/'20261116-图标审查与模板安全修复';pkg.mkdir(exist_ok=True);(pkg/'prompts').mkdir(exist_ok=True)
data=json.loads((base/'评审数据.json').read_text());data.update(title='图标审查与模板安全修复 · 待开发确认',revision='20261116-icon-contract-fix-v1',baseline='改前：2.2.2完整交付版（含未转义CSS示例）。改后：两处示例改为自然语言，审查与修复使用准确图标清单；共6份修改，3份保留。',history='开发已确认上轮花括号模板错误，转义修复后4/4生成成功。本轮继续修正F01审查误改，尚未部署服务端或重新生成验收。CSS保持2.2.2，不需要重传。',excluded='保留方案、架构、字体、封面、SDK及已通过的玩法规则。历史HTML不自动修改。',changes=[],files=[],issues=[],cases={'F01图标误改':{'after':'https://oss-xlss.test.xdf.cn/ig-kpm/multiple/2026-11/16-5kzWyeevQj6ULOM9fF71dw/index.html'},'F02正确接入':{'after':'https://oss-xlss.test.xdf.cn/ig-kpm/multiple/2026-11/16-wMdnXQq3T_mHgDxG0QFfAw/index.html'}},evidence={'F01图标误改':'审查错误地将真实类名判不存在，修复改成check/right/refresh；正误隐藏、下一题白块。','F02正确接入':'正确使用平台类名，正误独立显示，星星宽高120px。'})
icons=['play','pause','autoplay','sound','mute','show','hide','menu','outline','back','home','close','retry','next','submit','done','correct','incorrect','star','star-empty','hint','pencil','eraser','undo'];names=['cb-icon-'+i for i in icons]
css=(base/'css/standard-icon.css').read_text();assert all(re.search(r'\.'+re.escape(n)+r'\s*\{',css) for n in names)
allow='平台图标类名以本提示词给出的清单为准：'+ '、'.join('`'+n+'`' for n in names)+'。这些类名均可用，不得根据其他图标库习惯判为不存在，或擅自替换为清单外名称。`cb-icon-check`、`cb-icon-right`、`cb-icon-refresh`不在本清单中，不能作为上述内置图标的替代名；用户代码明确自行定义的图标另按其实际定义核对。'
review='审查图标时，'+allow+'无法读取外部CSS不等于类名不存在，不据此报错或要求重画。正误使用`cb-icon-correct`与`cb-icon-incorrect`，下一题使用`cb-icon-next`；同时核对HTML初始类名、JS切换类名与CSS状态选择器一致，答题后符号不被display、visibility或opacity隐藏。选项内正误反馈不加独立圆底、边框或阴影，也不使用伪元素绕过此要求；选项卡片本身的正常边框和选中样式可保留。只报告有代码或清单依据的错误，不推测远程资源内容。'
fix='修复图标时，'+allow+'审查意见若与本清单冲突，保留合法类名，只修复可定位的引用、尺寸、颜色或显示状态问题。正误使用`cb-icon-correct`与`cb-icon-incorrect`，下一题使用`cb-icon-next`。在当前允许文件内保持HTML、JS与CSS的类名契约一致；需联动其他文件时按现有任务流程说明依赖，不自行换名造成不匹配。选项内正误反馈移除额外底座及其伪元素，保留符号、选项卡片正常样式和业务事件。仍按原输出协议只输出当前指定文件代码。'
checks=[];diffs=[]
def units(s):return len(s.encode('utf-16-le'))//2
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
for f in json.loads((base/'评审数据.json').read_text())['files']:
 name=f['key']+'.txt';old=(base/'prompts'/name).read_text();new=old
 if f['key'] in ['agent.developer.instruction','agent.modify.developer.instruction']:
  needle='例如放大星星使用`.cb-stars .cb-icon{width:120px;height:120px}`。';assert new.count(needle)==1;new=new.replace(needle,'例如将星星图标的width和height均设置为120px。');new.format(task_content='TASK',all_code_content='CODE')
 elif 'reviewer' in f['key']:new=new.rstrip()+'\n'+('仅审查本轮修改范围。' if '.modify.' in f['key'] else '')+review+'\n'
 elif 'fixer' in f['key']:new=new.rstrip()+'\n'+('仅修复本轮修改范围。' if '.modify.' in f['key'] else '')+fix+'\n'
 ol=old.splitlines(True);nl=new.splitlines(True);cs=[]
 for tag,i,j,k,l in difflib.SequenceMatcher(None,ol,nl).get_opcodes():
  if tag=='equal':continue
  added=''.join(nl[k:l]);removed=''.join(ol[i:j]);newrisk=[x for x in re.findall(r'\{[^{}]*\}',added) if x not in re.findall(r'\{[^{}]*\}',removed)];assert not newrisk,(name,newrisk)
  c={'id':f"IC{f['order']:02d}-{len(cs)+1}",'file':f['key'],'title':'移除CSS示例的模板解析风险' if 'developer' in f['key'] else '以平台清单核对图标，禁止误改类名','kind':'替换' if j>i else '新增','where':f['title']+' → 图标接入规则','why':'开发确认CSS花括号被模板解析；F01审查误判后生成错误图标名。','cases':['F01图标误改','F02正确接入'],'note':'仅提示词变更，CSS不变；后台模板解析必须在模型调用前验证。','requires':[],'old':removed,'new':added,'start':units(''.join(ol[:i])),'end':units(''.join(ol[:j])),'line':i+1};cs.append(c);data['changes'].append(c)
 data['files'].append({**f,'original':old,'revised':new,'changed':bool(cs),'unchangedReason':'本轮未涉及，保留2.2.2原文。','changes':cs,'sourceSha256':sha(old),'revisedSha256':sha(new),'originalChars':units(old),'revisedChars':units(new)});(pkg/'prompts'/name).write_text(new);checks.append({'file':name,'changed':old!=new,'newBraceRisk':False,'sha256':sha(new)});diffs.append(''.join(difflib.unified_diff(ol,nl,fromfile='2.2.2/'+name,tofile='候选/'+name)))
data['devTasks']=[{'id':'IC-DEV1','title':'发布前用实际模板引擎解析全部9份提示词','links':[],'cases':[],'action':'按各环节真实变量集合执行模板解析与替换，验证不存在新增意外变量或缺参；失败时阻止发布并返回提示词名称与具体异常。保留原变量及既有转义，不对完整文本批量替换花括号。','done':'全部9份在后台实际模板引擎通过；本地增量检查不能替代该验收。'},{'id':'IC-DEV2','title':'核对审查与修复实际收到的图标清单','links':[],'cases':['F01图标误改'],'action':'应用6份改动（其余3份原样保留），核对角色映射及运行时实际注入内容包含24个合法类名；CSS继续2.2.2，无需重传。','done':'重新生成数学用例，提交、下一题、重玩及正误都使用准确类名，正误显示且无额外白圆；再验证修改路径。'},{'id':'IC-DEV3','title':'成品类名校验与历史课件','links':[],'cases':['F01图标误改'],'action':'建议在产物检查中将cb-icon-*与已部署清单及本地自定义图标定义比对；未知类名才提示，不自动猜测替换。存量错误HTML需定向重生成或修复，换提示词不会自动更新。','done':'无误改合法类名，无HTML/JS/CSS类名不一致；不强制给无反馈玩法添加图标。'}]
readme='''# 图标审查与模板安全修复

基于2.2.2完整包，仅6份修改、3份保留。创建/修改代码生成移除CSS花括号示例；创建/修改审查及修复各增加准确24类名清单、类名联动核对与选项无底座规则。CSS仍为2.2.2，不需重传。

开发已确认此前花括号模板错误，后台转义后生成恢复。本包用等义自然语言消除该示例的花括号，保留所有原变量占位符及既有转义。不要全局转义或删除花括号。发布前必须用后台实际模板引擎测试9份模板；本地已做新增花括号风险检查、两份developer占位替换模拟、24类名与真实CSS比对以及差异范围检查。

待开发确认与测试环境更新；未更新生产系统提示词，未修改历史HTML。评审页发布不代表服务端已部署。四条复测生成已恢复，但F01审查误改待本包重新生成验证。
'''
(pkg/'README.md').write_text(readme);(pkg/'评审数据.json').write_text(json.dumps(data,ensure_ascii=False,indent=2));(pkg/'改动对比.diff').write_text('\n'.join(diffs));(pkg/'校验结果.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
with zipfile.ZipFile(pkg/'complete-prompts.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in (pkg/'prompts').glob('*.txt'):z.write(p,p.name)
 z.writestr('README.md',readme);assert z.testzip() is None
out=repo/'icon-contract-fix-review';shutil.copytree(pkg,out,dirs_exist_ok=True);(out/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
for n in ['system-prompt-review.html','font-packaging-review.html','resource-contract-review.html']:
 p=repo/n;s=p.read_text();assert 'icon-contract-fix-data' not in s
 s=s.replace('<button data-round="feedback-fix">','<button data-round="icon-contract-fix">11月16日 图标审查与模板安全 · 最新候选</button><button data-round="feedback-fix">',1).replace('11月16日 反馈接入修复 · 最新候选','11月16日 反馈接入修复 · 上一轮')
 block='<script id="icon-contract-fix-data" type="application/json">'+json.dumps(data,ensure_ascii=False).replace('</','<\\/')+'</script>\n'
 s=s.replace('<script>const FEEDBACK_FIX_DATA=',block+'<script>const ICON_CONTRACT_FIX_DATA=JSON.parse(document.getElementById("icon-contract-fix-data").textContent);const FEEDBACK_FIX_DATA=',1).replace('const roundData={',"const roundData={'icon-contract-fix':ICON_CONTRACT_FIX_DATA,",1)
 if n=='system-prompt-review.html':s=s.replace("?requestedRound:'feedback-fix'","?requestedRound:'icon-contract-fix'")
 s=s.replace("if(round==='feedback-fix')return feedbackFixOverview();","if(round==='icon-contract-fix')return `<div class=\"revision-note\"><strong>先保证能生成，再防止审查把正确图标改错</strong><p>${esc(DATA.baseline)}</p><p>CSS保持2.2.2。开发需用实际模板引擎预解析全部9份。</p><a href=\"/icon-contract-fix-review/complete-prompts.zip\">下载九份完整TXT</a></div><table class=\"overview\"><tbody>${DATA.files.map(f=>`<tr><td><button data-file=\"${f.key}\">${esc(f.title)} ↗</button></td><td>${f.changed?f.changes.length+'处改动':'原样保留'}</td></tr>`).join('')}</tbody></table><p>${esc(DATA.history)}</p>${devGuide()}`;if(round==='feedback-fix')return feedbackFixOverview();",1)
 s=s.replace("if(round==='feedback-fix'){$('#round-label')","if(round==='icon-contract-fix'){$('#round-label').textContent=DATA.title;$('#review-title').textContent='图标审查与模板安全修复';$('#review-intro').textContent=DATA.baseline;$('#export-candidate').textContent='下载9份完整候选 TXT';}\nif(round==='feedback-fix'){$('#round-label')",1)
 p.write_text(s)
print('files changed',sum(x['changed'] for x in checks),'diff blocks',len(data['changes']),pkg)
