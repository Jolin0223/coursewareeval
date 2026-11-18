# -*- coding: utf-8 -*-
from pathlib import Path
import json,shutil,re,hashlib,zipfile,html
R=Path(__file__).resolve().parent
O=R.parent/'20261116-完整审查与正文收口提示词评审'
D=json.loads((R/'review-data.json').read_text())
P=R/'视频互动课件_完整提示词包_20261118_r13_联动候选'
issues=[
 dict(id='E1',title='教师工具太小、没有场景序号',old='已要求使用固定教师工具，并通过主题变量匹配课程风格；提示词不控制其尺寸或目录文本。',evidence='Bobo快照固定工具为16px字体、44px最小高度、280px面板；目录只写scene.name，没有序号。',change='保留宿主单一入口与样式隔离，禁止模型另造工具。尺寸与编号明确列为开发运行层改动。',stages='固定运行层；P5/P6/P7/R1保留边界',owner='工程主改',url='https://box.test.xdf.cn/kpm/a65e0eb2a79f4f599503a23e71f95312',snapshot='3a770a512941420aafa9de2b1bd6e36a',accept='在实际大屏、iframe和小屏检验可读可点；列表显示“序号＋场景名”、当前场高亮，拖动与跳转保持。建议以64px入口高度、20px文字作为桌面起点，窄屏面板收敛在视口内。'),
 dict(id='E2',title='视频 → H5 → 视频有多余播放门槛',old='H5直接呈现任务已有要求；但P5/P6/M1仍规定逐段点击，正常ended不能连播。此前没有完成这项联动。',evidence='Bobo开场ended只显示Next，订单页有播放遮罩，结尾普通入场再次等待播放；Panda方案也安排片尾再点Start。',change='P3/P4定义实际完成条件；P5/P6/P7/R1统一正常交接，M1第2/4/5条给出联动候选。封面进入后正常连播，互动必须等待实际完成；暂停和真实拒绝保留恢复入口。',stages='P3–P7、R1、M1＋运行层＋程序检查器',owner='必须同批联动',url='https://box.test.xdf.cn/kpm/a65e0eb2a79f4f599503a23e71f95312',snapshot='3a770a512941420aafa9de2b1bd6e36a',accept='走通封面→视频→H5操作→视频，片间无额外Start/Next/播放确认；课堂观察仍可停留。暂停不被异步事件恢复，播放拒绝有可用入口，重入与旧媒体清理正常。'),
 dict(id='E3',title='独立前景没有真实透明通道',old='逐图片真实Alpha、禁止画棋盘格及素材问题交上游均已写入。',evidence='四条方案34张图片中16张明确要求Alpha，实际16张全部RGB无透明通道；15张在HTML配置之外也被引用。苹果、红上衣可见绘制的棋盘底。',change='补最终处理文件与最终资源地址对应，不继续堆“透明”同义词，不让HTML滤镜伪装抠图。开发检查生图→抠图→转码→入库→打包每一步。',stages='P4/R1小范围补充；素材生产主改',owner='素材链路主改',url='https://box.test.xdf.cn/kpm/40a6f3c7c0dd4d39ba4b18d9fb3f2a82',snapshot='76d61c8146ac4bd2b069547f530fe28e',accept='核对最终文件的有效Alpha、主体完整性及HTML引用；在浅底深底上检验边缘。背景/封面/视频整帧不误判为必须透明。不把RGBA格式本身当成已经抠好。'),
 dict(id='E4',title='同一小熊在封面与视频中换身份',old='已有角色基准与真实图像依赖要求，但缺少逐个同类角色的固定映射。',evidence='大纲只写不同颜色围巾或帽子；六张图无角色基准，封面与两个视频参考图dependencyAssetIds为空。毛色与围巾对应确实变化。',change='逐个绑定称呼、毛色、脸型体型、服饰和允许变化；封面及所有派生图引用适用基准，生产时传真实参考图。参考数不足时用既有规则规划合成参考。',stages='P3/P4/R1＋图像生产依赖',owner='提示词＋生产核验',url='https://box.test.xdf.cn/kpm/c0d3d9bf064547d98a20b0ccc9d9b6eb',snapshot='51ea4f0c7c8541c78ea46fc8ac06d0ed',accept='逐角色横向比较封面、视频参考图、成片与H5。允许变姿势和位置，不允许无依据互换毛色/围巾。要求进入实际生成请求，不能只看计划存在依赖。'),
 dict(id='E5',title='画外旁白时角色仍连续做口型',old='旁白、画内台词、画外台词已有分工；镜头描述要求不作连续说话动作。',evidence='小熊和悟空4个旁白镜头计划都写了嘴部静止；悟空“快乐赴宴”成片抽帧仍反复张合嘴。现有证据不能证明后台启用了哪种口型模型。',change='旁白镜头明确闭口参考图和观察/指向等动作；实际说话者才对口型。核对送入视频服务的最终描述、音频用途及控制参数，缺可靠控制时改构图。',stages='P4/R1＋视频生产/成片验收',owner='视频生产主查',url='https://box.test.xdf.cn/kpm/40a6f3c7c0dd4d39ba4b18d9fb3f2a82',snapshot='76d61c8146ac4bd2b069547f530fe28e',accept='旁白成片无持续说话动作，画内角色台词与说话者一致；不通过HTML静音、重叠配音掩盖错误。不推断平台具备未提供的后期能力。'),
 dict(id='E6',title='需求确认的教学目标和设计风格难读',old='objective与designStyle是非空字符串，缺少内部信息组织规则，界面显示为整段长文本。',evidence='用户截图：教学目标合并认识、笔顺与应用；设计风格把画风、角色、字体、按钮、反馈和声音挤在同一段。',change='目标按认识/操作/应用等实际目标分行，不凑条数；风格按画风配色、角色道具、场景题板、字体语言、交互反馈、声音字幕分行。保留字段和类型，前端按换行显示标签与内容。',stages='P3、R1＋需求确认前端',owner='提示词＋显示层',url='',snapshot='',accept='JSON仍只用原有字段；字符串换行转义合法。长文本可展开、不静默截断；旧段落可原样显示。标签不匹配时作为普通文本渲染，不把模型输出作为HTML执行。')
]
D['currentIssues']=issues
D['h5Sync']=[
 {'rule':'教学目的先于玩法','action':'按观看讲解、共同观察、独立练习选择操作和推进条件，不强迫所有任务判分。','source':'已交付H5候选','stages':'P3/P4'},
 {'rule':'整轮结束必须有明确反馈','action':'有限题数结束显示已完成；不再切题、不强加弹窗奖励或二次Done确认。','source':'已交付H5候选，用户明确要求','stages':'P3–P7/R1'},
 {'rule':'圆形按钮与内部图标一起缩放','action':'圆按钮保持等宽等高，图标同步width/height；文字按钮留白不污染图标按钮。','source':'已交付H5候选','stages':'P4–P7/R1'},
 {'rule':'有效作答与输入兼容','action':'常规拖拽兼容先点对象再点目标；轨迹类活动按有效轨迹判断。','source':'已交付H5候选','stages':'P3–P7/R1'},
 {'rule':'反馈服务教学情境','action':'先选场景、角色或对象变化等反馈，再决定是否需要勾叉、星星和分数。','source':'已交付H5候选','stages':'P3–P7/R1'},
 {'rule':'取消、声音与资源的边界','action':'取消/失焦/资源失败不当学生答错；完全无声覆盖人声和音效；有效打包CSS沿用。','source':'H5后续复核建议，经本轮适配加入','stages':'P4–P7/R1'},
 {'rule':'视频课件默认精美封面','action':'继续默认整图封面＋全图有效点击；不照搬普通H5按需封面的默认值。','source':'保留视频课件明确要求','stages':'P3–P7/R1'}
]
(R/'review-data.json').write_text(json.dumps(D,ensure_ascii=False,indent=2))
readme='''# 视频互动课件提示词联动候选 · 接入说明

本包用于开发评审及联调，尚未替换Box提示词或运行代码，尚未执行真实模板组装和生成回归。不能仅替换TXT就宣称五项效果问题已解决。

## 使用范围

- 创建仍用P1–P7；当前修改用R1 SYSTEM；P8仅旧链路兼容。
- 相对r12改P3/P4/P5/P6/P7/R1及M1。开发来源仍为用户确认的(3).md；提供相对开发来源和相对r12两组全文差异。
- 连播必须同批更新P3–P7/R1、M1第2/4/5条、固定运行层的入场请求与程序检查器。M1开发原文单独保留用于核对，不能与候选同时追加。
- 配置TXT只放模型正文；完整SystemMessage只供联调核对，已含所需固定追加内容，禁止再重复追加。
- 固定purposeIsolation、stageOutputs、字段/枚举/模板变量均保留。P1/P2/P8原文保持；M1第1/3/6条逐字保持。playMedia、包内引用、preload=none、首次加载不等待readyState、重播归零、迟到回调清理均保留。

## 工程联动与验收

1. 教师工具：固定运行层放大入口与列表，序号按确认场景顺序显示；模型不另造或修改Shadow DOM。以实际iframe/大屏尺寸验收，不只看逻辑像素。建议桌面入口64px高、20px文字起步，小屏保持可达。
2. 连播：保持现有context字段和playMedia签名；扩展有效入场请求覆盖已进入课程的正常切场，并保留教师跳转。封面未进入不提前播放；单场预览不越界；手动暂停不被迟到回调恢复；反馈完成交接防重复。更新静态检查器，使合法ended/完成交接不被旧“逐段点击”规则拒绝。不改已经修好的加载、归零和拒绝恢复。
3. 透明素材：核对最终文件有效Alpha与主体完整，追踪原图/处理图/转码/入库/HTML引用。失败定位到资产生产，不让整课HTML修复循环承担抠图。
4. 角色：依赖按有向无环顺序执行，真实参考图进入生图/视频请求，不能只在计划写ID。封面也必须引用身份基准；数量受模型已有上限约束。
5. 旁白：实际请求区分声音归属与嘴部动作。旁白参考图自然闭口、人物做非说话动作，逐成片验收，不承诺不存在的参数或混音能力。
6. 需求确认：objective/designStyle仍为字符串，标准JSON转义换行。前端逐行显示；可按首个冒号分成标签与内容，但不依赖固定标签。旧长段落原样回退，内容作为文本，长内容可展开。不得直接JSON类型改为数组。

## 发布前必须确认

- 本包11_发布前校验为静态检查，不能代替真实Java模板组装、响应提取、模型输出及生成回归。
- 使用实际后端模板组装器验证所有模型正文＋固定后缀＋变量替换；留存生效内容hash及运行层/检查器版本。原P4固定后缀存在durationSeconds与引用数量混写的既有表述，本包未改该开发约束，需开发核对实际校验语义。
- 先过原生成和播放修复回归，再走封面→视频→H5→视频、相邻视频、暂停/重入/教师跳转/拒绝恢复/单场预览；检查透明前景、角色与旁白成片。
- 发布时保持提示词与运行层/检查器兼容；未完成配套时不要把本连播候选单独替换到旧运行层。若需回退，按同批兼容组合回退，不混搭。

## 历史课件

提示词更新不自动修复旧快照。旧HTML继续按其冻结版本运行；需要修复时生成新的可追溯版本。教师工具/交接更新HTML；透明前景替换处理后的资源；身份或口型错误重制相关上游素材及引用，不覆盖无关历史内容。
'''
(P/'README.md').write_text(readme);(R/'开发接入与保护边界.md').write_text(readme)
report='# 六项效果问题与本次修改清单\n\n依据11月18日已取得快照、方案和素材审查；本次为候选改动，不是修复验收结论。\n\n'
for i in issues:
 report+='## '+i['id']+' '+i['title']+'\n\n'+'\n\n'.join('**'+a+'：** '+i[b] for a,b in [('此前规则','old'),('证据','evidence'),('本次改动','change'),('责任环节','stages'),('验收','accept')])+'\n\n'
 if i['url']:report+='[测试环境会话]('+i['url']+') · snapshotId：`'+i['snapshot']+'`\n\n'
report+='## 普通H5同步\n\n来源：[普通H5当前教学交互候选](https://coursewareeval.chenjialing.cn/system-prompt-review?round=teaching)，Git来源66cbbe3；同时区分后续复核建议。\n\n'
for x in D['h5Sync']:report+='- **'+x['rule']+'**：'+x['action']+'（'+x['source']+'；'+x['stages']+'）\n'
(R/'效果问题与改动清单.md').write_text(report)
(P/'08_评审说明').mkdir(exist_ok=True)
(P/'08_评审说明/效果问题与改动清单.md').write_text(report)
(P/'08_评审说明/开发接入与保护边界.md').write_text(readme)
# Preserve previous preflight, strengthen for explicit patch counts and M1 clause-level lock.
V=P/'11_发布前校验';V.mkdir(exist_ok=True)
oldpack=O/'视频互动课件_完整提示词包_20261116_r12'
s=(oldpack/'11_发布前校验/preflight.py').read_text()
s=s.replace("!=1:errors.append(k+': patch anchor')","!=x.get('count',1):errors.append(k+': patch anchor')")
s=s.replace("r(?:9|10|11|12)","r(?:9|10|11|12|13)")
s=s.replace("if sha(m.encode())!='054b2275d28d40ec6c0bac2621999a091a9a1f25d8eae0448cfbcb475745bfc1':errors.append('M1 changed')", "\nfor n in [1,3,6]:\n if m.splitlines()[n]!=files['M1']['previous'].splitlines()[n]:errors.append('protected M1 clause '+str(n))\nif (fixed/files['M1']['filename']).read_text()!=m:errors.append('candidate M1 mismatch')\nfor k in ['P1','P2','P8']:\n if files[k]['final']!=files[k]['previous']:errors.append(k+': unchanged stage modified')")
s=s.replace('本次替换P3至P7配置.json','本次替换P3至P7配置_须联动.json')
s=s.replace("'fixedSuffixesLocked':True", "'developerOriginalSuffixFilesLocked':True,'mediaContractChangedClauses':[2,4,5],'mediaContractProtectedClauses':[1,3,6]")
s=s.replace("requires_backend_validation_and_P4_fixed_suffix_review","requires_runtime_checker_template_validation_and_generation_regression")
s=s.replace("errors=validate(D);", "errors=validate(D);\nfor f in D['files']:\n if f['id'] in ['P3','P4','P5','P6','P7','R1','M1'] and any(x in f['final'] for x in ['每一段视频均由可见播放或继续播放按钮的点击启动','教师工具首镜头例外不授权普通入场']):errors.append(f['id']+': stale manual playback rule')\n")
(V/'preflight.py').write_text(s)
for name in ['review-data.json','exact-patches.json']:shutil.copy2(R/name,V/name)
shutil.copy2(oldpack/'11_发布前校验/locked-sha256.json',V/'locked-sha256.json')
# New builder keeps exact recovery checks and review record logic.
s=(O/'build_review.py').read_text()
s=s.replace('11月16日审查版r12','11月18日联动候选r13').replace('当前 r12','当前 r13').replace('上一版r11','上一版r12').replace('r11 → r12','r12 → r13').replace('r11不是已确认开发基线','r12部署内容仍需生效hash确认').replace('2026.11.16 · 在线评审','2026.11.18 · 在线评审')
s=s.replace("btn('overview','评审总览')+", "btn('overview','评审总览')+btn('issues','效果问题与改动')+btn('confirmation','需求确认样例')+btn('engineering','开发联动清单')+")
s=s.replace('锁定 · 代码固定追加','联动候选 · 代码追加').replace("'原文保持'","'需联动'").replace('代码固定追加 · 原文锁定','代码固定追加 · 工程联动候选')
h=json.loads((O/'history-index.json').read_text());h[0]['title']='11月16日 完整审查 · r12';h[0]['status']='历史交付；用户反馈星期一部署后问题仍在，实际生效内容需开发hash核对'
h.insert(0,dict(id='r13',title='11月18日 效果闭环与确认结构 · 当前候选',status='已交付评审；待工程联调与生成验收',source=R.name,summary=D['summary'],package=True))
(R/'history-index.json').write_text(json.dumps(h,ensure_ascii=False,indent=2))
tabs=''.join('<a class="round-tab'+(' active' if x['id']=='r13' else '')+'" href="'+('./' if x['id']=='r13' else 'history/'+x['id']+'/')+'">'+html.escape(x['title'])+'</a>' for x in h)
s=re.sub(r'<nav class="round-tabs" aria-label="历次变更记录">.*?</nav>', '<nav class="round-tabs" aria-label="历次变更记录">'+tabs+'</nav>',s,flags=re.S)
s=re.sub(r'<div class="review-provenance">.*?</div></section>', '<div class="review-provenance"><strong>先看效果问题，再审开发(3).md → r13累计差异</strong><br>本次明确修改M1第2/4/5条的播放触发条件，须与运行层、程序检查器同批启用；其余播放修复保留。可切换r12 → r13只看本轮。仅更新公开评审与候选包，未替换Box配置、运行代码或旧课件。<br><a href="开发接入与保护边界.md">查看接入与保护边界</a></div></section>',s,flags=re.S)
start=s.index('function overview()');end=s.index('function pair(',start)
new=r'''function currentIssues(){return `<h1>六项效果问题与本次改动</h1><p class="muted">旧规则、快照证据、候选修订与工程责任逐项对应。已有描述不等于实际产物已经合格。</p>${D.currentIssues.map(x=>`<section class="card" id="${x.id}"><div class="cardbody"><span class="tag">${esc(x.owner)}</span><h2>${esc(x.id+' · '+x.title)}</h2><dl class="issue-grid"><dt>此前已写</dt><dd>${esc(x.old)}</dd><dt>实际证据</dt><dd>${esc(x.evidence)}${x.url?`<br><a href="${esc(x.url)}" target="_blank" rel="noopener">查看测试会话</a><div class="small muted">snapshotId：${esc(x.snapshot)}</div>`:''}</dd><dt>本次改动</dt><dd>${esc(x.change)}</dd><dt>责任环节</dt><dd>${esc(x.stages)}</dd><dt>验收结果</dt><dd>${esc(x.accept)}<br><strong>待工程实现及新版本复测</strong></dd></dl></div></section>`).join('')}`}
function h5Table(){return `<section class="card"><div class="cardbody"><h2>与普通H5最新规则的衔接</h2><p class="small"><a href="https://coursewareeval.chenjialing.cn/system-prompt-review?round=teaching" target="_blank" rel="noopener">普通H5教学交互评审</a> · 依据11月18日已交付候选66cbbe3及后续复核建议，来源分开标记。</p>${D.h5Sync.map(x=>`<div class="h5-row"><strong>${esc(x.rule)}</strong><div>${esc(x.action)}<br><small class="muted">${esc(x.source+' · '+x.stages)}</small></div></div>`).join('')}</div></section>`}
function confirmation(){const goals=[['认识','认识“雨”和雨字头，辨认“雪、雷”等天气字。'],['书写','观察并练习“雨、雪”的规范笔顺。'],['应用','将天气字与对应画面匹配，说出字义。']];const styles=[['画风与配色','儿童友好的3D Q版；火焰山暖橙与雨雪清凉蓝对照。'],['角色与道具','悟空身份固定：金箍、毛色、脸型与服饰贯穿封面、视频和H5；芭蕉扇形制一致。'],['场景与题板','场景负责环境；题板保留云纹、金箍主题边饰，中央清楚呈现真实文字。'],['字体与语言','中文用方正准圆简体；需要汉字注音时使用方正楷体拼音字库01。'],['交互与反馈','点击或拖移石头、书写、配对；实际完成后衔接。反馈用角色动作及温和提示。'],['声音与字幕','悟空台词用清亮温暖少年声，旁白用成年教师声；旁白镜头不做说话口型。字幕按真实时间轴和教学任务决定。']];const rows=a=>a.map(([k,v])=>`<div class="confirm-row"><strong>${esc(k)}</strong><span>${esc(v)}</span></div>`).join('');return `<span class="tag">显示方案示例 · 不改变接口字段</span><h1>需求确认：先看目标，再看设计决定</h1><p class="muted">以下是针对用户截图内容的展示样例，不是重新生成的课件方案。提示词负责输出短标签分行；产品前端负责把分行呈现得清楚。</p><section class="card confirm-demo"><div class="cardbody"><h2>悟空借芭蕉扇 · 需求确认</h2><p class="muted small">一年级 · 识字与书写 · 4个章节</p><h3>教学目标</h3><div class="confirm-group">${rows(goals)}</div><h3>教学大纲</h3><div class="chapter-grid">${['01 火焰山寻字','02 认识雨字头','03 学写雨和雪','04 芭蕉扇闯关'].map(x=>`<div>${esc(x)}</div>`).join('')}</div><h3>设计风格</h3><div class="confirm-group">${rows(styles)}</div></div></section><div class="callout"><strong>保持原接口兼容</strong><p>objective、designStyle仍是非空字符串，以标准JSON换行转义分行。前端按行渲染标签与文本；不匹配标签的旧段落原样显示，长内容可展开，模型文本不作为HTML执行。P3不新增字段或改成数组。</p></div><button data-page="P3">查看P3完整改文</button>`}
function engineering(){return `<h1>开发联动与发布边界</h1><p><a href="开发接入与保护边界.md">下载完整接入说明</a> · <a href="校验结果.json">静态校验结果</a></p><div class="callout"><strong>连播不能只替换提示词</strong><p>P3–P7/R1、M1第2/4/5条、固定运行层、程序检查器需使用同一套完成与播放规则。本包提供一致的联动候选；未更改Box配置或后端，也未宣称真实生成回归通过。</p></div><section class="card"><div class="cardbody"><h2>严格保留的开发修复</h2><p>P1/P2/P8、模板变量、JSON输出结构、用途及阶段固定后缀保持。M1第1/3/6条逐字保持；playMedia签名、包内资源引用、src/data-vc-src、preload=none、首次播放不等待readyState、重播归零及迟到回调隔离保留。教师工具仍由宿主提供。</p><h2>同批修改的内容</h2><ol><li>固定教师工具放大与场景编号，按真实显示尺寸验收。</li><li>运行层提供合法的正常入场请求；生成与检查器允许视频ended和互动完成后的衔接，保留暂停、拒绝恢复和单场预览隔离。</li><li>素材链追踪最终Alpha文件、实际角色参考图和视频音频用途。</li><li>需求确认前端支持字符串分行、标签显示和旧段落回退。</li></ol><h2>验证顺序</h2><p>先用实际后端组装器验证模板/变量/追加约束和原生成链，再验连续教学、媒体资产与跨屏显示。本地静态检查通过不能替代生成回归。原P4固定后缀中秒数与引用数量混写的表述保留，需开发核对实际实现。</p><h2>历史课件</h2><p>更新提示词不会改变旧快照。旧HTML继续按冻结版本运行；效果修复形成新版本，按问题更新HTML或上游素材，并保留版本追溯。</p></div></section><button data-page="M1">审阅M1的限定改动</button>`}
function overview(){return `<span class="tag">开发(3).md → r13累计对照</span><span class="tag warn">联动候选 · 待工程与生成验证</span><h1>效果闭环与需求确认结构</h1><p class="muted">把“已经写了什么、实际为何没生效、这次改什么、开发还要改什么”放在同一处。模型正文只保留执行规则，不写调词版本历史。</p><div class="toolbar"><button data-page="issues">先看6项问题清单</button><button data-page="confirmation">看需求确认样例</button><button data-page="engineering">看开发联动清单</button></div><div class="stats"><span><b>6</b>项当前问题</span><span><b>7</b>份相对r12改动</span><span><b>18</b>轮变更记录</span><span><b>${Object.keys(decisions).length}/${D.files.length}</b>份评审决定</span></div><section class="card"><ul class="summary">${D.summary.map((x,i)=>`<li><span class="number">${String(i+1).padStart(2,'0')}</span><div>${esc(x)}</div></li>`).join('')}</ul></section><p><a href="效果问题与改动清单.md">下载问题与改动清单</a> · <a href="开发接入与保护边界.md">接入与保护边界</a> · <a href="校验结果.json">静态校验结果</a></p>${h5Table()}<div class="callout"><strong>全文中的改动逐处标记</strong><p>默认对比开发来源(3).md与当前完整候选；切换r12 → r13查看本轮增量。红色删除线、绿色新增、灰色保留。M1是单列的工程候选，不冒充开发原文未改。</p></div><section class="card"><ul class="stage-list">${D.files.map(f=>`<li><div><strong>${esc(f.id+' '+f.name)}</strong><small>${esc(f.route||f.key||'')}</small></div><button data-page="${esc(f.id)}">看全文对照</button></li>`).join('')}</ul></section><details><summary>之前12项效果问题（历史记录，按当轮规则理解）</summary>${issueTable()}</details><p class="small muted">评审决定保存在当前浏览器，可导出共享。下载包始终为完整候选，不按零散选择混装协议；网页“采纳”不代表开发确认或Box部署。</p>`}
'''
s=s[:start]+new+s[end:]
s=s.replace("if(!['overview',...allowed].includes(page))", "if(!['overview','issues','confirmation','engineering',...allowed].includes(page))")
s=s.replace("page==='overview'?overview():file(D.files.find(f=>f.id===page))", "page==='overview'?overview():page==='issues'?currentIssues():page==='confirmation'?confirmation():page==='engineering'?engineering():file(D.files.find(f=>f.id===page))")
s=s.replace('</style></head>', '.issue-grid{display:grid;grid-template-columns:100px minmax(0,1fr);gap:14px 20px;margin:18px 0 0}.issue-grid dt{font-weight:600;color:var(--muted)}.issue-grid dd{margin:0;overflow-wrap:anywhere}.h5-row{display:grid;grid-template-columns:210px minmax(0,1fr);gap:20px;padding:16px 0;border-top:1px solid var(--line)}.confirm-demo{max-width:1000px}.confirm-demo h3{margin:22px 0 10px}.confirm-group{border:1px solid var(--line);border-radius:8px;overflow:hidden}.confirm-row{display:grid;grid-template-columns:120px minmax(0,1fr);gap:20px;padding:16px 18px;border-bottom:1px solid var(--line);background:#fbfdfc}.confirm-row:last-child{border:0}.confirm-row strong{color:#28634e}.chapter-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.chapter-grid div{background:#eaf4ef;padding:13px;border-radius:6px}@media(max-width:700px){.issue-grid{grid-template-columns:1fr;gap:6px}.issue-grid dd{margin-bottom:12px}.h5-row,.confirm-row{grid-template-columns:1fr;gap:5px}.chapter-grid{grid-template-columns:1fr}}</style></head>')
(R/'build_review.py').write_text(s)
print(json.dumps({'issues':len(issues),'history':len(h),'package':str(P)},ensure_ascii=False))
