from pathlib import Path
import json, re, hashlib, shutil, difflib, zipfile

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent / '20261116-完整审查与正文收口提示词评审'
OLDPACK = OLD / '视频互动课件_完整提示词包_20261116_r12'
PACKAGE = ROOT / '视频互动课件_完整提示词包_20261118_r13_联动候选'
D = json.loads((OLD/'review-data.json').read_text())
F = {f['id']:f for f in D['files']}
PATCHES=[]
for f in F.values():
    f['previous']=f['final']
    for key in ['diffDev','diffPrevious']:f.pop(key,None)

def replace(k,before,after,topic):
    assert before and F[k]['final'].count(before)==1, (k,topic,'anchor',F[k]['final'].count(before))
    assert '{' not in after and '}' not in after,(k,topic,'literal brace')
    F[k]['final']=F[k]['final'].replace(before,after)
    PATCHES.append(dict(id=k,topic=topic,before=before,after=after))

def append_after(k,anchor,text,topic):replace(k,anchor,anchor+'\n'+text,topic)

def replace_lines(k,predicate,after,topic):
    lines=[x for x in F[k]['final'].splitlines() if predicate(x)]
    for n,line in enumerate(dict.fromkeys(lines)):
        count=F[k]['final'].count(line)
        if count==1:replace(k,line,after,topic)
        else:
            # Duplicate paragraphs are replaced together, with exact count retained in evidence.
            assert '{' not in after and '}' not in after
            F[k]['final']=F[k]['final'].replace(line,after)
            PATCHES.append(dict(id=k,topic=topic,before=line,after=after,count=count))

structure='需求确认的objective与designStyle仍为非空字符串，不改为数组或对象。objective按实际目标分条，通常不超过4条，不为凑数增加目标；每条用简短标签加一个可观察的学习结果，如“认识：……”“操作：……”“应用：……”，不堆叠无法验证的口号。designStyle按“画风与配色、角色与道具、场景与题板、字体与语言、交互与反馈、声音与字幕”分行，每项写本课具体决定；不适用项省略，不压成一段。字符串内用标准JSON换行转义，解析后逐行显示；不用HTML、Markdown表格或新增字段。章节content依次写学习内容、学生动作、完成条件与后续衔接，保持短句。'
append_after('P3',F['P3']['final'].splitlines()[0],structure,'需求确认结构化')
identity='多位同类角色逐个固定名字或称呼、毛色或肤色、脸型体型、服装及配饰配色，给出允许变化；不能只写“不同颜色”或让各图自行分配。封面、视频及H5保持同一角色与外貌的对应关系，角色位置可变但身份不互换；任务明确换装时只改变指定服装，保留其他识别特征。'
append_after('P3',next(x for x in F['P3']['final'].splitlines() if x.startswith('主题元素可以用于')),identity,'多角色身份固定')
intent='先按需求与教学目标确定每段的用途：讲解或共同观察保留教学停留，不强加判分；独立练习或闯关以有效作答推进。未指定玩法时选择能体现目标且步骤最少的操作；缺省按本课已确定的教学流程衔接，不额外弹出模式选择。需要观察、讨论、跟读等无法自动判断结束的任务，规划有明确教学含义的完成入口。'
flow='教学衔接：点击整课封面进入后，视频正常结束直接进入下一互动或下一视频，不再重复“开始／播放”确认。互动先呈现任务并等待实际完成，必要反馈结束后进入后续环节；下一段为视频时自动尝试播放。课堂停留、讨论或主动提交按本场完成条件等待，不能用固定时长代替学生作答。暂停保留进度，不被切场或迟到回调擅自恢复；浏览器真实拒绝或资源失败时才展示边缘恢复入口，等待期间保留可见画面。'
terminal='有限题数或关卡结束后，明确显示整轮活动已完成，不继续切题；结果可留在当前页，不强制弹窗、奖励或二次Done确认。自由探索不强设终点，但主动结束后要有清楚终态。只按原上报协议提交已有真实结果一次；重新开始才重置本轮，不为完成反馈新增评分或绕过录音模式限制。'
for k in ['P3','P4']:
    anchor=next(x for x in F[k]['final'].splitlines() if x.startswith('输出仍只有既定大纲字段')) if k=='P3' else next(x for x in F[k]['final'].splitlines() if x.startswith('将各资源实际需要的规则'))
    append_after(k,anchor,intent+'\n'+flow+'\n'+terminal,'教学目的与完成衔接')

basechain='反复出现的每个角色及关键道具分别建立适用的基准；封面、角色变体和含角色的视频整帧都属于派生图，在现有dependencyAssetIds中引用实际适用基准，生产时按依赖顺序解析为真实参考图。每张描述复述其固定识别特征与本次允许的变化，不能仅写“同上”或基准名字。没有可用基准时先规划基准，不让多个独立请求各自重设计同一角色；无人物任务不强加角色。'
for k in ['P4','R1']:
    anchor=next(x for x in F[k]['final'].splitlines() if x.startswith('角色基准默认'))
    append_after(k,anchor,identity+'\n'+basechain,'角色依赖覆盖封面与多角色')
    before=next(x for x in F[k]['final'].splitlines() if x.startswith('旁白镜头的pictureDescription'))
    after='旁白镜头的pictureDescription明确画外旁白、出镜角色不作连续说话动作，并指定观察、指向或移动等具体行为；对应参考图采用自然闭口，避免张嘴说话或持续大笑。画内角色台词才指定实际说话者及对应口型，其他角色不代说；画外角色台词不驱动画内人物口型。按已有dub、speaker和音频引用逐段对应，不新增字段。参考音频承担配音不代表要驱动所有出镜角色说话；仅使用平台实际支持的控制能力，无法可靠控制时改用观察对象或无说话角色的镜头，不假定存在未提供的后期混音能力。'
    replace(k,before,after,'旁白参考图与视频动作一致')
    anchor=next(x for x in F[k]['final'].splitlines() if x.startswith('独立前景的每份description'))
    append_after(k,anchor,'交付给H5的应是经过透明处理并通过主体完整性检查的最终文件，资源地址也必须指向该文件；原始生图、抠图结果与最终打包引用不能混淆。生成描述不能代替真实Alpha检查，未取得检测结果不声明已完成，不要求HTML用滤镜或混合模式补救素材。','透明素材最终文件闭环')

# Replace all contradictory timing rules together. Loading, restart and lifecycle protections remain.
play='正常教学衔接按追加媒体运行硬契约调用VcCourseware.playMedia；视频结束和互动实际完成后允许进入下一媒体，不把可见播放按钮作为每段的必经步骤。首次进入、手动继续或重试在有效轻触释放或键盘处理栈同步请求；自动衔接须确认当前场景、播放批次、教学阶段和未手动暂停。每次捕获播放拒绝，失败时保留静帧并提供边缘继续/重试入口；禁止无限重试、空白等待或假装已经播放。资源加载事件不能自行启动新的教学播放。'
context='场景start(context)接收只读上下文：source保留course或teacher-tools，autoplay表示宿主请求本次入场的首镜头自动尝试，isActive()表示本次入场仍有效。只有context.autoplay且context.isActive()时才在视频阶段启动首镜头一次；纯H5直接初始化任务。mixed先做H5时先等待实际完成，不因autoplay跳过任务；之后按媒体运行契约衔接视频。普通教学切场与教师跳转由宿主统一传递播放请求，生成代码不伪造上下文。封面尚未进入、手动暂停或无效场景不得自动启动；单场预览只运行选定场景。所有播放复用playMedia与同一失败恢复流程，不同时启动多个镜头，不为规避播放限制而静音。真正有视频帧才移除覆盖静帧，异步回调核对当前场景、媒体和批次，stop清理事件及定时器。'
life='生命周期按实际执行路径判定：顶层只声明静态数据、无副作用辅助函数和registerScene，不启动计时、播放、上报或场景初始化。start可绑定按钮回调；有效入场请求、视频正常结束或互动实际完成的播放时机按追加媒体运行契约处理，不能只因代码嵌套在start中就误判。始终通过playMedia，不直接调用媒体play。场景根显隐由宿主hidden控制；内部封面、反馈与操作层可按教学状态切换，不能以通用display覆盖场景根hidden。'
for k in ['P5','P6','P7','R1']:
    s=F[k]['final']
    # The long paragraph occurs twice in developer/fixer, and inside the fixer role header.
    pat=r'除教师工具跳转的首镜头自动播放外，每一段视频均由可见播放或继续播放按钮的点击启动[^\n]*?正常(?:视频)?内容中的艺术性暗场不能?用?作?等待界面。'
    # Use explicit span endings for both spaced and compact original variants.
    spans=re.findall(r'除教师工具跳转的首镜头自动播放外，每一段视频均由可见播放或继续播放按钮的点击启动.*?(?:正常视频内容中的艺术性暗场不能用作等待界面。|正常内容中的艺术性暗场不当作等待界面。)',s)
    for old in dict.fromkeys(spans):
        count=F[k]['final'].count(old)
        F[k]['final']=F[k]['final'].replace(old,play)
        PATCHES.append(dict(id=k,topic='正常教学连续播放',before=old,after=play,count=count))
    replace_lines(k,lambda x:x.startswith('场景 start(context)'),context,'入场播放上下文')
    replace_lines(k,lambda x:x.startswith('生命周期判定按实际执行路径'),life,'生命周期判定与连播对齐')
    if '所有播放时机、异步校验与清理遵守末尾媒体运行硬契约，不新增自动播放权限或safeResetMedia。' in F[k]['final']:
        replace(k,'所有播放时机、异步校验与清理遵守末尾媒体运行硬契约，不新增自动播放权限或safeResetMedia。','所有播放时机、异步校验与清理遵守末尾媒体运行硬契约，不绕过宿主请求或引入safeResetMedia。','保护播放修复')
    anchor=next(x for x in F[k]['final'].splitlines() if x.startswith('H5入场直接展示题目'))
    append_after(k,anchor,flow+'\n'+terminal,'无重复门槛与整轮终态')

replace('P6','媒体统一通过VcCourseware.playMedia调用；除教师工具有效入场时的首镜头尝试外，播放由可见按钮的有效轻触释放或键盘激活触发，片间保留画面及恢复入口。','媒体统一通过VcCourseware.playMedia调用；按追加契约核对有效用户入口与正常教学自动衔接，片间保留画面，恢复入口仅用于暂停恢复、播放拒绝或资源错误。','评审允许合法连播')
replace('P6','教师工具首镜头例外不授权普通入场、片尾或定时器自动播放。','有效入场请求、正常片尾或互动完成的自动衔接按契约验收，不授权资源加载回调擅自播放或暂停后自行恢复。','评审播放条件')
old=next(x for x in F['P6']['final'].splitlines() if x.startswith('播放验收须覆盖'))
new='播放验收覆盖封面进入、正常视频到H5、有效作答到视频、相邻视频、教师跳转、单场预览、暂停继续、重入、播放拒绝、媒体错误及迟到回调。正常衔接不应出现多余开始或播放门槛；不能跳过需要学生操作或教师确认的阶段。无静帧、调用play即隐藏唯一画面、拒绝只记日志、切场先清空再黑屏等待均为可定位缺陷。按追加媒体契约判定播放时机，真实拒绝后的恢复按钮不算多余。资源与HTML错误分开定位；上游阻断在bugDescription写明assetId或shotId、证据及负责环节，不让修复器循环改HTML。未取得媒体证据不编造通过或失败，HTML通过不代表整课效果验收通过。'
replace('P6',old,new,'连贯性验收')
replace('P6','固定教师工具尺寸／序号、连续播放能力属于宿主契约，不要求P7重写受保护代码，也不把遵守追加媒体运行契约的逐段手动播放判成HTML缺陷。','固定教师工具尺寸、序号及宿主播放请求属于运行层责任，不要求P7重写受保护代码；区分宿主缺能力与生成代码没有执行已支持的连续教学流程。','运行层与生成代码责任')

# M1 is a separately labelled coordinated proposal, never silently presented as developer original.
M=F['M1']['final'].splitlines()
replace('M1',M[2],'2. 视频和音频统一调用VcCourseware.playMedia(media, context, restart)，返回原播放Promise；restart表示明确从头重播，默认false。首次进入、手动继续与重试必须在有效pointerup或键盘激活的处理栈同步请求，不先await归零、就绪或计时器。正常教学自动衔接仅按第4、5条执行。首次媒体及释放来源后重入起点已为0时直接播放，play本身触发加载。','媒体入口保留与衔接例外')
replace('M1',M[4],'4. loadedmetadata、loadeddata、canplay、canplaythrough只处理加载状态，不触发新的教学播放。当前视频正常ended后可衔接下一镜头或场景；互动按实际规则完成且必要反馈结束后可衔接下一媒体。反馈结束事件或有界展示计时只负责已完成任务的交接，不代替作答。交接须核对当前场景、媒体、批次、阶段及未暂停，每次完成只触发一次；失效或取消回调不得播放。不得把新媒体归零或加载就绪当作首次播放前提。','正常教学完成后的自动衔接')
replace('M1',M[5],'5. 只有宿主提供context.autoplay且context.isActive()时，start(context)可同步尝试当前视频阶段首镜头一次；宿主为已进入课程的正常教学切场和教师跳转提供该请求，封面未进入、已手动暂停或无效预览不提供。mixed先H5时等待有效完成，再按第4条衔接，不跳过互动。H5提示音可按实际教学流程尝试播放；真实拒绝后提供声音重试，不用全屏遮罩阻挡独立可操作任务。听辨任务若明确要求先听完，播放失败不能伪作听完或直接放开判题。所有自动尝试都捕获拒绝，保持静帧并提供可操作恢复入口，不假定首次点击永久授予浏览器播放权限。','宿主连续入场请求')
F['M1'].update(name='媒体运行契约（工程联动候选）',filename='M1_媒体运行契约_联动候选.txt',reason='仅调整第2、4、5条的播放触发条件；第1、3、6条逐字保留。需开发同步运行层与检查器后启用，不是已上线契约。',route='P5/P6/P7/R1固定追加；候选须与正文及工程实现同批切换，禁止新旧叠加')

# H5 rules: business constraints only; no ordinary-H5 SDK/task schemas copied over.
buttons='文字按钮的自适应宽度和左右留白只作用于文字按钮，不写到所有按钮共用的cb基类。圆形纯图标按钮保持等宽等高、圆形底座、无额外水平内边距且不被父布局挤压；按钮缩放时同步调整内部cb-icon的width与height，图标不超出底座，不能只改font-size。只在已有对应打包本地样式引用时保留该有效引用；否则用平台指定地址，不猜路径或重复加载。'
interaction='用户未指定交互而选择拖拽配对、归类或排序时，同时支持先点对象再点目标，两种输入共用同一状态和判定；描摹、自由绘制等需要连续轨迹的任务除外。连续任务按有效轨迹、覆盖或落点判断，不凭点起点或按下即算完成。尚未形成有效作答的pointercancel、失焦或资源失败只恢复可继续状态，不记学生答错、重试或完成；已经有效确认的结果不被后续清理事件撤回。'
feedback='反馈先按教学目标与情境规划，可用场景变化、角色动作、物体状态、短文案或声音；需明确正误符号或星星时才选对应图标，不因图标库提供就新增评分、星级或奖励。'
audio='声音是否需要依据教学任务与用户要求决定，不要求老师必须说出“朗读”。完全无声同时关闭人声与音效，仅不要配音、音效或录音时只关闭对应能力。听辨任务明确要求听完才作答时，只在真实播放结束后解除该条件，加载或播放失败可重试、不冒充听完；其他可独立完成任务不被声音失败遮罩阻挡。播放、暂停图标必须与真实动作和状态一致。'
for k in ['P4','P5','P6','P7','R1']:
    anchor=next(x for x in F[k]['final'].splitlines() if x.startswith('类名映射：'))
    append_after(k,anchor,buttons,'H5按钮内外尺寸与有效资源')
    anchor=next(x for x in F[k]['final'].splitlines() if x.startswith('H5入场直接展示题目'))
    append_after(k,anchor,interaction+'\n'+feedback+'\n'+audio,'H5有效作答反馈与声音')
if 'H5入场直接展示题目' not in F['P3']['final']:
    anchor=next(x for x in F['P3']['final'].splitlines() if x.startswith('交互同时考虑'))
    append_after('P3',anchor,'未指定交互且选择拖拽配对、归类或排序时，兼容点对象再点目标；描摹或自由绘制等连续轨迹任务除外。反馈按教学目标与主题选择，不默认堆勾叉、星星或分数。','H5适配规划')

append_after('R1',F['R1']['final'].splitlines()[0],'修改范围涉及教学目标或设计风格时，保留已有字段类型，用短标签分行写明确决定；教学目标对应可观察结果，设计风格分开写画风配色、角色道具、题板、字体语言和声音，不改动范围外内容。','修改确认信息结构化')

for k in ['P4','P5','P6','P7','R1']:
    replace(k,'使用公共图标时，在HTML head有效引用一次<link rel="stylesheet" href="https://oss-xlss.xdf.cn/ig-kpm/resources/standard-icon.css">；这是样式依赖，不生成媒体assetId，也不要求模型读取URL查询用法。','使用公共图标时，已有经确认有效的对应打包本地CSS就沿用；否则在HTML head有效引用一次<link rel="stylesheet" href="https://oss-xlss.xdf.cn/ig-kpm/resources/standard-icon.css">。这是样式依赖，不生成媒体assetId，不重复加载，也不要求模型读取URL查询用法。','图标样式来源规则统一')
for k in ['P3','P5','P7']:
    old='视频开始前、片间等待和失败时有封面/静帧与清楚入口' if k=='P3' else '首次进入和每次重入均立即显示已加载可用的封面/静帧及清晰播放入口'
    if old in F[k]['final']:
        new='视频开始前、片间等待和失败时有封面/静帧；首次进入或真实播放失败才提供相应入口' if k=='P3' else '首次进入和每次重入均立即显示可用封面/静帧；首次进入、暂停恢复或真实播放失败时提供相应入口，正常衔接不重复确认'
        replace(k,old,new,'静帧与播放入口分开')

F['P3']['reason']='教学目标和设计风格按短标签分行，保留字符串协议；逐角色固定身份，明确教学用途、衔接与结束。'
F['P4']['reason']='角色基准覆盖封面与派生图；逐场完成条件与连贯流程；闭口参考图及最终透明文件；同步H5有效作答与按钮规则。'
for k in ['P5','P6','P7']:F[k]['reason']='移除与连续教学冲突的逐段点击约束，同步M1候选；保留playMedia修复和输出协议，补齐H5终态、声音失败与按钮适配。'
F['R1']['reason']='同步角色、素材、H5与连续教学规则；保留授权范围、工具协议、最小修改和交付保护。'
D.update(revision='2026-11-18-r13-coordinated',zip=PACKAGE.name+'.zip',summary=[
 '五项效果问题逐项列出旧规则、快照证据、候选改文与工程责任，避免把已写规则当作已修复。',
 '需求确认保留objective/designStyle字符串，改为短标签分行；确认卡片按行分组展示需前端配合。',
 '封面、视频与H5逐角色固定身份并引用真实基准；旁白镜头同时约束参考图和动作；透明素材按最终文件验收。',
 '连续教学规则在P3–P7、R1与M1候选一致；必须与固定运行层及程序检查器联动，不能只替换TXT。',
 '参考普通H5的11月18日候选，补齐教学目的、有效作答、整轮终态和圆形按钮内外尺寸；视频默认精美封面保持。',
 'P1/P2/P8、模板变量、JSON字段和开发用途/阶段固定后缀保持；M1第1/3/6条与已修复的加载归零能力保持。',
 '本次只发布评审与联动候选包；未替换Box配置、后端运行层或历史快照，不宣称真实生成回归已通过。'])
(ROOT/'review-data.json').write_text(json.dumps(D,ensure_ascii=False,indent=2))
(ROOT/'exact-patches.json').write_text(json.dumps(PATCHES,ensure_ascii=False,indent=2))
PACKAGE.mkdir(exist_ok=True)
fixed=PACKAGE/'05_代码固定追加约束';fixed.mkdir(exist_ok=True)
shutil.copy2(OLDPACK/'05_代码固定追加约束/创建固定约束_开发11月16日原文.json',fixed)
shutil.copy2(OLDPACK/'05_代码固定追加约束/M1_媒体运行硬契约_开发原文.txt',fixed)
(fixed/F['M1']['filename']).write_text(F['M1']['final'])
suffix=json.loads((fixed/'创建固定约束_开发11月16日原文.json').read_text())
for f in F.values():
 if not f.get('configPath'):continue
 p=PACKAGE/f['configPath'];p.parent.mkdir(exist_ok=True,parents=True);p.write_text(f['final'])
 tail='\n\n'+suffix['purposeIsolation']+'\n\n'+suffix['stageOutputs'][f['id']] if f['id'] in suffix['stageOutputs'] else '\n\n'+F['M1']['final'] if f['id'] in ['P5','P6','P7','R1'] else ''
 p=PACKAGE/f['systemMessagePath'];p.parent.mkdir(exist_ok=True,parents=True);p.write_text(f['final']+tail)
for name,ids in [('创建配置键与完整值.json',['P1','P2','P3','P4','P5','P6','P7']),('本次替换P3至P7配置_须联动.json',['P3','P4','P5','P6','P7'])]:
 (PACKAGE/name).write_text(json.dumps({F[k]['key']:F[k]['final'] for k in ids},ensure_ascii=False,indent=2))
for baseline,dirname in [('dev','06_相对开发基线差异'),('previous','09_相对r12差异')]:
 d=PACKAGE/dirname;d.mkdir(exist_ok=True)
 for f in F.values():
  delta=''.join(difflib.unified_diff(f[baseline].splitlines(True),f['final'].splitlines(True),fromfile=baseline+'/'+f['filename'],tofile='candidate/'+f['filename']))
  (d/(f['id']+'.diff')).write_text(delta or '无改动\n')
shutil.copytree(OLDPACK/'10_配套图标CSS',PACKAGE/'10_配套图标CSS',dirs_exist_ok=True)
(PACKAGE/'全部环节完整提示词.md').write_text('\n\n'.join('## '+f['id']+' '+f['name']+'\n\n```text\n'+f['final']+'\n```' for f in F.values()))
print(json.dumps({'revision':D['revision'],'changed':[f['id'] for f in F.values() if f['previous']!=f['final']],'patches':len(PATCHES),'package':str(PACKAGE)},ensure_ascii=False))
