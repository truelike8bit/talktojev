# From Hobbyist Tinkerer to Research Contributor

*A practical, friendly guide for navigating your local Talk to Jev fork, testing hypotheses, and preparing your first open-source PR or research writeup.*

---

## 1. Welcoming the Hobbyist Perspective

You do not need to work at an AI lab or have a PhD in machine learning to make valuable contributions to `talktojev`. 

In fact, the creator of this project (Lucian Lazar) explicitly notes in the `README.md`:
> *"This repository is one implementation of that idea, written quickly and iteratively. It is not a one-to-one rendering of the paper, and it is not tidy. The paper is the idea; the code is a proof that it runs."*

Because Jev is built entirely on discrete classification (`decide()`), improving it does not require training massive neural nets or fine-tuning weights with clusters of GPUs. It requires **keen observation, linguistic sensitivity, clever prompt framing, and empirical discipline**—skills where a curious, thoughtful human often outperforms automated pipelines.

Your early-access TypeSafe API key and your willingness to converse deeply with Jev (as shown in `brunch_with_jev.md`) make you uniquely positioned to discover behavioral edges that automated benchmarks miss.

---

## 2. Managing Your Local Git Fork

When you are experimenting locally, keeping your repository clean will make your life vastly easier when you want to compare changes or eventually contribute back.

### The Golden Rule: Branch for Every Idea
Never make experimental changes directly on `main` or your tracking branch. Always create a lightweight branch for each hypothesis:

```bash
# Keep your baseline clean
git checkout main

# Create a branch for a specific test or feature
git checkout -b exp/performance-move
```

### Commit Messages That Tell a Story
When you commit, write the *why*, not just the *what*:
```bash
git commit -m "feat(moves): add 'perform' dialogue move to handle songs and jokes

When users asked Jev to sing or tell a joke, it previously selected 'answer'
and repeated meta-commitments ('i can sing for you') without producing content.
Adding 'perform' gives the classifier an explicit choice for artistic execution."
```

---

## 3. The 4-Step Empirical Experiment Loop

To make real progress and build confidence in your modifications, follow this 4-step loop:

```
┌────────────────┐      ┌────────────────┐
│ 1. Formulate   │ ───> │ 2. Implement   │
│   Hypothesis   │      │   Minimal Diff │
└────────────────┘      └────────────────┘
        ▲                       │
        │                       ▼
┌────────────────┐      ┌────────────────┐
│ 4. Evaluate &  │ <─── │ 3. Benchmark   │
│   Compare      │      │   Run Scenarios│
└────────────────┘      └────────────────┘
```

1. **Formulate Hypothesis:** *"If I add a decay factor to `mind.feel`, Jev will stop repeating 'grateful for you' 5 times in a row."*
2. **Implement Minimal Diff:** Touch as few lines as possible in `server.py` or `mind.py`.
3. **Benchmark Run Scenarios:** Run `python scripts/run_scenario.py scenarios/brunch.json`.
4. **Evaluate & Compare:** Compare the new report against your baseline run (`reports/baseline.md`). Did the conversation improve? Did latency or repetition get worse?

---

## 4. Anatomy of a World-Class First Pull Request (PR)

When you're ready to share your improvement with the upstream repository, follow this blueprint. Maintainers adore PRs structured like this:

### PR Title
> `feat: add performative move to eliminate meta-repetition in creative requests`

### PR Description Template
```markdown
### Summary of Problem
When prompted with creative requests ("sing me a song", "tell me a joke"), Jev 
classified the intent as `request`, but the available moves only allowed `answer` 
or `reason`. This caused Jev to loop on meta-statements ("i will sing a song for you, 
a song for you") rather than delivering content.

### Proposed Change
- Added `perform` to `MOVES` dictionary in `server.py`.
- Updated prompt criteria to distinguish between discussing an action vs performing it.

### Empirical Evidence (Before vs After)
Tested across `scenarios/humor_and_performance.json` (4 turns):

| Metric | Before (Commit 43463a9) | After (This PR) | Delta |
|---|---|---|---|
| Repetition Rate | 0.28 (degenerate loops) | 0.08 (clean) | -71% |
| Critique Score | 4.2 / 6 | 5.6 / 6 | +1.4 |
| Latency | 11.2s | 9.4s | -1.8s |

### Example Transcript Comparison
- **Prompt:** *"could you sing me a little song about our brunch together?"*
  - **Before:** *"well i can sing about our brunch together for you just now. because i am grateful for you. a song for you. i will sing a little song for you."*
  - **After:** *"sun on the table and bread in the pan, sweet coffee warm in my hand."*
```

---

## 5. Contributing to Research Papers and Notes

The paper *Generation is Classification* (Lazar, 2026) is an active, living body of work. Research in this paradigm progresses through empirical findings.

### How You Can Contribute Without Being an "Academic":
1. **Report Behavioral Anomalies:** Open an issue titled `[Observation] Emotional Attractor Basins across Multi-Turn Dialogues` and attach your `brunch_with_jev.md` report.
2. **Share Benchmark Datasets:** Submit new scenarios (e.g. `scenarios/philosophical.json`) to expand the evaluation suite.
3. **Zenodo & DOI Attribution:** Authors of open-source research code frequently add active community contributors to paper acknowledgments or Zenodo record metadata when code is merged into the public repo.

Every great open-source journey begins with a local fork, a spark of curiosity, and a willingness to test. You have the tools, the framework, and the insight—happy experimenting!
