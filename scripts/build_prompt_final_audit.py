from pathlib import Path
import re,json,hashlib,difflib,zipfile,shutil
P=Path.cwd(); B=P/'Obsidian Vault/03-AI互动课件制作'; R=P/'.tmp/coursewareeval-icons-font-20261112'; base=B/'20261116-图标审查与模板安全修复'; out=B/'20261116-系统提示词完整复核';(out/'prompts').mkdir(parents=True,exist_ok=True)
data=json.loads((base/'评审数据.json').read_text());oldfiles=data['files'];data.update(title='系统提示词完整复核 · 最终文本待验收',revision='20261116-final-audit-v1',baseline='对比上一份图标审查与模板安全修复包。仅消除规则冲突、协议歧义和调试语境；不新增玩法，不改CSS。',files=[],changes=[],history='9份TXT为独立完整文本，版本与案例仅出现在评审说明。已进行静态协议、变量、图标清单及导出一致性检查；后台实际模板解析与生成回归仍需开发执行。',excluded='保留字体、SDK指标结构、用户优先、封面按需、拖拽加点击、切题规则与单文件边界；历史HTML不自动更新。')
checks=[];diffs=[]
oldbad='`cb-icon-check`、`cb-icon-right`、`cb-icon-refresh`不在本清单中，不能作为上述内置图标的替代名；用户代码明确自行定义的图标另按其实际定义核对。'
for f in oldfiles:
 name=f['key']+'.txt';old=(base/'prompts'/name).read_text();s=old
 # Only remove development-history wording, not game rounds or current modification scopes.
 s=s.replace('公共V2图标CSS','平台提供的图标样式表').replace('历史课件不批量升级。','不修改当前需求以外的课件或功能。')
 for x in ['封面整图艺术按钮沿用原封面规则。','整图封面沿用原封面规则。','整图封面沿用原规则。','整图封面仍按原规则；']:
  s=s.replace(x,'整图封面按当前任务确定的表现形式和入口要求执行。')
 s=s.replace('通用教学插图、Logo仍按原素材规则处理；沿用现有输出协议。','教学插图、Logo按其用途规划素材；输出遵循本提示词规定的任务结构。')
 s=s.replace('图标是CSS图形，尺寸由width/height控制，不能仅设置font-size；','复用平台CSS图标时，尺寸由width/height控制，不能仅设置font-size；')
 s=s.replace(oldbad,'用户代码明确自行定义的图标按其实际定义核对，不强制替换为内置图标。')
 s=s.replace('正误使用`cb-icon-correct`与`cb-icon-incorrect`，下一题使用`cb-icon-next`','复用平台CSS图标时，正误对应`cb-icon-correct`与`cb-icon-incorrect`，下一题对应`cb-icon-next`')
 s=s.replace('答题后符号不被display、visibility或opacity隐藏。','应显示反馈的状态下，符号不被display、visibility或opacity隐藏；未作答时按玩法隐藏反馈是正常行为。')
 s=s.replace('选项内正误反馈不加独立圆底、边框或阴影，也不使用伪元素绕过此要求；','除用户明确指定其他造型外，选项内正误反馈不加独立圆底、边框或阴影，也不使用伪元素绘制底座；')
 s=s.replace('选项内正误反馈移除额外底座及其伪元素，','用户未指定其他造型且当前修复涉及选项反馈时，移除额外底座及其伪元素，')
 if 'architect' in name or 'reviewer' in name:
  s=s.replace('所有点击、触摸、拖拽、滑动、长按等交互时，尽量统一使用 Pointer Events','拖拽、绘制、滑动、长按等连续交互时，优先使用 Pointer Events')
  s=s.replace('  - 避免使用 click、mousedown、mousemove、mouseup、touchstart、touchmove 和 touchend','  - 普通按钮允许使用 click 承接鼠标、触摸和键盘激活；连续交互避免重复绑定鼠标与触摸事件。同一动作不得在 Pointer Events 与 click 中重复执行；不能仅因使用 click 而判错。')
 s=s.replace('生成代码时，请主动检查现有的鼠标、触摸及点击事件；能够安全替换的，统一改用 Pointer Events。仅在 Pointer Events 无法满足需求时保留其他事件，并在注释中说明原因。','连续交互优先使用Pointer Events；普通按钮可保留有效的click与键盘激活，避免重复触发，不为统一事件类型重写已正确的交互。')
 s=s.replace('生成代码时，仅检查本轮修改及必要联动涉及的鼠标、触摸及点击事件，不因此重写未涉及的交互；能够安全替换的，统一改用 Pointer Events。仅在 Pointer Events 无法满足需求时保留其他事件，并在注释中说明原因。','仅检查当前修改及必要联动涉及的交互：连续操作优先使用Pointer Events，普通按钮保留有效的click与键盘激活并避免重复触发，不重写未涉及或已正确的交互。')
 s=s.replace('检查正误符号在实际结构中具有可见尺寸、颜色及遮罩，不能仅凭类名判通过；','按所选实现检查正误符号的可见尺寸及显示条件；仅复用平台CSS图标时检查遮罩，不因SVG或图片没有CSS遮罩而判错；')
 s=s.replace('正误符号须有可见尺寸、颜色及遮罩，不能仅凭类名判通过；','按所选实现检查正误符号的可见尺寸及显示条件；仅复用平台CSS图标时检查遮罩，不因SVG或图片没有CSS遮罩而判错；')
 s=s.replace('遵循用户指定和整图封面原规则','遵循用户指定及当前任务确定的封面表现形式和入口要求')
 if 'architect' in name:
  a=s.index('在相关HTML代码任务的taskDetails中明确加入 ');b=s.index('内置图标无法准确表达',a)
  s=s[:a]+'在相关HTML代码任务的taskDetails中，用中文写明在head中引用上述样式表、选用的完整图标类名、按钮文案、子元素顺序及必要属性，不写HTML代码片段。按钮容器使用cb-theme，实际按钮按用途使用cb、cb-text等类，图标元素使用cb-icon和所选图标类，装饰性图标设置aria-hidden；仅列当前文件需要的信息，不要求下游读取URL或manifest.json。'+s[b:]
  if '.modify.' in name:
   s+='\n只输出包含imageTasks、audioTasks、codeTasks和reportMetrics四个字段的单个合法JSON对象，不输出解释或代码围栏。taskDetails使用中文描述，不包含代码；字段与任务类型遵循上述定义。\n'
 if 'developer' in name or 'fixer' in name:
  lines=s.splitlines(True);i=next(i for i,l in enumerate(lines) if l.startswith('3. 只输出'))
  lines[i]='3. 只输出当前指定文件修改后的完整代码，不输出差异片段、其他文件或解释。使用一个与文件类型对应的代码围栏：HTML用```html，JavaScript用```js，CSS用```css，并以```结束；围栏仅为回复的格式边界，不写入文件内容。\n';s=''.join(lines)
  s=s.replace('按真实状态切换成套素材，资源缺失或不合格时报告并按现有流程补齐，不用错误功能符号或虚假状态替代。','按真实状态切换任务提供的素材，不编造资源路径或虚假状态。资源加载失败时提供明确的失败状态及适用的重试入口；当前代码任务不承担素材生产，不在代码输出外追加说明。')
  s=s.replace('通过`width`和`height`设置图标实际尺寸，不用`font-size`代替；例如将星星图标的width和height均设置为120px。','通过`width`和`height`按布局设置CSS图标实际尺寸，不用`font-size`代替。')
  s=s.replace('复用平台CSS图标时，尺寸由width/height控制，不能仅设置font-size；图标与文字间距','图标与文字间距')
 if 'fixer' in name:
  s=s.replace('生图不合格需按现有流程补素材，不擅自改成另一种视觉形式；','保留任务确定的素材形式，不在代码修复中擅自换成另一种视觉形式；')
  s=s.replace('涉及其他文件或CDN缺失时，通过现有流程说明依赖，不声称单次修复覆盖全部文件。','只修复当前文件可解决的问题，不编造其他文件或CDN内容，不声称已修复当前文件以外的问题。')
  s=s.replace('仅有URL而缺少必要类名/字体信息时，通过现有流程报告缺失信息，不臆造远程文件内容，不修改其他文件。','无法从输入确认的资源名称不擅自替换；优先保留已有合法引用，不臆造远程文件内容。')
  s=s.replace('需联动其他文件时按现有任务流程说明依赖，不自行换名造成不匹配。','其他文件仍使用的合法名称和接口应保持兼容，不自行换名造成不匹配。')
  s=s.replace('2. 修改处增加必要的注释，方便后续的代码审查。','2. 必要注释说明代码用途与约束，不描述修改历史或调试过程。')
 if 'reviewer' in name:
  lines=s.splitlines(True)
  for i,l in enumerate(lines):
   if l.startswith('3. bug描述中'):lines[i]='3. 输出合法JSON，字符串中的双引号与反斜杠按JSON规范转义。只报告输入代码或明确任务要求可证明的问题，不推测未提供的用户要求。\n'
  s=''.join(lines)
  s=s.replace('在`btnStart`和`btnFree`的点击事件中，由于DOM元素的`display`属性切换后不会立即触发重排，导致`GameEngine`中的`resize`方法获取到的父容器尺寸为0。','简述该文件中可定位错误的触发条件与表现。')
  s=s.replace('按任务已给出的图标类名、字体名称和调用结构静态核对代码；','跨文件问题按责任文件分别列入bugList，说明相互依赖；不要求单次修复改动多个文件。按任务已给出的图标类名、字体名称和调用结构静态核对代码；')
 if name=='prompt.material-design-learning-tablet.txt':
  s=s.replace('完成全部任务后，使用与风格一致的反馈弹窗内展示完成结果、奖励和后续操作，弹窗应包含明确的关闭或再次挑战按钮，并保证按钮交互有效；不得使用浏览器原生alert、confirm或prompt。','需要结算的玩法在完成后展示与风格一致的结果及必要后续操作；仅在玩法需要时提供奖励或弹窗。自由绘画、探索等不强加成绩、星星或完成弹窗。采用结果弹窗时提供有效的关闭或再次挑战入口，不使用浏览器原生alert、confirm或prompt。')
 # Confirm exact template token inventory is unchanged, including escaped text and voice_names.
 token=lambda x:re.findall(r'(?<![\\{])\{([^{}]*?)(?<!\\)\}(?!\})',x)
 assert token(old)==token(s),(name,token(s))
 assert old.count('{{voice_names}}')==s.count('{{voice_names}}')
 assert not any(x in s for x in ['公共V2','旧版','上一版','最新版本','cb-icon-check','cb-icon-right','cb-icon-refresh','历史课件不批量升级'])
 (out/'prompts'/name).write_text(s)
 ol=old.splitlines(True);nl=s.splitlines(True);cs=[]
 units=lambda v:len(v.encode('utf-16-le'))//2
 for tag,i,j,k,l in difflib.SequenceMatcher(None,ol,nl).get_opcodes():
  if tag=='equal':continue
  c={'id':f"FA{f['order']:02d}-{len(cs)+1}",'file':f['key'],'title':'消除冲突与历史语境，明确当前环节职责','kind':'替换' if j>i else '新增','where':f['title'],'why':'完整文本复核：保持原输出契约，避免规则互相否定及依赖历史版本。','cases':[],'note':'仅改变本卡标注文本；模板变量和既有转义保留。','requires':[],'old':''.join(ol[i:j]),'new':''.join(nl[k:l]),'start':units(''.join(ol[:i])),'end':units(''.join(ol[:j])),'line':i+1};cs.append(c);data['changes'].append(c)
 data['files'].append({**f,'original':old,'revised':s,'changed':bool(cs),'changes':cs,'sourceSha256':hashlib.sha256(old.encode()).hexdigest(),'revisedSha256':hashlib.sha256(s.encode()).hexdigest(),'originalChars':units(old),'revisedChars':units(s)})
 checks.append({'file':name,'templateVariables':token(s),'voiceNamesPreserved':True,'noRevisionLanguage':True,'sha256':hashlib.sha256(s.encode()).hexdigest(),'charsBefore':len(old),'charsAfter':len(s)});diffs.append(''.join(difflib.unified_diff(ol,nl,fromfile='复核前/'+name,tofile='完整文本/'+name)))
readme='''# 系统提示词完整复核

完整ZIP仅包含9份供平台使用的TXT。版本、案例、调试过程和研发检查要求只记录在本说明及评审页，不注入模型提示词。

此次消除：图标黑名单式补丁及过度限制自定义图标；完成弹窗与按需反馈冲突；禁用click与键盘激活冲突；架构任务不许代码但要求HTML示例的冲突；代码输出与文字报告冲突；固定bug示例诱导；对旧规则和版本的依赖。补齐修改架构JSON输出约束，保留四字段契约。

花括号：保留各环节既有变量及既有转义，不添加裸CSS花括号；不采用全局转义。本地检查不代替后台实际模板引擎测试。

CSS保持已部署2.2.2，不重新上传。不修改历史HTML，不自动应用服务端提示词。生成与修改链路都要在测试环境验收。

## 研发发布前必须验证

1. 9份分别使用真实模板引擎及真实变量集合解析；缺参或意外变量时阻止发布。voice_names沿用现有双花括号处理顺序，不改变平台契约。
2. 核对角色与提示词映射、实际生效内容。创建/修改架构输出四字段合法JSON；审查输出bugList/isPassReview；代码生成/修复输出一个指定文件完整代码围栏，后端提取内容后再存文件，不把围栏存入HTML。
3. 重跑F01数学：提交、下一题和正误类名正确，状态显示且无多余白圆；F02星星、F03绘画、F04自由探索不回退。再用已有数学课件做一次单文件修改验证。
4. 组件类名以真实CSS及允许的本地定义核对，不凭常见图标库猜测。跨文件错误按责任文件派发，修复智能体每次只处理一个文件。

## 保留但需研发确认的既有约束

架构要求reportMetrics至少4项，沿用既有协议，未擅自改变数量；是否对自由探索课件适用由平台确认。语音仍按用户需求及设计方案规划，未改变既有默认策略。

上述检查通过前，不把静态文本检查表述为生成效果已通过或绝不会出错。
'''
(out/'README.md').write_text(readme);(out/'复核结果.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2));(out/'改动对比.diff').write_text('\n'.join(diffs))
data['devTasks']=[{'id':'FA-DEV1','title':'后台模板及输出协议预检','links':[],'cases':[],'action':'用真实模板引擎和各环节变量预解析9份；检查架构JSON、审查JSON、单文件代码围栏解析。不得把围栏写入HTML文件。','done':'解析成功，角色映射正确，异常时阻止发布。静态检查不替代后台验证。'},{'id':'FA-DEV2','title':'生成和修改两条链路回归','links':[],'cases':['F01图标误改','F02正确接入'],'action':'重跑F01–F04并补一次已有课件修改；核对图标名称、反馈显示、键盘与单次点击、无强加奖励。CSS保持2.2.2。','done':'真实产物与目标端验收，不把本地静态检查当模型效果通过。'},{'id':'FA-DEV3','title':'既有接口约束确认','links':[],'cases':[],'action':'reportMetrics至少4项和voice_names处理沿用既有契约；如需调整由平台统一确认，不在本次文本修订中擅改。','done':'不会因数量限制要求无评分课件新增评分，也不改变模板替换顺序。'}]
(out/'评审数据.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
with zipfile.ZipFile(out/'complete-prompts.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted((out/'prompts').glob('*.txt')):z.write(p,p.name)
 assert len(z.namelist())==9 and z.testzip() is None
site=R/'prompt-final-audit-review';shutil.copytree(out,site,dirs_exist_ok=True);(site/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
for name in ['system-prompt-review.html','font-packaging-review.html','resource-contract-review.html']:
 p=R/name;s=p.read_text();assert 'prompt-final-audit-data' not in s
 s=s.replace('<button data-round="icon-contract-fix">','<button data-round="final-audit">11月16日 完整文本复核 · 当前交付</button><button data-round="icon-contract-fix">',1).replace('11月16日 图标审查与模板安全 · 最新候选','11月16日 图标审查与模板安全 · 复核前')
 block='<script id="prompt-final-audit-data" type="application/json">'+json.dumps(data,ensure_ascii=False).replace('</','<\\/')+'</script>\n'
 s=s.replace('<script>const ICON_CONTRACT_FIX_DATA=',block+'<script>const FINAL_AUDIT_DATA=JSON.parse(document.getElementById("prompt-final-audit-data").textContent);const ICON_CONTRACT_FIX_DATA=',1).replace('const roundData={',"const roundData={'final-audit':FINAL_AUDIT_DATA,",1)
 if name=='system-prompt-review.html':s=s.replace("?requestedRound:'icon-contract-fix'","?requestedRound:'final-audit'")
 s=s.replace("function renderOverview(){",'''function renderOverview(){if(round==='final-audit')return `<div class="revision-note"><strong>模型只接收独立完整规则，不接收调试过程</strong><p>${esc(DATA.baseline)}</p><p><a href="/prompt-final-audit-review/complete-prompts.zip">下载9份完整TXT（ZIP仅含提示词）</a> · <a href="/prompt-final-audit-review/README.md">研发验收说明</a></p></div><table class="overview"><tbody>${DATA.files.map(f=>`<tr><td><button data-file="${f.key}">${esc(f.title)} ↗</button></td><td>${f.changes.length}处差异</td></tr>`).join('')}</tbody></table><p>${esc(DATA.history)}</p>${devGuide()}`;''',1)
 s=s.replace("if(round==='icon-contract-fix'){$('#round-label')","if(round==='final-audit'){$('#round-label').textContent=DATA.title;$('#review-title').textContent='完整文本复核';$('#review-intro').textContent=DATA.baseline;$('#export-candidate').textContent='下载9份完整 TXT';}\nif(round==='icon-contract-fix'){$('#round-label')",1);p.write_text(s)
print('files',len(checks),'diff blocks',len(data['changes']),'chars',sum(x['charsBefore'] for x in checks),sum(x['charsAfter'] for x in checks))
