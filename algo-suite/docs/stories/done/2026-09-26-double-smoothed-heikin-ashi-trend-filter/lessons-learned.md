# Lessons learned — 04k

The spec's default integration location was already outdated: both strategies
had moved into a shared ChainAlgorithm. Adding the selector there kept baseline
and hybrid consistent and made the new strategy an inherited config plus a
registry entry; no algorithm or model copy was needed.

Forex data are QuoteBars, while the reference plan specifically calls for
TradeBar consolidation. Reading LEAN's midpoint OHLC and constructing TradeBars
kept the requested native consolidator without discarding high/low information.
Scanning at the delivered bar's end time exposes a just-closed bucket without
waiting for a future bar. A native fixture with asymmetric bid/ask candles
proved that midpoint selection matters to the resulting direction.

A generic Python composition alone would not satisfy the user's subsequent
request to follow QuantConnect's custom-indicator standard. The final class
subclasses PythonIndicator and explicitly handles current, event publication,
samples, readiness and reset for manual updates. Tests against the actual pinned
runtime proved this interface, rather than relying on Python mocks of CLR types.

The pinned container lacks coverage.py. Native stdlib tracing plus host coverage's
executable-line universe provided measured line coverage without installing a new
runtime dependency. Mutation testing had to copy the entire imported package so
the container runner mounted the mutated code, not the editable production tree.
A fixed pytest base directory was also necessary: rapid mutation runs cleaned up
the ordinary pytest temporary directory containing the first coverage trace.

The first five-day EMA run timed out near its end at the default 600 seconds;
a retry with an explicit 1200-second limit completed. Failed/incomplete artifacts
were rejected by QA. Next time, choose an adequate explicit limit before running
paired F7 backtests, and capture the resolved strategy config from the first run.
The initial candidate ran before the config sidecar existed, so its first evidence
was labeled as a QA snapshot. Review prompted rerunning both arms from the same
clean code commit, requiring and hashing engine-written atomic sidecars for both.

Changing perception while retaining the original EMA-trained model is a valid
frozen-model input ablation, but not a retrained-model evaluation. Making that
scope explicit avoided quietly introducing a second training implementation of
Wilder/LWMA or claiming train/serve parity that was never demonstrated for it.
The tiny observed return difference is only a smoke result.

Existing workspace debt should remain visible. The package gate passed, while
root make check still reports TD-55's 52 unrelated BigQuery lint errors. The ready
TD-60 removal of obsolete direct joblib metadata was small and was completed.

Review follow-up also exposed a concurrent documentation branch, PR #43. Merging
its ancestry into this PR and resolving the directory move preserves TD-61 and
prevents a later merge from resurrecting the planned story. Its training-parity
proposal is now explicitly TD-62, a prerequisite for a DSHA-retrained comparison;
the implemented frozen-model ablation does not pretend to satisfy that work.
Resolved TD-60 was removed from the active ledger per its delete-not-archive rule.

Native acceptance now transports measured JSON into host BDD assertions. A log
marker can no longer conceal a missing assertion in the probe. The full perception
gauntlet is one Make target, with automatic coverage merging; its offline
architecture check also runs in the normal package gate. The atomic config artifact,
CLI diagnostic name, hybrid EMA default, and QA provenance/warm-up asymmetry have
host scenarios. Real DSHA output is additionally passed through F1 to verify the
conflict veto and the deliberately mixed DSHA-direction/EMA-strength trend score.
