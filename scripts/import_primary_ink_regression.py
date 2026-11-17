# -*- coding: utf-8 -*-
"""Append only this fixed-suite test version; retain all historical versions and ratings."""
from pathlib import Path
import json,hashlib,copy
SITE=Path(__file__).resolve().parent.parent
ROOT=Path('/Users/jolin/Documents/互动课件AI Agent/Obsidian Vault/03-AI互动课件制作/0312-20260813系统提示词效果固定测试集/runs/20261117-primary-ink')
VERSION='box-test-20261116-primary-ink';LABEL='11月16日测试版'
seedfile=SITE/'data/generation-experiment-seed.json';before=json.loads(seedfile.read_text());seed=copy.deepcopy(before);s=json.loads((ROOT/'test/generation-summary.json').read_text());requests=json.loads((ROOT/'requests.json').read_text());original={x['id']:x['prompt'] for x in requests['cases']};assert len(original)==28
results={x['id']:x for x in s['results']};allchecks=[]
for case in seed['cases']:
 if case.get('generationMode')=='manual':continue
 assert case['requirement']==original[case['id']]
 r=results.get(case['id'],{});v={k:r.get(k,'') for k in ['conversationId','fileUrl','pushUrl','fileName','snapshotId','finishedAt','startedAt','error']}
 v.update(id=VERSION,label=LABEL,group='固定测试集',taskId=f"fixed_{case['id']}_{VERSION}",status=r.get('status','pending'),prompt=case['requirement'],promptType='raw-user-requirement',environment='https://box.test.xdf.cn',generationMethod='box-pipeline-generate-only',generateMode='smart',published=False,evaluated=False,generationMessageId=r.get('messageId',''))
 check=ROOT/'test'/case['id']/'package-check.json'
 if check.exists():
  c=json.loads(check.read_text());allchecks.append(c);v['htmlSha256']=c['htmlSha256'];v['verification']={'scriptSyntax':'发现问题' if c['syntaxErrors'] else '通过','literalResourceReferences':'待核实' if c['missingLiteralReferences'] else '通过','audioDecode':'发现问题' if c['audioDecodeErrors'] else '通过' if c['audioFiles'] else '无音频文件','audioFileCount':c['audioFiles'],'interaction':'待验证','audioListening':'待验证','visualStatus':'待验证','scope':c['scope'],'reviewNote':'仅做包内基础检查；未自动评分、迭代或上架。请按实际画面和操作人工评审。'}
  findings=[]
  for err in c['syntaxErrors']:findings.append({'title':'脚本语法检查未通过','detail':err['file']+'：'+err['error'][:220]})
  for err in c['missingLiteralReferences']:findings.append({'title':'字面资源路径待核实','detail':err['file']+' → '+err['reference']})
  if findings:v['verification']['sourceFindings']=findings
 http=ROOT/'test'/case['id']/'http-check.json'
 if http.exists():
  h=json.loads(http.read_text());v.setdefault('verification',{}).update(httpResourceCount=h['checkedCount'],httpFailureCount=h['failureCount'])
 case['versions']=[x for x in case.get('versions',[]) if x['id']!=VERSION]+[v]
old=before.get('currentRun');history=seed.setdefault('runHistory',[])
if old and old.get('id')!=VERSION and not any(x.get('id')==old.get('id') for x in history):history.append(old)
seed['generatedAt']=s['updatedAt'];seed['currentRun']={'id':VERSION,'label':LABEL,'environment':'https://box.test.xdf.cn','generateMode':'smart','updatedAt':s['updatedAt'],'successCount':s['successCount'],'failureCount':s['failureCount'],'pendingCount':s['pendingCount'],'automaticCaseCount':28,'manualCaseCount':2,'comparisonType':'historical','requestsSha256':s['requestsSha256'],'note':'版本名称按用户指定为“11月16日测试版”；实际执行于2026年11月17日。固定28条需求原文不变，标准模式smart，仅生成首版。右侧下拉切换测试版本，左侧保留已有线上版本。','boundary':'所有历史课件、版本ID和评分关联保留；2条录音/口语用例待手动生成，不计失败。本轮不自动评分、迭代或上架。','basicCheckNote':f"已检查 {len(allchecks)}/28 份课件包；JS语法发现问题 {sum(bool(c['syntaxErrors']) for c in allchecks)} 份，字面资源路径待核实 {sum(bool(c['missingLiteralReferences']) for c in allchecks)} 份，音频解码异常 {sum(bool(c['audioDecodeErrors']) for c in allchecks)} 份。",'verificationNote':'仅生成及基础包检查；实屏、触控、完整通关和听感待人工验证。生成成功不代表质量通过，不计算效果提升率。','historicalBaselineNote':'左侧沿用网站已有线上结果，包括0813版本；本轮没有重新生成线上对照。'}
# No deletion/mutation of historical cases or versions, including all manual cases.
def retained(d):return [{**c,'versions':[v for v in c.get('versions',[]) if v['id']!=VERSION]} for c in d['cases']]
assert retained(before)==retained(seed)
assert len([c for c in seed['cases'] if any(v['id']==VERSION for v in c.get('versions',[]))])==28
if not (ROOT/'website-seed-before.json').exists():(ROOT/'website-seed-before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2))
seedfile.write_text(json.dumps(seed,ensure_ascii=False,indent=2)+'\n')
(ROOT/'website-import-verification.json').write_text(json.dumps({'versionId':VERSION,'label':LABEL,'frozenRequestsUnchanged':True,'historicalVersionsPreserved':True,'manualCasesPreserved':True,'resultCount':len(results),'checks':len(allchecks)},ensure_ascii=False,indent=2))
print(LABEL,s['successCount'],'success',s['failureCount'],'failed',s['pendingCount'],'pending; history preserved')
