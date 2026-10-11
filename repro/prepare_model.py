#!/usr/bin/env python3
"""Create a pinned local model snapshot and apply the documented TEI config workaround."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time


ALIASES = ("n_embd", "n_layer", "n_head")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    commands = [
        ["git", "init", str(output)],
        ["git", "-C", str(output), "remote", "add", "origin", f"https://huggingface.co/{args.model_id}"],
        ["git", "-C", str(output), "fetch", "--depth", "1", "origin", args.revision],
        ["git", "-C", str(output), "checkout", "--detach", "FETCH_HEAD"],
    ]
    for command in commands:
        completed = subprocess.run(command)
        if completed.returncode != 0:
            return completed.returncode
    config_path = output / "config.json"
    original_hash = sha256(config_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    removed = {key: config.pop(key) for key in ALIASES if key in config}
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = {
        "prepared_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_id": args.model_id,
        "revision": args.revision,
        "resolved_git_commit": subprocess.check_output(
            ["git", "-C", str(output), "rev-parse", "HEAD"], text=True
        ).strip(),
        "config_original_sha256": original_hash,
        "config_prepared_sha256": sha256(config_path),
        "removed_aliases": removed,
        "reason": "TEI Qwen3 parser rejects duplicate GPT-style aliases; weights and tokenizer are unchanged.",
    }
    (output / "tei-cold-start-preparation.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
