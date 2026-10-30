// Read-only net comparison. Historical review decisions and prompt text stay untouched.
function cumulativeBody(){
 const f=DATA.files.find(f=>f.key===state.file);
 const summary={1:'内容容器与字号、音效、精美封面、拖拽配点击、按用途切题',2:'方案约束落到文件任务，区分音频职责，封面资源与接入分工',6:'限定修改范围，拆清连续步骤，落实封面与交互要求',8:'按本轮修改意图复核，避免恢复用户已删内容',9:'修复限于当前文件，清理失效引用，不恢复已删内容'};
 if(!f)return `<div class="file-heading"><div><h2>上线前 → 六轮后最终版</h2><p>9 个环节 · 5 个有累计改动 · 4 个保持原文</p></div><button data-cumulative-zip>下载前后完整 TXT（18份）</button></div><p class="revision-note">左侧基线：最初修正后的「互动课件提示词(1)」原文。右侧终点：10月30日「封面三环节职责分层」最终交付稿，包含此前各轮保留下来的改动。用户已确认发布；此处未回读生产环境加载内容。中途撤回或被替换的方案不计入净改动。</p><table class="overview"><thead><tr><th>环节</th><th>累计结果</th><th>主要改动</th></tr></thead><tbody>${DATA.files.map(x=>`<tr><td><button data-file="${x.key}">${x.order}. ${esc(x.title)}</button><small>${esc(x.key)}</small></td><td>${x.changed?x.changes.length+' 处差异':'原文保留'}</td><td>${esc(summary[x.order]||'无累计改动')}</td></tr>`).join('')}</tbody></table><p class="summary-footer">点击环节查看红绿对照。此页只展示最终净差异，不重新收集采纳决定；六轮评审记录仍保留在原页签。修复智能体沿用单文件边界，不要求跨文件修改。本次仅更新评审展示，不改提示词或历史课件 HTML。</p>`;
 const side=(left,right)=>`<div class="diff"><section class="diff-side"><div class="diff-label">上线前 · 原始提示词</div><pre class="before">${left}</pre></section><section class="diff-side"><div class="diff-label">六轮后 · 最终交付稿</div><pre class="after">${right}</pre></section></div>`;
 let body=state.view==='full'?side(f.beforeHtml,f.afterHtml):state.view==='original'?`<div class="prompt-full"><pre>${esc(f.original)}</pre></div>`:state.view==='final'?`<div class="prompt-full"><pre>${esc(f.revised)}</pre></div>`:f.changed?f.changes.map((c,i)=>`<article class="change-card"><div class="change-head"><h3>累计差异 ${i+1} · ${!c.old?'新增':!c.new?'删除':'替换'}</h3><span class="where">原文第 ${c.line} 行 → 最终稿第 ${c.finalLine} 行</span></div>${side(c.old?`<span class="del-mark">${esc(c.old)}</span>`:'<span class="empty-old">原文无此内容</span>',c.new?`<span class="add-mark">${esc(c.new)}</span>`:'<span class="empty-old">最终稿已移除此内容</span>')}</article>`).join(''):'<div class="empty"><strong>本环节前后完全一致</strong>可查看完整全文或下载 TXT。</div>';
 return `<div class="file-heading"><div><h2>${f.order}. ${esc(f.title)}</h2><div class="file-key">${esc(f.key)}.txt</div></div><div class="file-tools"><button data-cumulative-before="${f.key}">下载上线前 TXT</button><button data-copy="${f.key}">复制最终全文</button><button data-download="${f.key}">下载最终 TXT</button></div></div><div class="toolbar"><div class="tabs">${[['diff','逐项净改动'],['full','完整对照'],['original','上线前全文'],['final','最终全文']].map(([v,t])=>`<button class="tab ${state.view===v?'active':''}" data-view="${v}">${t}</button>`).join('')}</div></div><p class="legend">红色：原文删除或替换 · 绿色：最终新增 · 未着色：保留原文</p>${body}`;
}
function renderCumulative(){
 $('#round-label').textContent='系统提示词评审 · 累计对比';
 $('#review-title').textContent='从上线前原文，直接看到最终改动';
 $('#review-intro').textContent='合并六轮结果，只展示最终保留的改动；无需逐轮拼接，也不把前一轮候选当成上线前基线。';
 document.querySelectorAll('[data-round]').forEach(x=>{x.classList.toggle('active',x.dataset.round===round);x.setAttribute('aria-pressed',x.dataset.round===round)});
 document.querySelectorAll('.history-only').forEach(x=>x.hidden=true);
 ['export-selected','export-candidate','export-review','import-review'].forEach(id=>{if($('#'+id))$('#'+id).hidden=true});
 renderNav();$('#main').innerHTML=cumulativeBody();$('#changed-files').textContent=5;$('#pending-count').textContent='—';$('#accepted-count').textContent='—';$('#storage-label').textContent='累计对比只读；原评审记录保持不变';
}
document.addEventListener('click',e=>{
 const b=e.target.closest('button');if(!b)return;
 if(b.dataset.cumulativeBefore){const f=DATA.files.find(f=>f.key===b.dataset.cumulativeBefore);download(f.key+'_上线前.txt',crlf(f.original))}
 if(b.hasAttribute('data-cumulative-zip')){const entries=DATA.files.flatMap(f=>[['上线前/'+f.key+'.txt',crlf(f.original)],['最终版/'+f.key+'.txt',crlf(f.revised)]]);entries.push(['版本说明.txt','基线：互动课件提示词(1)修正原文。终点：10月30日最终交付稿。未回读生产环境实际提示词。']);download('系统提示词_上线前与六轮后最终版.zip',zip(entries),'application/zip')}
});
