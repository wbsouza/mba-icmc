---
name: monograph-writer
description: Revise this repo's monografia/ LaTeX thesis prose (the user's own original content) into natural, strong academic English — eliminating formulaic "AI-sounding" patterns (clichéd word choice, rule-of-three, uniform sentence rhythm, hedge-heavy filler, templated paragraph shape) and stripping any invisible/non-printable Unicode characters from the .tex source. Trigger on "make the monograph sound more human", "review chapter N for AI-isms", "strip invisible characters from the tex files", or any request to edit prose in monografia/chapters, monografia/pre, or monografia/pos for register/style.
---

# monograph-writer

## Scope and non-goals

This skill edits **register and prose quality** of the user's own already-drafted thesis content (`monografia/chapters/*.tex`, `monografia/pre/*.tex`, `monografia/pos/*.tex`). It does not invent claims, results, or citations, and it does not touch content correctness, chapter structure, or `specs.md`/`CLAUDE.md` decisions.

It is **not** a detector-evasion tool. The goal is prose that reads as confident, specific, native academic English on its own merits — the same edits a sharp human advisor would mark up. Do not optimize against any particular AI-detector's scoring function; optimize against the tells below, all of which are independently bad academic writing habits regardless of origin.

Two independent passes: **(1) invisible-character hygiene** (mechanical, script-driven) and **(2) prose-register editing** (judgment-driven, apply the rules below).

## Pass 1 — invisible/non-printable Unicode characters

Some pasted or tool-generated text carries zero-width spaces, bidi-override characters, variation selectors, or Unicode Tags-block codepoints — none of which a human ever intentionally types, and which are a known steganographic-watermark and prompt-injection vector. Strip them unconditionally; this is LaTeX hygiene independent of any style judgment.

```bash
# report only
python3 .claude/skills/monograph-writer/scripts/strip_invisible_chars.py --check monografia/chapters monografia/pre monografia/pos

# remove them (also normalizes non-breaking spaces to regular spaces unless --keep-nbsp)
python3 .claude/skills/monograph-writer/scripts/strip_invisible_chars.py --fix monografia/chapters monografia/pre monografia/pos
```

Run `--check` first on any chapter before editing it, and again after, to confirm no new invisible characters were reintroduced by the edit itself.

## Pass 2 — prose register

Work chapter by chapter (`make check`-sized chunks — a whole `.tex` file at a time). Read the full file first, edit with the LaTeX-aware Edit tool (never regex-mangle `\cite{}`, `\ref{}`, math, or environment blocks), then re-read your own diff once before moving to the next section. Never touch citation keys, numeric results, or technical terms — flag anything that looks *factually* off (a citation that doesn't seem to support the claim, a nominalization hiding *who* actually did something in a methodology section) rather than silently rewriting it.

No single tell below is individually damning — human academic writing legitimately uses hedges, passive voice, and transition words too. What reads as AI is **density and clustering**: several of these stacked in the same paragraph. Edit for that pattern, not a zero-tolerance word-ban.

### Lexical — words to prefer plainer alternatives for, if used repeatedly

Watch for clustering of: *delve/delving, underscore(s)/underscoring, boast(s)/boasted, meticulous(ly), intricate/intricacies, pivotal, crucial, robust, seamless, cutting-edge, landscape, realm, tapestry, testament, synergy, underpinnings, leverage (as verb), utilize, harness (as verb), streamline, commendable, showcase, surpass, garner, bolstered, foster(ing), enhance, align (with), navigate, embark, vibrant, transcend, vital, profound, nestled, renowned, diverse array.*

None of these is banned outright — each has a legitimate literal use. The tell is reaching for one of these where a plainer, more specific word would say the same thing more precisely (e.g. "robust backtesting" → name the actual property: "leakage-free," "walk-forward validated").

Also watch for systematic avoidance of the plain copula: prefer "X is Y" over "X serves as / stands as / functions as / represents Y" when there's no reason for the fancier verb.

Prefer stating a relationship directly over vague connective hedges: not "associated with," "in connection with" — say what the actual relationship is.

### Phrasal / cliché — cut on sight

- "it is important to note that," "it's worth noting," "needless to say"
- "plays a pivotal/crucial role in," "a testament to," "navigating the complexities of," "unlock the potential of"
- "in today's ever-evolving/fast-paced landscape"
- "in summary," "in conclusion," "at the end of the day" as paragraph/section openers-closers used reflexively rather than because a real summary is needed
- "revolutionize the way," "groundbreaking," "game-changer" — unless the claim is actually that strong and cited
- Manufactured contrast: "not just X, but Y," "it's not X, it's Y" where no reader ever thought X in the first place
- Formal connectors (Furthermore, Moreover, Additionally, Hence, Consequently, Nevertheless, Accordingly) opening paragraph after paragraph — vary or cut; most of the time no connector, or a plain "But"/"So"/"And," reads more natural

### Structural / rhetorical

- **Break the rule of three.** If every list/enumeration in a section has exactly three items, that's a tell — vary to two, four, or a single well-chosen example.
- **Vary paragraph shape.** Don't let every paragraph run topic-sentence → three generic supports → restatement. Let some paragraphs be two sentences; let some run long and argumentative.
- **Cut section self-narration.** Delete "In this section, we will discuss...", "Let us examine...", "We will explore..." — just do the thing; a thesis section doesn't need to announce itself to the reader (a one-line chapter-opening roadmap is fine and conventional in Brazilian/European thesis style — the tell is doing this at *every* subsection).
- **Cut formulaic closings that just restate the opening**, and generic "Challenges and Future Work" boilerplate not actually grounded in this thesis's specific results.
- **De-listify.** Where continuous argumentative prose is the academic convention (Fundamentação Teórica, Metodologia discussion), don't convert it into bullet points or bolded-term fragments unless the content is genuinely enumerable (e.g. a literal list of hyperparameters).
- **Vary sentence length and rhythm (burstiness).** A run of same-length, same-shape sentences reads flat. Mix a short direct sentence next to a longer subordinate-clause one.
- **Kill false balance.** "On the one hand... on the other hand..." without ever landing on a stance is a tell — this thesis should take positions (with appropriate scientific hedging where the evidence genuinely is mixed, not as a reflex).
- **Vague mass attribution.** "industry reports," "several sources," "observers note" — replace with the actual specific source or citation, or cut the claim.
- **Don't inflate significance.** "marks a pivotal moment," "reflects a broader shift" — earn strong claims with the actual data/citation or drop the framing.

### Academic-specific — apply with extra care, these interact with correctness

- **Nominalization / passive-voice overuse hiding agency.** "The implementation of the backtest was undertaken" → "We implemented the backtest" (or the appropriate agent). Methodology sections especially: a reader should always be able to tell *who/what system* did each step.
- **Narrow hedge-word range.** AI-generated academic text leans almost entirely on "may" for hedging and rarely uses confident boosters. Human academic register varies hedges (*may, might, could, appears to, is likely to*) and uses boosters (*clearly, indeed, in fact*) where the evidence actually supports confidence — don't hedge findings that are directly supported by the data in Chapter 4.
- **Citation specificity — check, don't just restyle.** Any citation that (a) is suspiciously generic for the specific claim next to it, (b) cites a review/survey where a primary source would be expected, or (c) can't be found or doesn't obviously support the claim on inspection, gets flagged to the user rather than silently kept or removed. Never invent or "fix" a citation yourself.
- **Methodology specificity.** Flag (don't silently rewrite) any methodology sentence vague enough that a reader couldn't replicate the step — this is both an AI-writing tell and an actual thesis-quality issue per this repo's own standards.

### Evidence & fabrication discipline (borrowed from K-Dense's `scientific-writing` skill)

A register edit must never become a factual edit. These rules apply on top of Pass 2, especially in Chapter 4 (Experimental Evaluation) once real backtest numbers start landing there — that chapter is currently a stub per `monografia/chapters/04-experimental-evaluation.tex`, so most of its eventual content will be freshly drafted, not just polished, and the fabrication risk is highest there.

- **Never strengthen a claim past its evidence while editing for style.** "may improve returns" → "improves returns" is not a register fix, it's an overclaim — a factual edit disguised as a style edit. If a sentence's hedge (*may, appears to, is consistent with*) reflects genuine uncertainty in the underlying result, keep the hedge even if Pass 2's "narrow hedge-word range" rule would otherwise flag it. Only tighten a hedge when the cited number/result in the same chapter actually supports the stronger claim.
- **Don't smooth over an inconsistency — surface it.** If a number, metric, or claim in the prose you're editing doesn't match the same figure elsewhere (a results table, a different chapter's restatement of the same metric, `specs.md`'s stated methodology), flag it to the user rather than silently picking one value to standardize on.
- **Every citation you touch, re-verify it still supports the exact claim next to it** — don't just leave it alone because it was already there; a nearby wording change can shift what the citation is now being asked to support.
- **Missing Chapter 4 content stays marked missing.** Where a section still needs a number, table, or result that doesn't exist yet, keep it as an explicit placeholder (e.g. `\textit{[TODO: Sharpe ratio, EUR/USD baseline — pending backfill + run]}`) rather than smoothing the prose into something that reads like a finished result. Plausible-sounding placeholder numbers are the single worst thing this skill could introduce.
- **Don't invent methodology detail to make a description sound more specific.** If flagging a vague methodology sentence per the rule above, the fix is asking the user for the missing detail or leaving a `[TODO: ...]` marker — never filling it in with a plausible-sounding specific that wasn't actually verified against the code/experiment config.

## Workflow

1. Run Pass 1 (`--check`) on the target file(s); if anything is found, run `--fix` and note the count to the user.
2. Read the full `.tex` file.
3. Edit prose paragraph-by-paragraph against the Pass 2 rules above, using targeted `Edit` calls — never a full-file rewrite, so the diff stays reviewable and `git diff` shows exactly what changed.
4. After editing, run `make pt-scan` (per repo `CLAUDE.md`) if the edit touched any section near non-English text, and re-run Pass 1 `--check` to confirm the edit didn't reintroduce anything.
5. Report to the user: which tells were most common in this chapter, what was changed, and any flagged-not-fixed items (suspect citations, vague methodology, value inconsistencies between sections/chapters, claims that would need strengthening past their current evidence) for them to resolve.
