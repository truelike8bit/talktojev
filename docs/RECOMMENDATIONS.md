# Recommendations for Advancing Talk to Jev

**Document Purpose:** Grounded, prioritized recommendations for improving conversation quality, coherence, and behavioral depth in Jev's discrete-choice classification architecture.  
**Target Audience:** Project researchers, local fork maintainers, and community contributors.  
**Theoretical Foundation:** Lazar (2026), *Generation is Classification*; Bunt et al. (Dialogue Act Theory); WordNet semantic fields; Beam search tree optimization.

---

## 1. Executive Summary of Recommendations

The core thesis of this project is that **generation is classification, repeated, with a memory in between**. Output quality depends strictly on:
1. The **clarity and distinctiveness** of the choices put to the classifier.
2. The **richness of the state** presented before each choice.
3. The **diversity of vocabulary** made accessible during lookahead search.

Based on our empirical testing (`brunch_with_jev.md` and benchmark telemetry), we recommend five high-leverage architectural improvements:

| Priority | Area | Core Intervention | Expected Impact |
|:---:|:---|:---|:---|
| **P1** | **Performative Moves** | Add `deliver_performance` / `punchline` moves | Solves the "meta-repetition trap" when asked to sing or tell jokes |
| **P1** | **Emotional Decay** | Implement state decay in `Mind.feel` across turns | Prevents emotional attractor entrapment (e.g. infinite "grateful" loops) |
| **P2** | **Topical Lexicon Injection** | Inject topical clusters into word options | Elevates vocabulary beyond generic function words |
| **P2** | **Critique Loop Penalty** | Add repetition check to `critique_response` | Automatically rejects and re-plans degenerate looping sentences |
| **P3** | **Length-Normalized Beam Search** | Add length-normalization to sentence completion | Prevents abrupt 1-word replies like *"yes."* when detail is warranted |

---

## 2. Detailed Technical Proposals

### Proposal 1: Escaping the "Meta-Affirmation Trap" for Creative Requests
#### Observed Problem
In Turn 5 of our Brunch test (`brunch_with_jev.md`), the user requested:
> *"could you sing me a little song about our brunch together?"*

Jev responded:
> *"well i can sing about our brunch together for you just now. because i am grateful for you. a song for you. i will sing a little song for you."*

Jev understood the intent as `request (1.0)` but was unable to produce lyrics. Instead, it produced meta-commentary *about* its willingness to sing.
#### Theoretical Root Cause
Dialogue Act Theory (Bunt, 2011; Stolcke et al., 2000) distinguishes between:
- **Commissives:** Committing to an action (*"I will sing"*).
- **Performatives:** Executing the action itself (*"Sunlight on toast, coffee in cup..."*).

Currently, `MOVES` defines `answer`, `reason`, `example`, `admit`, etc. None of these describe *performing an artistic structure*. When the classifier selects `answer`, it chooses words that describe what it can do rather than doing it.
#### Actionable Solution
1. Add a dedicated performative move to `MOVES` in `server.py`:
```python
"perform": "a full sentence delivering the creative line itself — a joke punchline, a line of verse, or a rhyme (not talking about doing it)",
```
2. When `move == "perform"`, supply structural rhythm cues or genre tags into the state description.

---

### Proposal 2: Emotional Attractor Basin Decay
#### Observed Problem
In our multi-turn test, Jev rolled `feel: grateful` on Turn 1. Because the reflection prompt appends previous turns into context (`"i already told them: 'i am grateful for you'"`), Jev stayed locked in `grateful` for all 6 turns, inserting *"because i am grateful for you"* into multiple unrelated questions.
#### Theoretical Root Cause
In dynamical systems, recursive feedback loops create **attractor basins**. In Jev's `reflect()` function, past self-disclosures are fed into the next turn's state. The classifier perceives continuity as consistency, leading to emotional fixation.
#### Actionable Solution
In `mind.py` and `server.py`:
1. **Decay Parameter:** Multiply prior feeling weights by a decay constant (e.g. `decay = 0.65` per turn).
2. **Contrastive Prompting:** In `plan_response`, explicitly prompt:
   > *"You previously felt {last_feel}. Given what they just said, how does your feeling shift now?"*
3. This encourages dynamic emotional journeys (e.g., `curious` -> `amused` -> `thoughtful` -> `reflective`).

---

### Proposal 3: Topical Lexicon Expansion (Semantic Field Priming)
#### Observed Problem
Jev's vocabulary relies heavily on `GRAMMAR_SLOT_WORDS` (~150 function words) and `ECHO_USER_WORDS` (up to 24 words from the user's prompt). Content words come from broad WordNet categories (`object`, `feeling`, `action`). As a result, Jev often struggles to name specific entities unless the user says them first.
#### Actionable Solution
Implement **Topical Lexicon Priming**:
1. When the classifier detects the topic in `plan_response` (e.g. food/dining, technology, cosmology, nature), extract 15-20 related synsets from WordNet or a static thematic lexicon (e.g. `lexicon/dining.json`: *toast, brew, syrup, aroma, crisp*).
2. Inject these candidate words into the `_user_words` slot during `_generate_sentence`.
3. This allows Jev to speak with domain-appropriate texture without altering the classifier architecture.

---

### Proposal 4: Enhancing the Critique Evaluator
#### Current Mechanism
In `critique_response`, Jev evaluates:
- `grammar`: `correct` / `minor` / `broken`
- `relevance`: `relevant` / `partial` / `off_topic`
- `natural`: `natural` / `awkward` / `robotic`
#### Proposed Enhancement
Add an explicit fourth critique criterion:
- `repetition`:
  - `fresh`: *"uses new phrasing and adds new information"*
  - `repetitive`: *"repeats phrases or ideas already spoken in this reply or earlier turns"*
If `repetition == "repetitive"`, subtract 2 points from the score. If score < 4, trigger `_better_of` or sentence re-planning. This automatically suppresses degenerate looping before the visitor ever sees it.

---

### Proposal 5: Length-Normalized Beam Search and Boundary Stopping
#### Observed Problem
When asked *"do you know what coffee tastes like?"*, Jev responded with a solitary word: *"yes."*
#### Theoretical Root Cause
In `_plan_move`, the boundary check checks `reply: complete / more`. For a short sentence, stopping immediately after `"yes."` has high individual word probability, but zero communicative value.
#### Actionable Solution
1. Require a minimum word count (e.g., `MIN_SENTENCE_WORDS = 4`) for communicative moves (`answer`, `reason`, `example`), allowing single-word stops only for explicit binary acknowledgments when followed by an explanatory sentence.
2. In lookahead candidate scoring, apply a small length-normalization factor so longer informative phrases are not penalized by cumulative multiplicative probabilities.

---

## 3. Experimentation Roadmap

| Phase | Milestone | Primary Files Modified | Validation Method |
|:---:|:---|:---|:---|
| **Phase 1** | Implement `perform` move & `repetition` critique | `server.py` | Run `scenarios/humor_and_performance.json` |
| **Phase 2** | Implement emotional decay in `Mind` | `mind.py`, `server.py` | Run `scenarios/brunch.json` (verify emotion transitions) |
| **Phase 3** | Topical Lexicon Priming | `server.py`, `build_vocab.py` | Run full batch evaluation suite |
| **Phase 4** | Benchmark Comparison & Writeup | `bench.py`, `PAPER.md` | Compare A/B runs using `scripts/batch_eval.py compare` |
