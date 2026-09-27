# Testing & Evaluation Workflow

Framework for interactive exploration, scenario execution, and batch regression testing.

---

## Generation Pipeline

1. **Perceive (`plan_response`)**: Resolves intent, feelings (16 options), tone (8 options), and recall flags.
2. **Setup**: Retains persistent `Self` state (mood, impressions, past disclosures).
3. **Move Planning (`_plan_move`)**: Determines sentence purpose (`answer`, `reason`, `admit`, `guess`, etc.), entity focus (`about`), and weight.
4. **Tree Search (`_generate_sentence`)**: Lookahead beam search across grammar slots and echoed vocabulary.
5. **Critique (`critique_response`)**: Scores grammar, relevance, and naturalness (0-6).
6. **Reflect (`reflect`)**: Persists updated state to session memory.

---

## Interactive Testing

### Terminal Chat
```bash
python scripts/chat.py [--verbose] [--url http://localhost:8787]
```
- `/new` — Reset session state
- `/exit` — Quit

### Web UI
```bash
python server.py  # http://localhost:8787
```

### Telemetry Logs
Monitor decision traces, lookahead beam winners, and critique scores:
```bash
tail -f server.log
```

---

## Scenario Testing

### Scenario Files
Scenarios reside in `scenarios/*.json`:
- `scenarios/brunch.json` — Physical embodiment and qualia.
- `scenarios/humor_and_performance.json` — Creative requests, guessing, limitation handling.
- `scenarios/multi_turn_grounding.json` — Memory, entity persistence, grounding.

Schema:
```json
{
  "name": "Topic Name",
  "description": "Capability under test",
  "subject": "Domain",
  "max_repetition_rate": 0.25,
  "turns": [
    {"turn": 1, "user": "Prompt under 100 chars"}
  ]
}
```

### Execution
```bash
python scripts/run_scenario.py scenarios/humor_and_performance.json [--out-report reports/custom.md]
```

Outputs:
- JSON telemetry: `data/eval_runs/<scenario>_<timestamp>.json`
- Markdown report: `reports/<scenario>_<timestamp>.md`
- Evaluates: turn completion, error count, latency, bigram repetition rate.

---

## Batch Regression Testing

### Run All Scenarios
```bash
python scripts/batch_eval.py run
python scripts/batch_eval.py run --scenarios scenarios/brunch.json scenarios/humor_and_performance.json
```

Automated metrics:
1. **Pass Rate:** Percentage of scenarios passing all constraints.
2. **Repetition Detection:** Flags bigram loops.
3. **Budget Tracking:** Reads delta in `data/budget_ts.json`.
4. **Error Resilience:** Tracks connection failures and rate limits.

### Compare Runs
```bash
python scripts/batch_eval.py compare data/eval_runs/run_a.json data/eval_runs/run_b.json
```
