#!/usr/bin/env bash
set -euo pipefail

readonly REPOSITORY="https://github.com/malaiwah/text-embeddings-inference.git"
readonly COMMIT="5806bdc99f11ad490cd7e38c1f4dd757034c0adb"
readonly SOURCE_DIR=".cache/src/tei-warmup-pr-${COMMIT}"
readonly TARGET_DIR=".cache/build/tei-warmup-pr-native-target"
readonly BINARY=".cache/bin/tei-warmup-pr-5806bdc"

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

readonly PATCH="${PWD}/repro/patches/tei-respect-max-batch-requests.patch"
if git -C "${SOURCE_DIR}" apply --reverse --check "${PATCH}" 2>/dev/null; then
  echo "Correctness patch already applied"
else
  git -C "${SOURCE_DIR}" apply --check "${PATCH}"
  git -C "${SOURCE_DIR}" apply "${PATCH}"
fi

resolved_commit="$(git -C "${SOURCE_DIR}" rev-parse HEAD)"
if [[ "${resolved_commit}" != "${COMMIT}" ]]; then
  echo "Resolved ${resolved_commit}, expected ${COMMIT}" >&2
  exit 1
fi

# ort-sys prefers any pkg-config ONNX Runtime over its pinned downloaded
# archive. Homebrew upgrades can leave that dylib with stale Abseil links, so
# use ort-sys's verified archive for a self-contained macOS smoke binary.
if [[ "$(uname -s)" == "Darwin" ]]; then
  export PKG_CONFIG_LIBDIR=/nonexistent
fi

CARGO_TARGET_DIR="${PWD}/${TARGET_DIR}" cargo build \
  --manifest-path "${SOURCE_DIR}/Cargo.toml" \
  --release \
  --bin text-embeddings-router \
  --no-default-features \
  --features ort,http,static-linking

mkdir -p "$(dirname "${BINARY}")"
cp "${TARGET_DIR}/release/text-embeddings-router" "${BINARY}"
chmod +x "${BINARY}"
"${BINARY}" --help | grep --fixed-strings -- '--warmup-tokens'
