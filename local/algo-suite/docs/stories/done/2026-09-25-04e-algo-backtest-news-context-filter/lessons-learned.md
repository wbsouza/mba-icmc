# Lessons learned — Spec 04e: news-context filter F4

**Check that the external data exists before building against it, and let the result decide
the design.** The pre-start check found the two halves in different states. Event features
were real and buildable: `algo-score events --kind gdelt` produced 44640 rows for 2020-01.
Per-symbol sentiment was not: a full month would cost about 500 GB and about 90 hours at the
`gdelt_ngrams` adapter's throughput (TD-48). So F4 treats the event Parquet as a mandatory
input that fails fast when missing, and treats sentiment as best-effort, ABSTAINing when it is
absent. Nothing was built against an invented fixture.

**At a zero threshold, a strict `<` guard doesn't reject zero.** `abs(polarity) < threshold`
is False when both are `0.0`, so neutral sentiment fell through to SELL. A scenario had
recorded that behavior as intended. It was fixed after review (`e04de19`), and polarity `0.0`
now always ABSTAINs. When adding boundary scenarios, check what the zero-signal case *should*
do, not only which side of the threshold it lands on.

**Mutation survivors:** 144/148 were killed. The last 4 are message-text canaries (TD-49), the
same class as TD-34/36/40, left for the project-wide decision on exact-string assertions.
