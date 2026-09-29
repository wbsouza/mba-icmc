# Lessons learned — Story 07 (monografia document QA)

§1 was blocked on Spec 06 landing, and Spec 06 landed with a much larger
Chapter 4 than originally scoped (two whole new sections, five new tables)
under a deadline that moved up by four months. The build-hygiene half of
this story (§2) turned out to be the resilient part — it's a mechanical,
repeatable check (`make verify`) that got run informally, correctly, every
time a chapter changed, without needing its own dedicated story pass. The
content-consistency review (§1) is the part that actually needs a human
reading two specific paragraphs against the final text, which a mechanical
check can't substitute for — that's the real remaining gap, not a checklist
definition exercise.
