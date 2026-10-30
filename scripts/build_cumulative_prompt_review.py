"""Derive a read-only baseline-to-final comparison from the six retained rounds."""
from pathlib import Path
import re,json,hashlib,difflib,html
p=Path(__file__).resolve().parents[1]/'system-prompt-review.html'
s=p.read_text()
d={k:json.loads(v) for k,v in re.findall(r'<script type="application/json" id="([^"]+)">(.*?)</script>',s,re.S)}
base=d['review-data'];final=d['cover-roles-data'];files=[]
for b,f in zip(base['files'],final['files']):
 assert b['key']==f['key']
 a,z=b['original'],f['revised'];al=a.splitlines(True);zl=z.splitlines(True)
 before=[];after=[];changes=[]
 for tag,i,j,k,l in difflib.SequenceMatcher(None,al,zl,autojunk=False).get_opcodes():
  old=''.join(al[i:j]);new=''.join(zl[k:l]);bo=html.escape(old);af=html.escape(new)
  if tag!='equal':
   bo='<span class="del-mark">'+bo+'</span>';af='<span class="add-mark">'+af+'</span>'
   changes.append({'old':old,'new':new,'line':i+1,'finalLine':k+1})
  before.append(bo);after.append(af)
 row={key:b[key] for key in ['key','title','order','phase']}
 row.update(original=a,revised=z,changed=a!=z,changes=changes,sourceSha256=hashlib.sha256(a.encode()).hexdigest(),revisedSha256=hashlib.sha256(z.encode()).hexdigest(),beforeHtml=''.join(before),afterHtml=''.join(after))
 # Each side must reproduce the exact saved text, not a patch chain.
 assert ''.join(al)==a and ''.join(zl)==z
 files.append(row)
data={'title':'上线前 → 六轮后最终版','baseline':'最初修正后的互动课件提示词(1)原文 → 10月30日最终交付稿','files':files,'changes':[]}
block='<script type="application/json" id="cumulative-data">'+json.dumps(data,ensure_ascii=False,separators=(',',':'))+'</script>'
s=re.sub(r'<script type="application/json" id="cumulative-data">.*?</script>\n?','',s,flags=re.S)
s=s.replace('<script type="application/json" id="cover-roles-data">',block+'\n<script type="application/json" id="cover-roles-data">')
p.write_text(s)
print(json.dumps({'files':len(files),'changed':sum(f['changed'] for f in files),'diffBlocks':sum(len(f['changes']) for f in files)}))
