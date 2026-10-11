#!/usr/bin/env bash
set -euo pipefail

readonly REPOSITORY="https://github.com/malaiwah/text-embeddings-inference.git"
readonly COMMIT="5806bdc99f11ad490cd7e38c1f4dd757034c0adb"
readonly SOURCE_DIR=".cache/src/tei-warmup-pr-${COMMIT}"
readonly IMAGE="tei-warmup-pr:5806bdc"

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

docker build \
  --platform linux/amd64 \
  --build-arg "GIT_SHA=${COMMIT}" \
  --tag "${IMAGE}" \
  "${SOURCE_DIR}"

docker image inspect --format '{{.Id}} {{.Architecture}} {{.Os}}' "${IMAGE}"
