# Runtime resource intervention after the frozen results snapshot

Clock confirmation: **2026-09-28 00:49:16 UTC**. This addendum follows the
[00:36 results snapshot](intermediate-results-20260928T003601Z.md) and does not
replace its process or completion observations.

The user reported authorizing the main owner to raise the two active native
LEAN containers from two to four CPUs each, with no algorithm or input
change. This documentation task performed only a read-only `docker inspect`.
It independently confirmed the following current settings:

| Container | State | NanoCpus | CPU quota/period | Memory limit |
| --- | --- | --- | --- | --- |
| boring_panini | running | 4,000,000,000 (4 CPUs) | 0 / 0 | 6,442,450,944 bytes (6 GiB) |
| adoring_vaughan | running | 4,000,000,000 (4 CPUs) | 0 / 0 | 6,442,450,944 bytes (6 GiB) |

The exact intervention instant and prior two-CPU allocation are reported by
the main owner, not reconstructed from Docker history. The current inspection
does not identify a final run manifest or prove a performance outcome. No
container-to-run mapping is invented here. Runtime limits were changed during
active execution; **do not claim uniform CPU allocation across all old runs**
or treat elapsed-time comparisons as controlled benchmarks.

The host specification was reported by the user: Ryzen 5900X, 12 cores and
24 threads, 121.4 GiB RAM (approximately 60 GiB available), RTX 3090 with
24 GiB VRAM. Those host values were not independently measured in this task.

The user also reported a new runner budget of six maximum slots, four CPUs
and eight GiB per container, and two workers. This is a planned/new-run
allocation, not the settings observed above and not a retroactive description
of predecessor runs. The GPU capability probe assigned to Mendel is pending;
no research backend change or GPU-accelerated result is claimed.

Read-only verification command:

```sh
docker inspect --format '{{.Name}} status={{.State.Status}} nano_cpus={{.HostConfig.NanoCpus}} cpu_quota={{.HostConfig.CpuQuota}} cpu_period={{.HostConfig.CpuPeriod}} memory_bytes={{.HostConfig.Memory}}' boring_panini adoring_vaughan
```
