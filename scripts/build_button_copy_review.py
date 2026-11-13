# -*- coding: utf-8 -*-
"""Integrate the approved button-copy package into existing review rounds."""
from pathlib import Path
import argparse,json,re,hashlib,difflib,shutil
ap=argparse.ArgumentParser();ap.add_argument('package',type=Path);args=ap.parse_args()
root=Path(__file__).resolve().parent.parent;pkg=args.package.resolve()
src=json.loads((pkg/'评审数据.json').read_text());base_data=json.loads(re.search(r'<script id="font-packaging-data" type="application/json">(.*?)</script>',(root/'system-prompt-review.html').read_text(),re.S).group(1))
metadata={f['key']:f for f in base_data['files']}
data={'title':'按钮文案分场景 · 最新候选','date':'2026-11-13','baseline':'改前：字体随包确认版。改后：单题 Retry、最终结果弹窗整轮重玩 Try again，不额外添加 Done 确认按钮。','revision':'20261113-button-copy-v1','compatibleBaseline':'','removedChangeIds':[],'files':[],'changes':[],'issues':[],'cases':{'单题':{},'结算':{},'Done':{}},'evidence':{'单题':'用户确认：单题会有 Retry 按钮，保留重试当前题的含义。','结算':'用户确认：最后弹窗上的整轮重玩使用 Try again，不是 Retry。','Done':'用户确认：出现完成弹窗已表示答完，正常场景不需要额外的 Done 文案图标。'},'history':'本页仅评审，尚未部署本次文案候选；12例专项测试发生在本轮文案修订之前。历史课件不批量修改。','excluded':'字体缺失已确认是资源未上传，本轮忽略，不作为提示词缺陷。字体规则、图标CSS资源与其他提示词内容保持基线。','devTasks':[{'id':'BC-DEV1','title':'更新九份完整TXT','links':[],'cases':[],'action':'按本页或完整ZIP替换对应九个环节提示词。保留现有输出结构、单文件修复边界及字体随包流程。','done':'单题 Retry 与结果弹窗 Try again 按各自操作范围实现，常规完成弹窗不额外添加 Done。'},{'id':'BC-DEV2','title':'无需重新上传图标CSS','links':[],'cases':[],'action':'两种重试继续复用 cb-icon-retry，不重命名类名或 retry_count 等字段。新提示词不再推荐完成确认入口，CSS保留旧 cb-icon-done 兼容历史课件。','done':'CDN文件保持原版；没有因删除旧图标资源导致历史课件失效。'},{'id':'BC-DEV3','title':'部署后按操作范围复测','links':[],'cases':['单题','结算'],'action':'单题 Retry 只重试当前题；最终弹窗 Try again 从第一题开始新一轮并重置本轮进度与成绩。纯文案修改不顺带改作答或计分规则。','done':'分别验证两类按钮，原有继续/关闭等有实际用途的入口正常；不增加 Done 二次确认。'}]}
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def units(s):return len(s.encode('utf-16-le'))//2
for item in src['changes']:
 key=item['file'][:-4];m=metadata[key];old=item['before'];new=item['after'];ol=old.splitlines(True);nl=new.splitlines(True);changes=[]
 for tag,i,j,k,l in difflib.SequenceMatcher(None,ol,nl).get_opcodes():
  if tag=='equal':continue
  before=''.join(ol[i:j]);after=''.join(nl[k:l]);id=f"BC{m['order']:02d}-{len(changes)+1}"
  if '常用图标调用清单' in after:title='不再把完成图标列入常用入口';why='保留图标库兼容性，只从默认推荐清单中移除多余完成入口。';cases=['Done']
  elif '优先使用Start' in after:title='去掉方案设计中优先使用 Done 的示例';why='从上游移除 Done 的默认推荐，避免后续环节将示例变成必加按钮。';cases=['Done']
  else:title='单题 Retry，结算整轮重玩 Try again';why='按操作范围区分文案和真实动作，避免全局替换；当前环节落实对应职责。';cases=['单题','结算','Done']
  change={'id':id,'file':key,'title':title,'kind':'替换','where':m['title']+' → 按钮文案与调用规范','why':why,'cases':cases,'note':'本轮仅调整文案与多余完成入口；字体问题已确认属于资源未上传，不在此修改。','requires':[],'old':before,'new':after,'start':units(''.join(ol[:i])),'end':units(''.join(ol[:j])),'line':i+1}
  changes.append(change);data['changes'].append(change)
 data['files'].append({**{k:m[k] for k in ['key','title','phase','purpose','order']},'original':old,'revised':new,'newline':'LF','sourceSha256':sha(old),'revisedSha256':sha(new),'originalChars':units(old),'revisedChars':units(new),'changed':True,'changes':changes,'issues':[],'unchangedReason':'','diff':[]})
out=root/'button-copy-review';out.mkdir(exist_ok=True)
(out/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
shutil.copytree(pkg/'prompts',out/'prompts',dirs_exist_ok=True)
shutil.copyfile(str(pkg)+'.zip',out/'complete-prompts.zip');shutil.copyfile(pkg/'交付说明.md',out/'README.md');shutil.copyfile(pkg/'改动对比.diff',out/'changes.diff')
overview='''function buttonCopyOverview(){return `<div class="revision-note"><strong>按操作范围命名，不全局替换 Retry</strong><p><b>单题 / 当前步骤：</b>Retry，只重试当前题或步骤。<br><b>最终结果弹窗：</b>Try again，从第一题重新玩一轮，重置本轮进度与成绩。<br><b>完成反馈：</b>弹窗已表明答完，不额外添加 Done/完成确认按钮；有实际用途的继续、关闭等操作按需求保留。</p><p>中文课件使用对应中文文案，用户明确指定优先。修改环节仅处理本轮涉及内容，不顺带改无关作答、切题或计分逻辑。</p><p><b>字体说明：</b>字体缺失已确认是资源未上传，本轮忽略，不作为提示词问题；字体规则保持原样。</p><p><a href="/button-copy-review/complete-prompts.zip">下载九份完整TXT＋开发说明</a> · <a href="/button-copy-review/changes.diff">下载精确diff</a></p></div><table class="overview"><thead><tr><th>环节</th><th>本轮修改</th><th>查看</th></tr></thead><tbody>${DATA.files.map(f=>`<tr><td>${f.order}. ${esc(f.title)}</td><td>${esc(f.changes.map(c=>c.title).join('；'))}</td><td><button data-file="${f.key}">原文 / 改后 ↗</button></td></tr>`).join('')}</tbody></table><p class="summary-footer">${esc(DATA.history)} 原文灰色保留，替换标红，新增标绿；评审记录与历史轮次独立。</p>${devGuide()}`}\n'''
for name in ['system-prompt-review.html','font-packaging-review.html','resource-contract-review.html']:
 p=root/name;s=p.read_text()
 assert 'button-copy-data' not in s,'Already patched'
 s=s.replace('<button data-round="font-packaging">11月13日 字体随包 · 最新修订</button>','<button data-round="button-copy">11月13日 按钮文案分场景 · 最新候选</button><button data-round="font-packaging">11月13日 字体随包 · 上一轮</button>')
 block='<script id="button-copy-data" type="application/json">'+json.dumps(data,ensure_ascii=False).replace('</','<\\/')+'</script>\n'
 s=s.replace('<script>const FONT_PACKAGING_DATA=',block+'<script>const BUTTON_COPY_DATA=JSON.parse(document.getElementById("button-copy-data").textContent);const FONT_PACKAGING_DATA=')
 s=s.replace("const roundData={","const roundData={'button-copy':BUTTON_COPY_DATA,")
 if name=='system-prompt-review.html':s=re.sub(r"let round=Object.hasOwn\(roundData,requestedRound\)\?requestedRound:'[^']+';","let round=Object.hasOwn(roundData,requestedRound)?requestedRound:'button-copy';",s)
 s=s.replace('function renderOverview(){',overview+"function renderOverview(){if(round==='button-copy')return buttonCopyOverview();")
 s=s.replace('function caseHtml(id){',"function caseHtml(id){if(round==='button-copy')return `<span class=\"case-link\">${esc(id)} · 用户确认</span>`;")
 s=s.replace("if(round==='font-packaging'){$('#round-label')", "if(round==='button-copy'){$('#round-label').textContent=DATA.title;$('#review-title').textContent='单题 Retry · 结算 Try again';$('#review-intro').textContent=DATA.baseline;$('#export-candidate').textContent='下载9份完整候选 TXT';}\nif(round==='font-packaging'){$('#round-label')")
 s=s.replace("download(round==='font-packaging'?", "download(round==='button-copy'?(selectedOnly?'按钮文案_已采纳.zip':'按钮文案分场景_九份完整候选.zip'):round==='font-packaging'?")
 p.write_text(s)
print('Integrated',len(data['files']),'files /',len(data['changes']),'changes into 3 existing review pages')
