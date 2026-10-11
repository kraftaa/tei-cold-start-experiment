#!/usr/bin/env bash
set -euo pipefail

readonly REPOSITORY="https://github.com/huggingface/text-embeddings-inference.git"
readonly COMMIT="2bff275313a7b93e9a5d4dc1dbfdce8e72c7d820"
readonly SOURCE_DIR=".cache/src/tei-v1.8.0-2bff275"
readonly TARGET_DIR=".cache/build/tei-v1.8.0-native-target"
readonly BINARY=".cache/bin/tei-v1.8.0-2bff275-batchcap"
readonly PATCH="${PWD}/repro/patches/tei-v1.8-respect-max-batch-requests.patch"
readonly METRICS_PATCH="${PWD}/repro/patches/tei-v1.8-metrics-0.23.1.patch"
readonly POSITION_IDS_PATCH="${PWD}/repro/patches/tei-v1.8-position-ids.patch"

if [[ ! -d "${SOURCE_DIR}/.git" ]]; then
  if [[ -e "${SOURCE_DIR}" ]]; then
    echo "Refusing to overwrite non-Git path: ${SOURCE_DIR}" >&2
    exit 1
  fi
  mkdir -p "${SOURCE_DIR}"
  git -C "${SOURCE_DIR}" init
  git -C "${SOURCE_DIR}" remote add origin "${REPOSITORY}"
fi
git -C "${SOURCE_DIR}" fetch --depth 1 origin "${COMMIT}"
git -C "${SOURCE_DIR}" checkout --detach "${COMMIT}"
if git -C "${SOURCE_DIR}" apply --reverse --check "${PATCH}" 2>/dev/null; then
  echo "Correctness patch already applied"
else
  git -C "${SOURCE_DIR}" apply --check "${PATCH}"
  git -C "${SOURCE_DIR}" apply "${PATCH}"
fi
if git -C "${SOURCE_DIR}" apply --reverse --check "${POSITION_IDS_PATCH}" 2>/dev/null; then
  echo "Position IDs compatibility patch already applied"
else
  git -C "${SOURCE_DIR}" apply --check "${POSITION_IDS_PATCH}"
  git -C "${SOURCE_DIR}" apply "${POSITION_IDS_PATCH}"
fi
if git -C "${SOURCE_DIR}" apply --reverse --check "${METRICS_PATCH}" 2>/dev/null; then
  echo "Metrics compatibility patch already applied"
else
  git -C "${SOURCE_DIR}" apply --check "${METRICS_PATCH}"
  git -C "${SOURCE_DIR}" apply "${METRICS_PATCH}"
fi

if [[ "$(git -C "${SOURCE_DIR}" rev-parse HEAD)" != "${COMMIT}" ]]; then
  echo "Source commit does not match ${COMMIT}" >&2
  exit 1
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  export PKG_CONFIG_LIBDIR=/nonexistent
  readonly FEATURES="ort,http"
else
  readonly FEATURES="ort,http,static-linking"
fi

# TEI 1.8's pinned metrics 0.23.0 no longer compiles under Rust 1.98;
# use the locally available pre-regression toolchain for reproducibility.
CARGO_TARGET_DIR="${PWD}/${TARGET_DIR}" rustup run 1.82.0 cargo build \
  --manifest-path "${SOURCE_DIR}/Cargo.toml" \
  --release \
  --bin text-embeddings-router \
  --no-default-features \
  --features "${FEATURES}"

mkdir -p "$(dirname "${BINARY}")"
cp "${TARGET_DIR}/release/text-embeddings-router" "${BINARY}"
chmod +x "${BINARY}"
"${BINARY}" --help >/dev/null
