#!/bin/bash
# Builds Shajara.app (Apple Silicon + Intel) without opening Xcode.
#   ./build.sh            -> build/Shajara.app
#   ./build.sh install    -> also copies it to /Applications
set -euo pipefail
cd "$(dirname "$0")"

APP=build/Shajara.app
MIN=13.0
SOURCES=(Shajara/*.swift)
SDK=$(xcrun --sdk macosx --show-sdk-path)

rm -rf "$APP" build/obj
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources" build/obj

for arch in arm64 x86_64; do
  echo "→ $arch uchun kompilyatsiya…"
  xcrun swiftc -O -parse-as-library -swift-version 5 \
    -sdk "$SDK" -target "$arch-apple-macos$MIN" \
    -o "build/obj/Shajara-$arch" "${SOURCES[@]}"
done
lipo -create build/obj/Shajara-arm64 build/obj/Shajara-x86_64 -output "$APP/Contents/MacOS/Shajara"

cp Info.plist "$APP/Contents/Info.plist"
cp Resources/AppIcon.icns "$APP/Contents/Resources/AppIcon.icns"
printf 'APPL????' > "$APP/Contents/PkgInfo"

# Ad-hoc signature: enough to run on this Mac. For other Macs / the App Store,
# sign with your Developer ID instead (see README.md).
codesign --force --deep --options runtime --sign "${SIGN_IDENTITY:--}" \
  --entitlements Shajara.entitlements "$APP"

echo "✓ Tayyor: $(pwd)/$APP"

if [[ "${1:-}" == "install" ]]; then
  rm -rf /Applications/Shajara.app
  cp -R "$APP" /Applications/
  echo "✓ /Applications/Shajara.app ga oʻrnatildi"
fi
