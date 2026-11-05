#!/usr/bin/env bash
# Build signed release APKs and verify their signatures and permissions.
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

signing_store="${SNAPREP_SIGNING_KEY_STORE:-$project_dir/.secrets/android-upload.jks}"
signing_alias="${SNAPREP_SIGNING_KEY_ALIAS:-snaprep}"
if [[ -z "${FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD:-}" && -f "$project_dir/.secrets/android-signing.env" ]]; then
  # Generated locally with mode 600; never included in the app package.
  source "$project_dir/.secrets/android-signing.env"
fi
if [[ ! -f "$signing_store" ]]; then
  echo "Signing keystore missing: $signing_store" >&2
  exit 1
fi
if [[ -z "${FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD:-}" ]]; then
  echo "Set FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD before building." >&2
  exit 1
fi
if [[ ! -x .venv/bin/flet ]]; then
  echo "Install project dependencies with uv sync first." >&2
  exit 1
fi

android_sdk="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Android/sdk}}"
apksigner_bin="$(command -v apksigner || true)"
aapt_bin="$(command -v aapt || true)"
if [[ -z "$apksigner_bin" ]]; then
  apksigner_bin="$(find "$android_sdk/build-tools" -maxdepth 2 -name apksigner -type f 2>/dev/null | sort -V | tail -n 1 || true)"
fi
if [[ -z "$aapt_bin" ]]; then
  aapt_bin="$(find "$android_sdk/build-tools" -maxdepth 2 -name aapt -type f 2>/dev/null | sort -V | tail -n 1 || true)"
fi
if [[ -z "$apksigner_bin" || -z "$aapt_bin" ]]; then
  echo "Android SDK build-tools (apksigner and aapt) are required to verify the APK." >&2
  exit 1
fi

build_marker="$(mktemp)"
trap 'rm -f "$build_marker"' EXIT

.venv/bin/flet build apk --python-version 3.13 \
  --android-signing-key-store "$signing_store" \
  --android-signing-key-alias "$signing_alias"

mapfile -d '' -t apks < <(find build/apk -maxdepth 1 -type f -name '*.apk' -newer "$build_marker" -print0)
if (( ${#apks[@]} == 0 )); then
  echo "No APK found in build/apk." >&2
  exit 1
fi
for apk in "${apks[@]}"; do
  verification="$("$apksigner_bin" verify --verbose --print-certs "$apk")"
  if [[ "$verification" == *"Android Debug"* ]]; then
    echo "Debug certificate detected in $apk" >&2
    exit 1
  fi
  expected_fingerprint="$(tr -d ':[:space:]' < scripts/android_upload_cert.sha256 | tr '[:upper:]' '[:lower:]')"
  actual_fingerprint="$(printf '%s\n' "$verification" | sed -n 's/^Signer #1 certificate SHA-256 digest: //p' | head -n 1 | tr -d ':[:space:]' | tr '[:upper:]' '[:lower:]')"
  if [[ -z "$actual_fingerprint" || "$actual_fingerprint" != "$expected_fingerprint" ]]; then
    echo "APK signer does not match the rotated SnapRep upload certificate: $apk" >&2
    exit 1
  fi
  permissions="$("$aapt_bin" dump permissions "$apk")"
  found_vibrate=false
  while IFS= read -r permission; do
    if [[ "$permission" == "com.datlabs.snap_rep.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION" ]]; then
      continue
    fi
    if [[ "$permission" != "android.permission.VIBRATE" ]]; then
      echo "Unexpected permission in $apk: $permission" >&2
      exit 1
    fi
    found_vibrate=true
  done < <(printf '%s\n' "$permissions" | sed -n "s/.*uses-permission: name='\([^']*\)'.*/\1/p")
  if [[ "$found_vibrate" != true ]]; then
    echo "Expected VIBRATE permission missing from $apk" >&2
    exit 1
  fi
  echo "Verified signed APK and permissions: $apk"
done
