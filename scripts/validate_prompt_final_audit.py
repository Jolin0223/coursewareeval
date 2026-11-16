from pathlib import Path
import re,json,zipfile,hashlib
B=Path('Obsidian Vault/03-AI互动课件制作');root=B/'20261116-系统提示词完整复核';base=B/'20261116-图标审查与模板安全修复/prompts';css=(B/'20261116-反馈图标接入修复-2.2.2/css/standard-icon.css').read_text();checks=[]
for p in sorted((root/'prompts').glob('*.txt')):
 s=p.read_text();old=(base/p.name).read_text();tokens=lambda t:re.findall(r'(?<![\\{])\{([^{}]*?)(?<!\\)\}(?!\})',t)
 assert tokens(s)==tokens(old)
 for k in [r'\{',r'\}',r'\%', '{{voice_names}}']:assert s.count(k)==old.count(k),(p.name,k)
 assert not re.search(r'旧版|上一版|本次优化|最新版本|V2|badcase|F0[1-4]|cb-icon-check|cb-icon-right|cb-icon-refresh|整图封面原规则|统一改用 Pointer',s)
 classes=set(re.findall(r'cb-icon-[a-z-]+',s));assert len(classes)==24,(p.name,len(classes));assert all(re.search(r'\.'+re.escape(c)+r'\s*\{',css) for c in classes)
 if 'developer' in p.name or 'fixer' in p.name:assert '完整代码' in s and '使用一个' in s and '围栏仅为回复的格式边界' in s
 if 'architect' in p.name:assert all(k in s for k in ['imageTasks','audioTasks','codeTasks','reportMetrics','taskDetails']) and '在相关HTML代码任务的taskDetails中明确加入 <link' not in s
 if 'reviewer' in p.name:assert all(k in s for k in ['bugList','isPassReview','filePath','fileBugDescription'])
 checks.append({'file':p.name,'variablesUnchanged':True,'escapingUnchanged':True,'iconClassesMatchCSS':True,'noRevisionResidue':True,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
with zipfile.ZipFile(root/'complete-prompts.zip') as z:
 assert len(z.namelist())==9 and z.testzip() is None
 for p in (root/'prompts').glob('*.txt'):assert z.read(p.name)==p.read_bytes()
(root/'交付校验.json').write_text(json.dumps({'scope':'静态文本和打包一致性；不是后台实际模板引擎或模型生成效果验收','checks':checks,'zipOnlyNinePrompts':True},ensure_ascii=False,indent=2));print('9 templates: tokens/escapes,24-class allowlists,protocol markers,revision scan,ZIP bytes passed')
