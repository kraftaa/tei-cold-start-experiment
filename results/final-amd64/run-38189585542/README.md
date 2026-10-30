# Final native AMD64 benchmark artifact

This directory preserves the downloaded artifact from the successful four-arm benchmark so the evidence does not disappear when GitHub's artifact retention period ends.

## Provenance

- GitHub Actions run: [#38189585542](https://github.com/kraftaa/tei-cold-start-experiment/actions/runs/38189585542)
- Artifact name: `amd64-cold-start-38189585542`
- Repository commit: `7131f3c7daf880f969bab1dc8f310c718f811385`
- Workflow environment capture: `2026-10-12T00:55:52Z`
- Platform: native `x86_64`, Ubuntu 24.04.5 LTS
- CPU reported by runner: AMD EPYC 7763, 4 logical CPUs

## Contents

- `ci/environment.json`: host and runtime metadata;
- `ci/references/`: pinned correctness reference used by all candidate arms;
- `ci/raw/`: one JSONL record per fresh-process trial;
- `ci/summary/`: machine-readable JSON and readable Markdown summaries;
- `logs/`: the server output for every trial.

The raw records include the corresponding server-log path used while the workflow was running. GitHub's run page also retains the original job log.

## Interpretation

The headline comparison is the candidate's default warmup versus the same binary with 64-token and zero-token warmup. This isolates the warmup setting. All arms completed 20/20 correct trials. See the repository [README](../../../README.md) and [decision record](../../../docs/decision.md) for the result and limitations.

This was an exploratory native AMD64 GitHub-hosted run, not the final fixed Spot-instance/container validation.
