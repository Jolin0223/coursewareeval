const STORAGE_KEY = 'coursewareeval.workspace.v1';
const ROUTE_TITLES = {
  overview: '总览',
  style: '画面风格测评',
  template: '一键同款 vs 套用玩法',
  generation: '生成模型测评',
};

const STATUS_LABELS = {
  ready: '可入库',
  issue: '有问题',
  todo: '待补齐',
  reviewed: '已评审',
};

const REASON_TAGS = [
  '玩法骨架保留更好',
  '用户需求适配更好',
  '交互完整度更好',
  '视觉更稳定',
  '内容跑偏',
  '题型被改坏',
  '缺少核心交互',
  '画面/文字异常',
];

const app = {
  route: 'overview',
  styleQuery: '',
  templateQuery: '',
  selectedStyleId: '',
  selectedCaseId: '',
  data: { styles: [], cases: [] },
  state: loadState(),
};

init();

async function init() {
  const [styleSeed, templateSeed] = await Promise.all([
    fetch('./data/style-eval-seed.json').then((res) => res.json()),
    fetch('./data/template-eval-seed.json').then((res) => res.json()),
  ]);
  app.data.styles = styleSeed.styles || [];
  app.data.cases = templateSeed.cases || [];
  app.selectedStyleId = app.data.styles[0]?.id || '';
  app.selectedCaseId = app.data.cases.find((item) => item.userDemand)?.id || app.data.cases[0]?.id || '';
  bindEvents();
  render();
}

function bindEvents() {
  document.querySelector('.nav').addEventListener('click', (event) => {
    const button = event.target.closest('[data-route]');
    if (!button) return;
    app.route = button.dataset.route;
    render();
  });

  document.getElementById('export-state').addEventListener('click', exportState);
  document.getElementById('reset-state').addEventListener('click', () => {
    if (!confirm('确认清空本机补充的截图、分数和结论？')) return;
    localStorage.removeItem(STORAGE_KEY);
    app.state = loadState();
    render();
  });

  document.getElementById('content').addEventListener('input', handleInput);
  document.getElementById('content').addEventListener('change', handleChange);
  document.getElementById('content').addEventListener('click', handleClick);
}

function loadState() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    return {
      artifacts: parsed.artifacts || {},
      styleMeta: parsed.styleMeta || {},
      templateMeta: parsed.templateMeta || {},
    };
  } catch {
    return { artifacts: {}, styleMeta: {}, templateMeta: {} };
  }
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(app.state));
  document.getElementById('storage-state').textContent = '已保存到本机';
}

function artifactKey(type, recordId, variantId) {
  return `${type}:${recordId}:${variantId}`;
}

function render() {
  document.querySelectorAll('.nav-item[data-route]').forEach((item) => {
    item.classList.toggle('active', item.dataset.route === app.route);
  });
  document.getElementById('page-title').textContent = ROUTE_TITLES[app.route] || '总览';
  const content = document.getElementById('content');
  if (app.route === 'style') content.innerHTML = renderStylePage();
  else if (app.route === 'template') content.innerHTML = renderTemplatePage();
  else if (app.route === 'generation') content.innerHTML = renderGenerationPage();
  else content.innerHTML = renderOverview();
}

function renderOverview() {
  const styleVersions = app.data.styles.reduce((sum, item) => sum + item.versions.length, 0);
  const styleReady = app.data.styles.filter((item) => item.finalPrompt).length;
  const casesWithWinner = app.data.cases.filter((item) => item.winner).length;
  const screenshotCount = Object.values(app.state.artifacts).filter((item) => item.screenshot).length;
  const better = app.data.cases.reduce((acc, item) => {
    if (!item.winner) return acc;
    acc[item.winner] = (acc[item.winner] || 0) + 1;
    return acc;
  }, {});

  return `
    <div class="metric-grid">
      ${metric('基础风格', app.data.styles.length, '19 种风格入库候选')}
      ${metric('Prompt 版本', styleVersions, '来自 7月2日测评表')}
      ${metric('已判定案例', casesWithWinner, '一键同款 / 套用玩法')}
      ${metric('已补截图', screenshotCount, '本机工作记录')}
    </div>
    <section class="panel">
      <div class="panel-header">
        <h2 class="panel-title">近期测评重心</h2>
        <span class="status-pill">P0</span>
      </div>
      <div class="generation-board">
        <div class="model-card">
          <div class="model-name">画面风格调整</div>
          <p class="muted">19 种基础风格，按 Prompt 版本追踪问题和最终入库稿。</p>
          <ul class="small-list">
            <li><span>已提取风格</span><strong>${app.data.styles.length}</strong></li>
            <li><span>最终稿字段</span><strong>${styleReady}</strong></li>
          </ul>
        </div>
        <div class="model-card">
          <div class="model-name">套用玩法对比</div>
          <p class="muted">同一素材和用户需求下，对比一键同款与套用玩法的有效性。</p>
          <ul class="small-list">
            <li><span>一键同款胜出</span><strong>${better.same || 0}</strong></li>
            <li><span>套用玩法胜出</span><strong>${better.template || 0}</strong></li>
          </ul>
        </div>
        <div class="model-card">
          <div class="model-name">生成模型测评</div>
          <p class="muted">下一阶段接入 Gemini 3.1 Pro、Gemini 3.5 Flash 等模型测试。</p>
          <ul class="small-list">
            <li><span>模型维度</span><strong>待建</strong></li>
            <li><span>素材链路</span><strong>待建</strong></li>
          </ul>
        </div>
      </div>
    </section>
  `;
}

function metric(label, value, note) {
  return `
    <div class="metric">
      <div class="metric-label">${escapeHtml(label)}</div>
      <div class="metric-value">${value}</div>
      <div class="record-meta">${escapeHtml(note)}</div>
    </div>
  `;
}

function renderStylePage() {
  const styles = filteredStyles();
  const selected = app.data.styles.find((item) => item.id === app.selectedStyleId) || styles[0] || app.data.styles[0];
  if (selected && selected.id !== app.selectedStyleId) app.selectedStyleId = selected.id;

  return `
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">19 种基础风格</h2>
          <div class="muted">按风格维度沉淀每版 Prompt、效果截图、问题和最终入库稿。</div>
        </div>
        <div class="toolbar">
          <input class="search-input" id="style-search" value="${escapeAttr(app.styleQuery)}" placeholder="搜索风格">
        </div>
      </div>
      <div class="layout-two">
        <div class="record-list">
          ${styles.map((item) => renderStyleListCard(item)).join('')}
        </div>
        <div>
          ${selected ? renderStyleDetail(selected) : emptyPanel('暂无风格数据')}
        </div>
      </div>
    </section>
  `;
}

function renderStyleListCard(item) {
  const meta = app.state.styleMeta[item.id] || {};
  const status = meta.status || item.status || 'issue';
  const latest = latestVersion(item);
  return `
    <button class="record-card ${item.id === app.selectedStyleId ? 'active' : ''}" data-action="select-style" data-id="${item.id}">
      <div class="record-title">${escapeHtml(item.displayName)}</div>
      <div class="record-meta">${latest?.label || '无版本'} · ${item.versions.length} 版</div>
      <div class="badge ${status}">${STATUS_LABELS[status] || status}</div>
    </button>
  `;
}

function renderStyleDetail(style) {
  const meta = app.state.styleMeta[style.id] || {};
  const status = meta.status || style.status || 'issue';
  return `
    <div class="detail-head">
      <div>
        <div class="detail-title">${escapeHtml(style.displayName)}</div>
        <div class="muted">来源：7月2日调整画面风格效果测试</div>
      </div>
      <select class="select-input" data-style-meta="${style.id}" data-field="status">
        ${statusOptions(status)}
      </select>
    </div>
    <div class="version-timeline">
      ${style.versions.map((version) => renderVersionCard(style, version)).join('')}
    </div>
    ${style.finalPrompt ? `
      <section class="panel" style="margin-top:12px; box-shadow:none;">
        <div class="panel-header">
          <h3 class="panel-title">最终入库 Prompt</h3>
          <button class="ghost-button" data-action="copy-final-prompt" data-style-id="${style.id}">复制</button>
        </div>
        <div class="prompt-box">${escapeHtml(style.finalPrompt)}</div>
      </section>
    ` : ''}
  `;
}

function renderVersionCard(style, version) {
  const key = artifactKey('style', style.id, version.id);
  const artifact = app.state.artifacts[key] || {};
  const status = artifact.status || version.status || 'issue';
  const score = artifact.score || '';
  const issue = artifact.issue ?? version.issue ?? '';
  return `
    <article class="version-card">
      <div class="card-top">
        <div>
          <div class="card-title">${escapeHtml(version.label)} ${version.finalCandidate ? '· 最终候选' : ''}</div>
          <div class="record-meta">${version.effectUrl ? '已有课件链接' : '未记录课件链接'}</div>
        </div>
        <span class="badge ${status}">${STATUS_LABELS[status] || status}</span>
      </div>
      ${renderArtifactFrame(key, version.effectUrl)}
      <div class="artifact-actions">
        <label class="ghost-button">
          上传截图
          <input class="file-input" type="file" accept="image/*" data-upload="${key}">
        </label>
        ${version.effectUrl ? `<a class="ghost-button" href="${escapeAttr(version.effectUrl)}" target="_blank" rel="noreferrer">打开链接</a>` : ''}
      </div>
      <div class="field-grid">
        <label>状态<br><select class="select-input" data-artifact="${key}" data-field="status">${statusOptions(status)}</select></label>
        <label>分数<br><input class="text-input score-input" data-artifact="${key}" data-field="score" type="number" min="0" max="5" step="0.5" value="${escapeAttr(score)}"></label>
      </div>
      <label>问题记录<br><textarea class="text-area" data-artifact="${key}" data-field="issue">${escapeHtml(issue)}</textarea></label>
      <details>
        <summary>查看 Prompt</summary>
        <div class="prompt-box">${escapeHtml(version.prompt || '未记录 Prompt')}</div>
      </details>
    </article>
  `;
}

function renderTemplatePage() {
  const cases = filteredCases();
  const selected = app.data.cases.find((item) => item.id === app.selectedCaseId) || cases[0] || app.data.cases[0];
  if (selected && selected.id !== app.selectedCaseId) app.selectedCaseId = selected.id;

  return `
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2 class="panel-title">一键同款 vs 套用玩法</h2>
          <div class="muted">每个素材独立比较，一键同款、套用玩法 V1、套用玩法 V2 都作为方案版本。</div>
        </div>
        <div class="toolbar">
          <input class="search-input" id="template-search" value="${escapeAttr(app.templateQuery)}" placeholder="搜索素材或需求">
        </div>
      </div>
      <div class="layout-two">
        <div class="record-list">
          ${cases.map((item) => renderCaseListCard(item)).join('')}
        </div>
        <div>
          ${selected ? renderCaseDetail(selected) : emptyPanel('暂无案例数据')}
        </div>
      </div>
    </section>
  `;
}

function renderCaseListCard(item) {
  const meta = app.state.templateMeta[item.id] || {};
  const winner = meta.winner || item.winner || '';
  return `
    <button class="record-card ${item.id === app.selectedCaseId ? 'active' : ''}" data-action="select-case" data-id="${item.id}">
      <div class="record-title">${escapeHtml(shortId(item.materialId))}</div>
      <div class="record-meta">${escapeHtml(item.userDemand || '未填写用户需求')}</div>
      <div class="badge ${winner ? 'win' : 'todo'}">${winnerLabel(winner) || '待判定'}</div>
    </button>
  `;
}

function renderCaseDetail(item) {
  const meta = app.state.templateMeta[item.id] || {};
  const winner = meta.winner || item.winner || '';
  const reasons = meta.reasons || [];
  return `
    <div class="detail-head">
      <div>
        <div class="detail-title">${escapeHtml(shortId(item.materialId))}</div>
        <div class="muted">${escapeHtml(item.materialId)}</div>
      </div>
      <select class="select-input" data-template-meta="${item.id}" data-field="winner">
        <option value="" ${winner === '' ? 'selected' : ''}>待判定</option>
        <option value="same" ${winner === 'same' ? 'selected' : ''}>一键同款胜出</option>
        <option value="template-v1" ${winner === 'template-v1' ? 'selected' : ''}>套用玩法 V1 胜出</option>
        <option value="template-v2" ${winner === 'template-v2' ? 'selected' : ''}>套用玩法 V2 胜出</option>
        <option value="template" ${winner === 'template' ? 'selected' : ''}>套用玩法整体胜出</option>
      </select>
    </div>
    <section class="panel" style="box-shadow:none; margin-bottom:12px;">
      <div class="panel-title">用户需求</div>
      <p style="margin-top:8px; line-height:1.7;">${escapeHtml(item.userDemand || '未填写')}</p>
    </section>
    <div class="variant-grid">
      ${item.variants.map((variant) => renderVariantCard(item, variant, winner)).join('')}
    </div>
    <section class="panel" style="box-shadow:none; margin-top:12px;">
      <div class="panel-header">
        <h3 class="panel-title">胜出原因</h3>
      </div>
      <div class="reason-cloud">
        ${REASON_TAGS.map((tag) => `<button class="chip-button ${reasons.includes(tag) ? 'active' : ''}" data-action="toggle-reason" data-case-id="${item.id}" data-tag="${escapeAttr(tag)}">${escapeHtml(tag)}</button>`).join('')}
      </div>
      <label style="display:block; margin-top:12px;">结论备注<br><textarea class="text-area" data-template-meta="${item.id}" data-field="note">${escapeHtml(meta.note || '')}</textarea></label>
    </section>
  `;
}

function renderVariantCard(item, variant, winner) {
  const key = artifactKey('template', item.id, variant.id);
  const artifact = app.state.artifacts[key] || {};
  const score = artifact.score || '';
  const issue = artifact.issue || '';
  const isWinner = winner === variant.id || (winner === 'template' && variant.method === 'template');
  return `
    <article class="variant-card">
      <div class="card-top">
        <div>
          <div class="card-title">${escapeHtml(variant.label)}</div>
          <div class="record-meta">${variant.effectUrl ? '已有课件链接' : '未记录课件链接'}</div>
        </div>
        ${isWinner ? '<span class="badge win">胜出</span>' : '<span class="badge todo">对比项</span>'}
      </div>
      ${renderArtifactFrame(key, variant.effectUrl)}
      <div class="artifact-actions">
        <label class="ghost-button">
          上传截图
          <input class="file-input" type="file" accept="image/*" data-upload="${key}">
        </label>
        ${variant.effectUrl ? `<a class="ghost-button" href="${escapeAttr(variant.effectUrl)}" target="_blank" rel="noreferrer">打开链接</a>` : ''}
      </div>
      <label>分数<br><input class="text-input score-input" data-artifact="${key}" data-field="score" type="number" min="0" max="5" step="0.5" value="${escapeAttr(score)}"></label>
      <label>问题记录<br><textarea class="text-area" data-artifact="${key}" data-field="issue">${escapeHtml(issue)}</textarea></label>
    </article>
  `;
}

function renderGenerationPage() {
  const models = [
    ['Gemini 3.1 Pro', '复杂交互、长 Prompt、题型保持能力'],
    ['Gemini 3.5 Flash', '速度、稳定性、成本和可批量测试能力'],
    ['内部课件模型', '和现有生成链路、素材链路、声音/生图模型组合'],
  ];
  return `
    <section class="panel">
      <div class="panel-header">
        <h2 class="panel-title">生成模型测评矩阵</h2>
        <span class="status-pill">第二阶段</span>
      </div>
      <div class="generation-board">
        ${models.map(([name, note]) => `
          <div class="model-card">
            <div class="model-name">${escapeHtml(name)}</div>
            <p class="muted">${escapeHtml(note)}</p>
            <ul class="small-list">
              <li><span>知识准确性</span><strong>-</strong></li>
              <li><span>交互完整性</span><strong>-</strong></li>
              <li><span>视觉质量</span><strong>-</strong></li>
            </ul>
          </div>
        `).join('')}
      </div>
    </section>
  `;
}

function renderArtifactFrame(key, url) {
  const artifact = app.state.artifacts[key] || {};
  if (artifact.screenshot) {
    return `
      <div class="artifact-frame">
        <img src="${artifact.screenshot}" alt="测评截图">
      </div>
    `;
  }
  const [type, , variant = ''] = key.split(':');
  const previewKind = type === 'template' ? variant : 'style';
  const hasLink = Boolean(url);
  return `
    <div class="artifact-frame empty-frame ${previewKind}">
      <div class="mock-courseware">
        <div class="mock-top"></div>
        <div class="mock-board">
          <span></span><span></span><span></span>
        </div>
        <div class="mock-actions"><i></i><i></i><i></i></div>
      </div>
      <div class="artifact-empty">
        <strong>${hasLink ? '已保留私有链接' : '待补效果截图'}</strong>
        <div class="record-meta">${hasLink ? '上传截图后，团队不用登录也能评审' : '先放截图，再记录问题和结论'}</div>
      </div>
    </div>
  `;
}

function handleInput(event) {
  const target = event.target;
  if (target.id === 'style-search') {
    app.styleQuery = target.value;
    render();
    return;
  }
  if (target.id === 'template-search') {
    app.templateQuery = target.value;
    render();
    return;
  }
  if (target.dataset.artifact) {
    updateArtifact(target.dataset.artifact, target.dataset.field, target.value);
    return;
  }
  if (target.dataset.templateMeta) {
    updateTemplateMeta(target.dataset.templateMeta, target.dataset.field, target.value);
    return;
  }
}

function handleChange(event) {
  const target = event.target;
  if (target.dataset.upload) {
    uploadScreenshot(target.dataset.upload, target.files?.[0]);
    return;
  }
  if (target.dataset.artifact) {
    updateArtifact(target.dataset.artifact, target.dataset.field, target.value);
    render();
    return;
  }
  if (target.dataset.styleMeta) {
    updateStyleMeta(target.dataset.styleMeta, target.dataset.field, target.value);
    render();
    return;
  }
  if (target.dataset.templateMeta) {
    updateTemplateMeta(target.dataset.templateMeta, target.dataset.field, target.value);
    render();
  }
}

function handleClick(event) {
  const action = event.target.closest('[data-action]');
  if (!action) return;
  const type = action.dataset.action;
  if (type === 'select-style') {
    app.selectedStyleId = action.dataset.id;
    render();
  } else if (type === 'select-case') {
    app.selectedCaseId = action.dataset.id;
    render();
  } else if (type === 'toggle-reason') {
    toggleReason(action.dataset.caseId, action.dataset.tag);
  } else if (type === 'copy-final-prompt') {
    const style = app.data.styles.find((item) => item.id === action.dataset.styleId);
    navigator.clipboard?.writeText(style?.finalPrompt || '');
    action.textContent = '已复制';
    setTimeout(() => { action.textContent = '复制'; }, 1200);
  }
}

function updateArtifact(key, field, value) {
  app.state.artifacts[key] = { ...(app.state.artifacts[key] || {}), [field]: value };
  saveState();
}

function updateStyleMeta(styleId, field, value) {
  app.state.styleMeta[styleId] = { ...(app.state.styleMeta[styleId] || {}), [field]: value };
  saveState();
}

function updateTemplateMeta(caseId, field, value) {
  app.state.templateMeta[caseId] = { ...(app.state.templateMeta[caseId] || {}), [field]: value };
  saveState();
}

function toggleReason(caseId, tag) {
  const meta = app.state.templateMeta[caseId] || {};
  const current = new Set(meta.reasons || []);
  if (current.has(tag)) current.delete(tag);
  else current.add(tag);
  app.state.templateMeta[caseId] = { ...meta, reasons: [...current] };
  saveState();
  render();
}

async function uploadScreenshot(key, file) {
  if (!file) return;
  const screenshot = await resizeImage(file, 1280, .82);
  updateArtifact(key, 'screenshot', screenshot);
  render();
}

function resizeImage(file, maxWidth, quality) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const image = new Image();
      image.onload = () => {
        const scale = Math.min(1, maxWidth / image.width);
        const canvas = document.createElement('canvas');
        canvas.width = Math.round(image.width * scale);
        canvas.height = Math.round(image.height * scale);
        const ctx = canvas.getContext('2d');
        ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL('image/jpeg', quality));
      };
      image.onerror = reject;
      image.src = reader.result;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function exportState() {
  const blob = new Blob([JSON.stringify({
    exportedAt: new Date().toISOString(),
    state: app.state,
  }, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `coursewareeval-workspace-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

function filteredStyles() {
  const query = app.styleQuery.trim().toLowerCase();
  if (!query) return app.data.styles;
  return app.data.styles.filter((item) => item.displayName.toLowerCase().includes(query));
}

function filteredCases() {
  const query = app.templateQuery.trim().toLowerCase();
  if (!query) return app.data.cases;
  return app.data.cases.filter((item) => `${item.materialId} ${item.userDemand}`.toLowerCase().includes(query));
}

function latestVersion(style) {
  return [...style.versions].reverse().find((item) => item.effectUrl || item.prompt || item.issue);
}

function statusOptions(selected) {
  return Object.entries(STATUS_LABELS).map(([value, label]) => (
    `<option value="${value}" ${selected === value ? 'selected' : ''}>${label}</option>`
  )).join('');
}

function winnerLabel(value) {
  if (value === 'same') return '一键同款胜出';
  if (value === 'template') return '套用玩法胜出';
  if (value === 'template-v1') return '套用玩法 V1 胜出';
  if (value === 'template-v2') return '套用玩法 V2 胜出';
  return '';
}

function shortId(value) {
  if (!value) return '未记录素材ID';
  return `${value.slice(0, 8)}…${value.slice(-4)}`;
}

function emptyPanel(text) {
  return `<div class="panel"><div class="muted">${escapeHtml(text)}</div></div>`;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  }[char]));
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, '&#096;');
}
