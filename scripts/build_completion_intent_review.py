# -*- coding: utf-8 -*-
"""Add the completion-intent review without replacing the previous round."""
from pathlib import Path
import argparse,json,re,hashlib,difflib,shutil
ap=argparse.ArgumentParser();ap.add_argument('package',type=Path);pkg=ap.parse_args().package.resolve();root=Path(__file__).resolve().parent.parent
src=json.loads((pkg/'评审数据.json').read_text());prev=json.loads((root/'button-copy-review/data.json').read_text());meta={f['key']:f for f in prev['files']}
data={**prev,'title':'完成操作按场景 · 待研发确认','revision':'20261113-completion-intent-v1','baseline':'改前：上一轮按钮文案分场景版。改后：保留必要主动结束/提交，取消结果已展示后的多余 Done 确认。Retry / Try again 不变。','files':[],'changes':[],'cases':{'必要结束':{},'结果弹窗':{},'状态标签':{}},'evidence':{'必要结束':'用户确认：绘画、搭建、录音或确认最终选择等场景，应保留实际需要的结束/提交操作，并写清具体动作。','结果弹窗':'用户确认：结果已展示时不需要再确认完成；单题 Retry 与整轮 Try again 按操作范围区分。','状态标签':'用户确认：已完成可作状态展示，不做成没有实际动作的按钮。'},'history':'本轮候选待研发确认，未替换服务端提示词、未跑新版效果测试。历史HTML不批量修改。','excluded':'字体已确认属于资源未上传，本轮不计为提示词问题。字体、封面、SDK、单文件修复与CSS资源保持原样。'}
data['devTasks']=[{'id':'CI-DEV1','title':'确认九环节候选并部署','links':[],'cases':[],'action':'使用本轮九份完整TXT。保留现有输入输出协议和单文件修复能力，不全局替换Done或删除所有完成入口。','done':'必要主动结束/提交入口保留；结果已展示后无多余完成二次确认。'},{'id':'CI-DEV2','title':'CSS资源无需更新','links':[],'cases':[],'action':'cb-icon-done按语义匹配复用，不代表必加按钮。Retry与Try again继续用cb-icon-retry；资源、类名和接口字段不变。','done':'当前CSS继续使用，历史课件不受影响。'},{'id':'CI-DEV3','title':'部署后验证五类场景','links':[],'cases':['必要结束','结果弹窗','状态标签'],'action':'验证单题Retry、结算Try again、自由绘画或录音结束、必要作答提交、非交互完成标签；不能因完成字样误删入口。','done':'文案与真实动作匹配；单题重试不重开整轮，整轮重玩重置本轮进度与成绩；无额外Done确认。'}]
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def units(s):return len(s.encode('utf-16-le'))//2
for item in src['changes']:
 key=item['file'][:-4];m=meta[key];old=item['before'];new=item['after'];ol=old.splitlines(True);nl=new.splitlines(True);changes=[]
 for tag,i,j,k,l in difflib.SequenceMatcher(None,ol,nl).get_opcodes():
  if tag=='equal':continue
  before=''.join(ol[i:j]);after=''.join(nl[k:l]);catalog='图标调用清单（16个' in after
  change={'id':f"CI{m['order']:02d}-{len(changes)+1}",'file':key,'title':'完成图标按语义匹配选用，不必生成按钮' if catalog else '按用途保留必要结束操作，移除多余确认','kind':'替换','where':m['title']+' → 按钮与完成反馈规则','why':'明确资源可用与必须生成入口是两回事；不删除CSS能力。' if catalog else '避免把“不加多余Done”误解为所有完成、结束或提交操作都不能出现。','cases':['必要结束','结果弹窗','状态标签'],'note':'单题 Retry、整轮 Try again 保持；字体和其他任务规则不变。','requires':[],'old':before,'new':after,'start':units(''.join(ol[:i])),'end':units(''.join(ol[:j])),'line':i+1}
  changes.append(change);data['changes'].append(change)
 data['files'].append({**m,'original':old,'revised':new,'sourceSha256':sha(old),'revisedSha256':sha(new),'originalChars':units(old),'revisedChars':units(new),'changed':True,'changes':changes,'diff':[]})
out=root/'completion-intent-review';out.mkdir(exist_ok=True);(out/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2));shutil.copytree(pkg/'prompts',out/'prompts',dirs_exist_ok=True)
for a,b in [('交付说明.md','README.md'),('改动对比.diff','changes.diff')]:shutil.copyfile(pkg/a,out/b)
shutil.copyfile(str(pkg)+'.zip',out/'complete-prompts.zip')
overview='''function completionIntentOverview(){return `<div class="revision-note"><strong>取消多余确认，保留必要结束操作</strong><p>不是看到 Done/完成 就删除，而是判断点击是否完成了一项必要操作。</p><table class="overview"><thead><tr><th>场景</th><th>本轮规则</th></tr></thead><tbody><tr><td>单题 / 当前步骤重试</td><td>Retry，只重试当前题或步骤。</td></tr><tr><td>最终弹窗整轮重玩</td><td>Try again，从第一题开始，重置本轮进度与成绩。</td></tr><tr><td>全部答完，结果已展示</td><td>不再添加 Done/完成 二次确认；保留有实际用途的后续操作。</td></tr><tr><td>绘画、搭建、录音或确认最终作答</td><td>保留必要结束/提交入口，优先“画好了”“搭好了”“结束录音”“提交答案”等准确动作文案；英语用对应英文，需表达“我做完了”时可用 I’m done。</td></tr><tr><td>仅标记某关已完成</td><td>非交互状态标签，不伪装成按钮。</td></tr></tbody></table><p>遵循课件语言，用户明确指定优先；不因举例新增操作。字体缺失已确认是资源未上传，本轮忽略，字体规则不改。</p><p><a href="/completion-intent-review/complete-prompts.zip">下载九份完整TXT＋开发说明</a> · <a href="/completion-intent-review/changes.diff">下载本轮精确diff</a></p></div><table class="overview"><thead><tr><th>环节</th><th>本轮修改</th><th>查看</th></tr></thead><tbody>${DATA.files.map(f=>`<tr><td>${f.order}. ${esc(f.title)}</td><td>${esc(f.changes.map(c=>c.title).join('；'))}</td><td><button data-file="${f.key}">原文 / 改后 ↗</button></td></tr>`).join('')}</tbody></table><p class="summary-footer">${esc(DATA.history)} 与上一轮红绿对比；旧页签与评审记录保留。</p>${devGuide()}`}\n'''
for name in ['system-prompt-review.html','font-packaging-review.html','resource-contract-review.html']:
 p=root/name;s=p.read_text();assert 'completion-intent-data' not in s
 s=s.replace('<button data-round="button-copy">11月13日 按钮文案分场景 · 最新候选</button>','<button data-round="completion-intent">11月13日 完成操作按场景 · 待研发确认</button><button data-round="button-copy">11月13日 按钮文案分场景 · 上一轮</button>')
 block='<script id="completion-intent-data" type="application/json">'+json.dumps(data,ensure_ascii=False).replace('</','<\\/')+'</script>\n'
 s=s.replace('<script>const BUTTON_COPY_DATA=',block+'<script>const COMPLETION_INTENT_DATA=JSON.parse(document.getElementById("completion-intent-data").textContent);const BUTTON_COPY_DATA=')
 s=s.replace('const roundData={',"const roundData={'completion-intent':COMPLETION_INTENT_DATA,")
 if name=='system-prompt-review.html':s=s.replace("?requestedRound:'button-copy';","?requestedRound:'completion-intent';")
 s=s.replace('function renderOverview(){',overview+"function renderOverview(){if(round==='completion-intent')return completionIntentOverview();")
 s=s.replace("if(round==='button-copy')return `<span class=\"case-link\">", "if(round==='button-copy'||round==='completion-intent')return `<span class=\"case-link\">")
 s=s.replace("if(round==='button-copy'){$('#round-label')", "if(round==='completion-intent'){$('#round-label').textContent=DATA.title;$('#review-title').textContent='保留必要结束操作 · 取消多余完成确认';$('#review-intro').textContent=DATA.baseline;$('#export-candidate').textContent='下载9份完整候选 TXT';}\nif(round==='button-copy'){$('#round-label')")
 s=s.replace("download(round==='button-copy'?", "download(round==='completion-intent'?(selectedOnly?'完成操作按场景_已采纳.zip':'完成操作按场景_九份完整候选.zip'):round==='button-copy'?")
 p.write_text(s)
print('Integrated',len(data['files']),'files /',len(data['changes']),'changes')
