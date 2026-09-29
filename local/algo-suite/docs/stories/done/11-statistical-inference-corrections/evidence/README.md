# Independent statistical validation

The registered finite simulation passed all four primary gates. The observed
null rejection rates were 6% and 7%; these meet the prespecified Monte Carlo
bound of 8.775%, but do not establish exact 5% size for other processes.

| AR(1) phi | Daily mean effect | Primary L=20 rejection rate | Wilson 95% interval |
| --- | --- | --- | --- |
| 0.0 | 0.0 | 6.00% | 3.83%–9.28% |
| 0.0 | 0.001 | 94.00% | 90.72%–96.17% |
| 0.0 | 0.002 | 100.00% | 98.74%–100.00% |
| 0.6 | 0.0 | 7.00% | 4.62%–10.46% |
| 0.6 | 0.001 | 49.67% | 44.05%–55.29% |
| 0.6 | 0.002 | 94.00% | 90.72%–96.17% |

All 24 combinations, including block-length sensitivities and the IID comparator,
are in `simulation-results.json`. Under phi=0.6, the IID comparator rejected
31% of true nulls. The dependence-aware primary method rejected 7%. No p-value
decision disagreed with whether the corresponding interval excluded zero in
the 7,200 simulated comparisons. These 24 rows reproduced exactly when the
script was rerun on September 27 after the review follow-up.

## Registered extensions at thesis-scale windows (both failed, both reported)

Two block-length rules were registered in `../method-design.md` before running,
each with its own scenario indices. Null rejection at the rule length, 300
replications, bound 8.775%:

| n | phi | `floor(n^(1/3))` | Wilson 95% | `floor(n/10)` | Wilson 95% | gate |
| --- | --- | --- | --- | --- | --- | --- |
| 90 | 0.0 | L=4: 5.67% | 3.6%–8.9% | L=9: 10.00% | 7.1%–13.9% | pass / **fail** |
| 90 | 0.6 | L=4: 13.67% | 10.2%–18.0% | L=9: 14.00% | 10.5%–18.4% | **fail** / **fail** |
| 180 | 0.0 | L=5: 6.67% | 4.4%–10.1% | L=18: 9.33% | 6.5%–13.2% | pass / **fail** |
| 180 | 0.6 | L=5: 10.67% | 7.7%–14.7% | L=18: 9.33% | 6.5%–13.2% | **fail** / **fail** |

Power at effect 0.002 (reported, not gated): 51%/58% at n=90 and 75%/78% at
n=180 under phi=0; 31%/30% and 40%/40% under phi=0.6. The IID comparator (L=1)
rejected 31–35% of true nulls under phi=0.6 at both n. All 21,600 decisions
were coherent between p-value and interval.

Interpretation: short blocks under-cover AR(1) dependence (an analytic bias
expression in `../method-design.md` predicts the observed sizes within one
Wilson interval), and the maximal length under the ten-block guard is liberal
even without dependence because ten blocks are too few. No third rule was
tried. Consequence: a 90–180-day window cannot yet support a calibrated
confirmatory paired test with this procedure; see the conclusion in
`../method-design.md` and TD-62.

The six independent DSR/PSR references in `formula-reference.json` use mpmath
at 80 decimal digits and inverse-erf, independently of production NormalDist.
All agree within 1e-12; maximum observed absolute error was 3.56e-15. The sixth
fixture (SR 0.2, T 100, N 10, dispersion 0.1) is the constant asserted in
`deflated_sharpe.feature`.

Reproduce from `algo-suite`:

```sh
uv run --with mpmath==1.3.0 python docs/stories/done/11-statistical-inference-corrections/evidence/validate_inference.py
```

The script fixes seed, scenarios, sample sizes, burn-in, resamples and block
lengths as registered in `../method-design.md`. It writes both JSON artifacts and
exits nonzero because the extension gates failed; that is the recorded outcome,
not a reproduction error. Retain the checked-in originals when comparing a
subsequent implementation.
NumPy version is recorded in the simulation JSON. This is software validation,
not an analysis of the trading experiment or evidence supporting H1.

Reference equations/methods: [Bailey and López de Prado (2014), Eq. 2](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf);
[Politis and Romano (1994)](https://doi.org/10.1080/01621459.1994.10476870).

Verification of this evidence script: Ruff passed; strict mypy passed with
`MYPYPATH=algo-analyze/src` when checking the standalone script from the workspace.

## Saved-run integration and migration inventory

From the repository root, execute `evidence/smoke-saved-runs.sh` via its full story
path. The script inventories seven local saved outputs (including two experiment
subruns) and two September pilot runs. All nine original runs lack the newly
required inference metadata; their original DSR cannot be regenerated honestly
without that metadata and actual selection records. See `local-inventory.json`
and `pilot-inventory.json` for every run and its diagnostic.

The script copies the two successful pilot outputs into a disposable directory,
adds an explicitly reconstructed daily-grid/cost declaration, and retains the
original input hashes in `pilot-sources.json`. Both contain 30 daily returns,
all zero. `pilot-baseline-v2.json` and `pilot-hybrid-v2.json` correctly report
zero-variance DSR as unavailable. `pilot-paired-v2.json` diagnoses degenerate
paired differences at L=3 (the largest length satisfying the ten-block guard
for 30 days) and at the L=1 IID comparator. Neither length is a size-calibrated
inferential setting at this n (see the extensions above); the run exercises
the diagnostics only. `run_a`/`run_b` now record run names, not absolute paths. No trial history is invented. Hash assertions
verify that raw runs remain unchanged. Frozen models are never opened for write.

The files ending `.stderr.txt` capture the exact CLI configuration diagnostics;
temporary absolute paths in outputs identify the disposable copies used.
