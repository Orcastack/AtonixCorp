#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
REGISTRY_PREFIX=${REGISTRY_PREFIX:-}
VERSION_TAG=${VERSION_TAG:-local}

tag_image() {
  local image_name=$1
  if [[ -n "$REGISTRY_PREFIX" ]]; then
    printf '%s/%s:%s' "$REGISTRY_PREFIX" "$image_name" "$VERSION_TAG"
  else
    printf '%s:%s' "$image_name" "$VERSION_TAG"
  fi
}

build_image() {
  local image_tag=$1
  local dockerfile=$2
  local context_dir=$3

  echo "==> Building $image_tag from $dockerfile"
  docker build -f "$dockerfile" -t "$image_tag" "$context_dir"
}

cd "$ROOT_DIR"

API_DEV_IMAGE=$(tag_image ledgora/api-dev)
API_PROD_IMAGE=$(tag_image ledgora/backend)
APP_DEV_IMAGE=$(tag_image ledgora/app-dev)
APP_PROD_IMAGE=$(tag_image ledgora/app)

build_image "$API_DEV_IMAGE" api/Dockerfile api
build_image "$API_PROD_IMAGE" api/Dockerfile.prod api
build_image "$APP_DEV_IMAGE" app/Dockerfile app
build_image "$APP_PROD_IMAGE" app/Dockerfile.prod app

cat <<EOF

Built images:
  $API_DEV_IMAGE
  $API_PROD_IMAGE
  $APP_DEV_IMAGE
  $APP_PROD_IMAGE

Compose service mapping:
  api, banking-sync, approval-digest -> $API_DEV_IMAGE (local dev uses api/Dockerfile)
  app -> $APP_DEV_IMAGE
  db -> postgres image pulled from registry, not built locally

Production release mapping:
  backend -> $API_PROD_IMAGE
  app -> $APP_PROD_IMAGE
EOF