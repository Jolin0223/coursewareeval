function renderHitareaHeader(){
 $('#round-label').textContent='系统提示词评审 · 整图封面全屏入口';
 $('#review-title').textContent='整图封面整页可点，不再猜按钮位置';
 $('#review-intro').textContent='基于 T15 的真实问题补齐执行与审查：②⑥架构拆任务、③⑦代码实现、④⑧审查拦截、⑤⑨按指定文件修复。①方案设计保留。本轮是待评审候选，尚未发布或复测。';
 $('#export-candidate').textContent='下载8份修改后的完整 TXT';
}
function hitareaOverview(){return `<div class="revision-note"><strong>本轮采用的规则</strong><p>对于整个封面页只是一张整图的，进入点击区域必须覆盖整个封面容器，并随舞台缩放；不得根据图片中按钮的位置猜测或设置局部热区。图片里的按钮仅作视觉引导。完整点击结束后进入一次，隔离本次手势，避免误触第一题。</p><p>用户明确另定入口时遵循其要求；有选关、输入控件的开场页不套用全屏遮罩。修改和修复仅处理本轮涉及的封面入口，不批量更改旧课件。</p></div><table class="overview"><thead><tr><th>环节</th><th>本轮职责</th><th>对比</th></tr></thead><tbody>${DATA.files.map(f=>`<tr><td><button data-file="${f.key}">${f.order}. ${esc(f.title)}</button></td><td>${esc(f.changed?f.changes[0].title:f.unchangedReason)}</td><td><button data-file="${f.key}">${f.changed?'原文 → 本轮完整候选':'原文保留'}</button></td></tr>`).join('')}</tbody></table><div class="issue"><h3>T15：局部热区与图内按钮错位</h3><p>1920×1080 舞台中，点击层仅400×150，位于left760/top650；JS只在该层pointerdown进入。在线CSS、JS和图片已核对。这里是源码与素材证据，尚未对修订后效果做复测。</p><p>${caseHtml('T15')} · <a href="https://box.xdf.cn/kpm/2ef71583dc294b44b72dd6724bb21430" target="_blank" rel="noopener">生产会话 2ef71583dc294b44b72dd6724bb21430 ↗</a></p><p>HTML snapshotId：779d0bba96464430959202bbc5613dbe</p></div>${devGuide()}`}
