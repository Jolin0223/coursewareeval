"""Offline artifact checks only. Real backend rendering and generation are separate gates."""
from pathlib import Path
import json,re,hashlib,sys,copy
R=Path(__file__).resolve().parent;P=R.parent
D=json.loads((R/'review-data.json').read_text());PATCH=json.loads((R/'exact-patches.json').read_text());LOCK=json.loads((R/'locked-sha256.json').read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def variables(s):return re.findall(r'\{\{voice_names\}\}|\{(?:task_content|html_code_content|to_fix_content|input)\}',s)
def validate(d):
 errors=[]
 for f in d['files']:
  k=f['id'];s=f['final'];expected=f['previous']
  for x in [x for x in PATCH if x['id']==k]:
   if expected.count(x['before'])!=x.get('count',1):errors.append(k+': patch anchor')
   expected=expected.replace(x['before'],x['after'])
   if '{' in x['after'] or '}' in x['after']:errors.append(k+': new literal brace')
  if s!=expected:errors.append(k+': unreviewed text delta')
  if variables(s)!=variables(f['dev']):errors.append(k+': variables changed')
  if re.search(r'(?i)\br(?:9|10|11|12|13)\b|2\.2\.2|新增规则|图标同步|本轮合并|上一版提示词|2026[-.]11',s):errors.append(k+': prompt history')
 return errors
def check_message(actual,expected):return actual==expected
errors=validate(D);
for f in D['files']:
 if f['id'] in ['P3','P4','P5','P6','P7','R1','M1'] and any(x in f['final'] for x in ['每一段视频均由可见播放或继续播放按钮的点击启动','教师工具首镜头例外不授权普通入场']):errors.append(f['id']+': stale manual playback rule')
files={f['id']:f for f in D['files']}
fixed=P/'05_代码固定追加约束'
for n,h in LOCK.items():
 if sha((fixed/n).read_bytes())!=h:errors.append('locked suffix changed: '+n)
suffix=json.loads((fixed/'创建固定约束_开发11月16日原文.json').read_text());m=files['M1']['final']

for n in [1,3,6]:
 if m.splitlines()[n]!=files['M1']['previous'].splitlines()[n]:errors.append('protected M1 clause '+str(n))
if (fixed/files['M1']['filename']).read_text()!=m:errors.append('candidate M1 mismatch')
for k in ['P1','P2','P8']:
 if files[k]['final']!=files[k]['previous']:errors.append(k+': unchanged stage modified')
for f in D['files']:
 k=f['id']
 if not f.get('configPath'):continue
 s=(P/f['configPath']).read_text()
 if s!=f['final']:errors.append(k+': config TXT mismatch')
 tail='\n\n'+suffix['purposeIsolation']+'\n\n'+suffix['stageOutputs'][k] if k in suffix['stageOutputs'] else '\n\n'+m if k in ['P5','P6','P7','R1'] else ''
 if not check_message((P/f['systemMessagePath']).read_text(),s+tail):errors.append(k+': SystemMessage/suffix mismatch')
for name,ids in [('创建配置键与完整值.json',['P1','P2','P3','P4','P5','P6','P7']),('本次替换P3至P7配置_须联动.json',['P3','P4','P5','P6','P7'])]:
 if json.loads((P/name).read_text())!={files[k]['key']:files[k]['final'] for k in ids}:errors.append(name+': config JSON mismatch')
css=(P/'10_配套图标CSS/standard-icon.css').read_text();available=set(re.findall(r'\.(cb-icon-[a-z-]+)\b',css))
for k in ['P4','P5','P6','P7','R1']:
 used=set(re.findall(r'cb-icon-[a-z-]+',files[k]['final']))
 if not used<=available:errors.append(k+': undefined icon '+str(used-available))
 if len(used)!=24:errors.append(k+': icon catalog incomplete')
# Negative cases must fail, to protect against the actual prior regression classes.
negative=[]
for label,mutate in [('css_brace',lambda s:s+'\n.x{width:120px}'),('renamed_variable',lambda s:s.replace('{task_content}','{task_contents}')),('history',lambda s:'r12调试版本\n'+s)]:
 trial=copy.deepcopy(D);f=next(f for f in trial['files'] if f['id']=='P5');f['final']=mutate(f['final']);negative.append({'case':label,'rejected':bool(validate(trial))})
negative.append({'case':'duplicate_fixed_suffix','rejected':not check_message(files['P5']['final']+'\n\n'+m+'\n\n'+m,files['P5']['final']+'\n\n'+m)})
if not all(x['rejected'] for x in negative):errors.append('negative-case checker failed')
report={'revision':D['revision'],'staticChecksPassed':not errors,'errors':errors,'stages':len(files),'developerOriginalSuffixFilesLocked':True,'mediaContractChangedClauses':[2,4,5],'mediaContractProtectedClauses':[1,3,6],'iconClasses':len(available),'negativeCases':negative,'backendTemplateRun':'not_run','generationRegression':'not_run','releaseReadiness':'requires_runtime_checker_template_validation_and_generation_regression','knownDeveloperIssue':'P4 durationSeconds sentence mixes seconds and reference count; fixed server suffix intentionally unchanged'}
(R/'校验结果.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(1 if errors else 0)
