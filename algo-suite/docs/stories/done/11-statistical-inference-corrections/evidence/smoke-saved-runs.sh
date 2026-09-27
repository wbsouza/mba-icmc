#!/usr/bin/env bash
# Reanalyze saved LEAN runs on disposable copies; never write into original runs.
set -euo pipefail
repo=$(git rev-parse --show-toplevel)
suite="$repo/algo-suite"
evidence=$(cd "$(dirname "$0")" && pwd)
pilot="$suite/data/training/2026-09-26-six-month-pilot/data"
work=$(mktemp -d /tmp/story11-real-smoke.XXXXXX)
trap 'rm -rf "$work"' EXIT
cd "$suite"
ALGO_DATA_ROOT="$suite/data" uv run algo-analyze inference-inventory > "$evidence/local-inventory.json" 2> "$evidence/local-inventory.stderr.txt"
ALGO_DATA_ROOT="$pilot" uv run algo-analyze inference-inventory > "$evidence/pilot-inventory.json" 2> "$evidence/pilot-inventory.stderr.txt"
uv run python - "$pilot" "$work" "$evidence" <<'PY'
import hashlib
import json
import shutil
import sys
from pathlib import Path

pilot, work, evidence = map(Path, sys.argv[1:])
records = []
for family in ('baseline', 'hybrid'):
    originals = sorted((pilot / 'runs' / family).glob('*/run.json'))
    assert len(originals) == 1, 'Choose and register a unique saved pilot run'
    original = originals[0].parent
    destination = work / 'runs' / family
    destination.mkdir(parents=True)
    hashes = {}
    for name in ('run.json', 'main.json', 'metrics.json'):
        source = original / name
        hashes[name] = hashlib.sha256(source.read_bytes()).hexdigest()
        shutil.copy2(source, destination / name)
    contract = dict(source='main.json', frequency='calendar-day', timezone='UTC',
                    annualization=365, risk_free_daily=0, symbol='EURUSD',
                    start='2015-09-01', end='2015-10-01',
                    costs='Recorded engine equity; no fills and no recorded trading fees. '
                          'Execution-cost economics remain unvalidated.')
    (destination / 'inference-inputs.json').write_text(json.dumps(contract, indent=2)+'\n')
    records.append(dict(run=str(original.relative_to(pilot)), hashes=hashes,
                        metadata_provenance='Reconstructed only on disposable copy from '
                        'saved run dates and zero-fill equity; no selection history invented',
                        contract=contract))
(evidence / 'pilot-sources.json').write_text(json.dumps(records, indent=2)+'\n')
PY
for family in baseline hybrid; do
    ALGO_DATA_ROOT="$work" uv run algo-analyze metrics --run "$family" > "$evidence/pilot-$family-v2.json" 2> "$evidence/pilot-$family.stderr.txt"
done
ALGO_DATA_ROOT="$work" uv run algo-analyze significance --runs baseline --runs hybrid --block-length 3 --block-length 1 --block-rule 'L=3 is the largest length satisfying the ten-block guard for 30 days; L=1 is the IID comparator; no length is size-calibrated at this n (method-design extensions); integration diagnostic only, not trading inference' --resamples 499 --seed 20260927 > "$evidence/pilot-paired-v2.json" 2> "$evidence/pilot-paired.stderr.txt"
uv run python - "$pilot" "$evidence" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

pilot, evidence = map(Path, sys.argv[1:])
for record in json.loads((evidence / 'pilot-sources.json').read_text()):
    for name, digest in record['hashes'].items():
        assert hashlib.sha256((pilot / record['run'] / name).read_bytes()).hexdigest() == digest
for family in ('baseline', 'hybrid'):
    result = json.loads((evidence / f'pilot-{family}-v2.json').read_text())
    assert result['schema_version'] == 2 and result['status'] == 'unavailable'
    assert result['deflated_sharpe_probability'] is None
    assert 'zero return variance' in result['reason']
    assert result['portfolio']['n_observations'] == 30
paired = json.loads((evidence / 'pilot-paired-v2.json').read_text())
assert paired['primary']['block_length'] == 3 and paired['primary']['status'] == 'unavailable'
assert 'degenerate' in paired['primary']['reason']
assert paired['sensitivity'][0]['block_length'] == 1
assert paired['sensitivity'][0]['status'] == 'unavailable'
assert 'degenerate' in paired['sensitivity'][0]['reason']
assert paired['run_a'] == 'baseline' and paired['run_b'] == 'hybrid'
print('PASS: two saved LEAN runs, 30 actual daily returns, unavailable flat-equity inference; original hashes unchanged')
PY
