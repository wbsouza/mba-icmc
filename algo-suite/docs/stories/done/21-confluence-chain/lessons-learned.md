# Lessons learned — Story 21 (confluence chain)

The engine came together cleanly across three phases with real gates at
every step (mutation-hardened, native LEAN scenarios green) — the harder
problem turned out to be data-layout assumptions, not chain logic. Two
independent fixes for the same root bug (the preflight gate's partition
path pointing at a store nothing actually writes) landed on two different
branches within hours of each other, and one of them was itself wrong in a
subtle way — it fixed the symptom (a fictional path) with a different
fiction (the wrong real store), verified only by a circular self-check that
couldn't have caught the mistake. The version that turned out correct was
proven not by review but by an actual successful cell launch.

What would be done differently: when a "genuine production finding" is
reported, verify it against what the real runtime path actually reads
before trusting the fix — not just against a new unit test the same person
wrote. A test that asserts a function equals itself under different inputs
on both sides cannot catch a wrong assumption shared by both sides.

The registered fourteen-cell study itself was pre-authorized to launch the
moment its gates passed, and its gates did pass — but building and hardening
the engine, alongside three other stories and a monograph, under a
deadline that moved up by four months, took the full session. Running the
actual study is real, valuable, still-open work — see Story 26.
