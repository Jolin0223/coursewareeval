#!/usr/bin/env python3
"""Append a named fixed-suite run without replacing historical versions or ratings."""
import argparse, json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--summary', required=True)
p.add_argument('--seed', required=True)
p.add_argument('--version-id', required=True)
p.add_argument('--label', required=True)
args = p.parse_args()
summary_file = Path(args.summary)
summary = json.loads(summary_file.read_text())
seed_path = Path(args.seed)
seed = json.loads(seed_path.read_text())
assert summary['testSetId'] == seed['testSetId']
results = {r['id']: r for r in summary['results']}
automatic = [c for c in seed['cases'] if c.get('generationMode') != 'manual']
assert len(automatic) == 28
for case in automatic:
    result = results.get(case['id'], {})
    if result: assert result['prompt'] == case['requirement']
    version = {k: result.get(k, '') for k in (
        'conversationId', 'fileUrl', 'pushUrl', 'fileName', 'snapshotId',
        'finishedAt', 'startedAt', 'error')}
    version.update(id=args.version_id, label=args.label, group='固定测试集',
        taskId=f"fixed_{case['id']}_{args.version_id}",
        status=result.get('status', 'pending'), prompt=case['requirement'],
        promptType='raw-user-requirement', environment=summary['kpmBaseUrl'],
        generationMethod=summary['generationMethod'], generateMode=summary['generateMode'],
        published=False, evaluated=False)
    events_file = summary_file.parent / case['id'] / 'events.jsonl'
    if events_file.exists():
        events = [json.loads(line) for line in events_file.read_text().splitlines()]
        version['messageIds'] = sorted({e['messageId'] for e in events if e.get('messageId')})
        generation_messages = [e['messageId'] for e in events if e.get('eventType') == 2 and e.get('messageId')]
        version['generationMessageId'] = generation_messages[-1] if generation_messages else ''
        if events: version['firstSubmittedAt'] = events[0]['at']
    check_file = summary_file.parent / case['id'] / 'package-check.json'
    if check_file.exists(): version['htmlSha256'] = json.loads(check_file.read_text())['htmlSha256']
    case['versions'] = [v for v in case.get('versions', []) if v['id'] != args.version_id] + [version]
seed['generatedAt'] = summary['updatedAt']
seed['currentRun'] = {
    'id': args.version_id, 'label': args.label, 'generateMode': summary['generateMode'],
    'updatedAt': summary['updatedAt'], 'successCount': summary['successCount'],
    'failureCount': summary['failureCount'], 'pendingCount': summary['pendingCount'],
    'automaticCaseCount': 28, 'manualCaseCount': 2,
    'comparisonType': 'historical',
    'note': '线上采用网站已有历史结果；固定集原文不变，标准模式（smart），只生成首版，不自动迭代。2条录音/口语用例待手动生成。',
    'boundary': '本轮验证首次生成；不覆盖生成后的修改链路。历史对照不能单独证明提示词的因果收益，未完成实测的课件不计作质量通过。',
    'requestsSha256': summary['requestsSha256'],
}
temp = seed_path.with_suffix('.tmp')
temp.write_text(json.dumps(seed, ensure_ascii=False, indent=2)+'\n')
temp.replace(seed_path)
print(f"Imported {args.label}: success={summary['successCount']}, failed={summary['failureCount']}, pending={summary['pendingCount']}; historical and manual cases preserved")
