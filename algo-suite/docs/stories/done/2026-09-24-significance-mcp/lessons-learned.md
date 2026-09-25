# Lessons learned — Spec 05b: algo-analyze Monte-Carlo permutation test

**Sourced from the parallel Spec 05 analysis lanes opened as stacked PRs**
(05b significance, 05c ablation, 05d figures).

**Keep analysis lanes importable before CLI wiring.** This story deliberately
landed `mcp_test` as a small isolated function with BDD coverage and no command
surface. That made it possible to review the statistical contract independently
from Spec 05e's integration work, and let later lanes stack on the same package
scaffold without mixing command-line concerns into every PR.

**Fail fast on an under-sampled Monte-Carlo run.** A tiny permutation count can
return a number, but that number is easy to over-read. Enforcing a clear minimum
keeps Chapter 4 significance values reproducible and harder to misuse.

**Stacked PRs are the right shape for parallel lanes that share a new package.**
05b creates the `algo-analyze` scaffold, so 05c and 05d should target the branch
before them. Otherwise every PR would show the same package bootstrap files and
reviewers would have to mentally subtract duplicated context.
