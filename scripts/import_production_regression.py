#!/usr/bin/env python3
"""Append an actual production run while preserving all historical artifacts."""
import argparse
import copy
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--summary', required=True)
p.add_argument('--seed', required=True)
p.add_argument('--version-id', required=True)
p.add_argument('--label', required=True)
a = p.parse_args()
summary_path = Path(a.summary)
summary = json.loads(summary_path.read_text())
assert summary['kpmBaseUrl'] == 'https://box.xdf.cn'
assert summary['requestedCount'] == 28
seed_path = Path(a.seed)
seed = json.loads(seed_path.read_text())
before = copy.deepcopy(seed)
assert summary['testSetId'] == seed['testSetId']
results = {r['id']: r for r in summary['results']}
assert len(results) == len(summary['results']), 'Duplicate case results'
automatic = [c for c in seed['cases'] if c.get('generationMode') != 'manual']
assert len(automatic) == 28
assert set(results) <= {c['id'] for c in automatic}
for c in automatic:
    r = results.get(c['id'])
    if not r:
        continue
    assert r['prompt'] == c['requirement'], 'Frozen prompt changed'
    v = {k: r.get(k, '') for k in ('conversationId', 'fileUrl', 'pushUrl',
        'fileName', 'snapshotId', 'startedAt', 'finishedAt', 'error')}
    v.update(id=a.version_id, label=a.label, group='固定测试集',
        taskId=f"fixed_{c['id']}_{a.version_id}", status=r['status'],
        prompt=c['requirement'], promptType='raw-user-requirement',
        environment=summary['kpmBaseUrl'], generateMode=summary['generateMode'],
        generationMethod=summary['generationMethod'], published=False, evaluated=False)
    ef = summary_path.parent / c['id'] / 'events.jsonl'
    if ef.exists():
        events = [json.loads(line) for line in ef.read_text().splitlines() if line.strip()]
        v['messageIds'] = sorted({e['messageId'] for e in events if e.get('messageId')})
        ids = [e['messageId'] for e in events if e.get('eventType') == 2 and e.get('messageId')]
        v['generationMessageId'] = ids[-1] if ids else ''
    cf = summary_path.parent / c['id'] / 'package-check.json'
    if cf.exists():
        ch = json.loads(cf.read_text())
        v['htmlSha256'] = ch['htmlSha256']
        v['verification'] = {
            'scriptSyntax': '发现问题' if ch['syntaxErrors'] else '通过',
            'literalResourceReferences': '待核实' if ch['missingLiteralReferences'] else '通过',
            'audioDecode': '发现问题' if ch['audioDecodeErrors'] else '通过' if ch['audioFiles'] else '无音频文件',
            'audioFileCount': ch['audioFiles'], 'scope': ch['scope'],
            'interaction': '待验证', 'audioListening': '待验证', 'visualStatus': '待验证',
            'reviewNote': '包内基础检查完成；真实画面、交互、听感与知识逻辑继续评审，不将生成成功等同于质量通过。'}
    versions = c.setdefault('productionVersions', [copy.deepcopy(c['baseline'])] if c.get('baseline') else [])
    existing = next((x for x in versions if x['id'] == a.version_id), None)
    if existing:
        # Incremental checks must not erase scores or independent review evidence.
        for key in ('evaluation',):
            if key in existing: v[key] = existing[key]
        v['verification'] = {**existing.get('verification', {}), **v.get('verification', {})}
    c['productionVersions'] = [x for x in versions if x['id'] != a.version_id] + [v]

for old, new in zip(before['cases'], seed['cases']):
    if old.get('generationMode') == 'manual':
        assert old == new, 'Manual case changed'
        continue
    for key in old:
        if key != 'productionVersions': assert old[key] == new[key], f'Historical field changed: {key}'
    old_history = [v for v in old.get('productionVersions', []) if v['id'] != a.version_id]
    new_history = [v for v in new.get('productionVersions', []) if v['id'] != a.version_id]
    assert old_history == new_history, 'Historical production results changed'

previous = seed.get('currentRun')
if previous and previous['id'] != a.version_id:
    history = seed.setdefault('runHistory', [])
    if not any(r['id'] == previous['id'] for r in history): history.append(previous)
seed['generatedAt'] = summary['updatedAt']
seed['currentRun'] = {
    'id': a.version_id, 'label': a.label, 'environment': summary['kpmBaseUrl'],
    'generateMode': summary['generateMode'], 'updatedAt': summary['updatedAt'],
    **{k: summary[k] for k in ('successCount','failureCount','pendingCount','requestsSha256')},
    'automaticCaseCount': 28, 'manualCaseCount': 2, 'comparisonType': 'production-latest',
    'note': '本轮使用线上最新提示词，按固定28条原始需求、标准模式（smart）生成首版。线上栏默认显示最新结果；下拉可切回0813线上版本。测试环境历史结果另行保留。',
    'boundary': '保留全部历史课件、版本ID及评分关联；不自动修复或迭代。2条录音/口语用例仍待手动生成。',
    'verificationNote': '生成成功不等于质量通过。人工与AI评审独立记录；未完成的画面、操作、试听检查标为待验证。',
}
checks = [v['verification'] for c in automatic for v in c.get('productionVersions', []) if v['id'] == a.version_id and v.get('verification')]
if checks:
    seed['currentRun']['basicCheckNote'] = f"已检查 {len(checks)}/28 份课件包；JS语法发现问题 {sum(x['scriptSyntax'] != '通过' for x in checks)} 份，明确资源路径待核实 {sum(x['literalResourceReferences'] != '通过' for x in checks)} 份。"
seed_path.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'imported':len(results),'historicalPreserved':True,'manualPreserved':True},ensure_ascii=False))
