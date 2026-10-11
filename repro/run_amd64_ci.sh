#!/usr/bin/env bash
set -uo pipefail

trials="${1:-20}"
if ! [[ "${trials}" =~ ^[1-9][0-9]*$ ]]; then
  echo "usage: $0 [positive-trial-count]" >&2
  exit 2
fi

mkdir -p results/ci/raw results/ci/summary results/ci/references

overall=0
run_case() {
  local config="$1"
  local output="$2"
  if ! python3 bench/run.py --config "${config}" --trials "${trials}" --output "${output}"; then
    overall=1
  fi
  if [[ -s "${output}" ]]; then
    python3 bench/summarize.py "${output}" \
      --json-output "results/ci/summary/$(basename "${output}" .jsonl).json" \
      --markdown-output "results/ci/summary/$(basename "${output}" .jsonl).md" || overall=1
  fi
}

python3 repro/capture_environment.py --output results/ci/environment.json || overall=1

reference_output="results/ci/raw/baseline-reference.jsonl"
if ! python3 bench/run.py \
  --config repro/configs/tei-v1.8.0-cpu-int8-correctness.json \
  --trials 1 \
  --capture-reference \
  --output "${reference_output}"; then
  overall=1
fi

if [[ -f results/ci/references/tei-v1.8.0-cpu-int8-correctness.json ]]; then
  run_case \
    repro/configs/tei-v1.8.0-cpu-int8-correctness.json \
    results/ci/raw/baseline.jsonl
  run_case \
    repro/configs/tei-warmup-pr-zero-amd64-ci.json \
    results/ci/raw/candidate-zero.jsonl
  run_case \
    repro/configs/tei-warmup-pr-64-amd64-ci.json \
    results/ci/raw/candidate-64.jsonl
else
  echo "Baseline reference was not created; candidate comparisons cannot run." >&2
  overall=1
fi

exit "${overall}"
