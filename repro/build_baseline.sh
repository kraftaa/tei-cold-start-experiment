#!/usr/bin/env bash
set -euo pipefail

readonly REPOSITORY="https://github.com/huggingface/text-embeddings-inference.git"
readonly COMMIT="2bff275313a7b93e9a5d4dc1dbfdce8e72c7d820"
readonly SOURCE_DIR=".cache/src/tei-v1.8.0-${COMMIT}"
readonly IMAGE="tei-v1.8.0-correctness:2bff275"
readonly PATCH_DIR="${PWD}/repro/patches"

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

patches=(
  "tei-v1.8-respect-max-batch-requests.patch"
  "tei-v1.8-position-ids.patch"
  "tei-v1.8-metrics-0.23.1.patch"
)
for patch_name in "${patches[@]}"; do
  patch_path="${PATCH_DIR}/${patch_name}"
  if git -C "${SOURCE_DIR}" apply --reverse --check "${patch_path}" 2>/dev/null; then
    echo "Patch already applied: ${patch_name}"
  else
    git -C "${SOURCE_DIR}" apply --check "${patch_path}"
    git -C "${SOURCE_DIR}" apply "${patch_path}"
  fi
done

if [[ "$(git -C "${SOURCE_DIR}" rev-parse HEAD)" != "${COMMIT}" ]]; then
  echo "Source commit does not match ${COMMIT}" >&2
  exit 1
fi

docker build \
  --platform linux/amd64 \
  --build-arg "GIT_SHA=${COMMIT}" \
  --tag "${IMAGE}" \
  "${SOURCE_DIR}"

docker image inspect --format '{{.Id}} {{.Architecture}} {{.Os}}' "${IMAGE}"
