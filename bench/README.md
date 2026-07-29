# bench

Reusable benchmarking artifacts, independent of the rest of Clusius:

- `schema/result.schema.json` — the open result schema every Clusius run conforms to.
- `datasets/` — small task-appropriate eval sets used as the accuracy guard during
  auto-tuning.
- `results/` — real, committed results from actual runs (never mocked).
