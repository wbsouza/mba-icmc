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
The candidate ran before the new config sidecar existed, so its config evidence is
honestly labeled as a QA snapshot; actual model equality comes from engine logs.

Changing perception while retaining the original EMA-trained model is a valid
frozen-model input ablation, but not a retrained-model evaluation. Making that
scope explicit avoided quietly introducing a second training implementation of
Wilder/LWMA or claiming train/serve parity that was never demonstrated for it.
The tiny observed return difference is only a smoke result.

Existing workspace debt should remain visible. The package gate passed, while
root make check still reports TD-55's 52 unrelated BigQuery lint errors. The ready
TD-60 removal of obsolete direct joblib metadata was small and was completed.
