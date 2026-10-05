#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

python_bin="${PYTHON_BIN:-python3}"
"$python_bin" -m venv .venv-macos
.venv-macos/bin/python -m pip install --upgrade pip
.venv-macos/bin/python -m pip install -r requirements-macos.txt
.venv-macos/bin/python scripts/make_macos_icon.py

.venv-macos/bin/python -m PyInstaller \
  --noconfirm --clean --onedir --windowed \
  --name SonyFocusViewer \
  --osx-bundle-identifier com.liu223344.focusviewer \
  --icon build_assets/FocusViewer.icns \
  --collect-all rawpy --collect-all pillow_heif \
  app.py

.venv-macos/bin/python scripts/patch_macos_bundle.py dist/SonyFocusViewer.app
codesign --force --deep --sign - dist/SonyFocusViewer.app
arch_name="$(uname -m)"
ditto -c -k --sequesterRsrc --keepParent dist/SonyFocusViewer.app "dist/SonyFocusViewer-macOS-${arch_name}.zip"
echo "Built dist/SonyFocusViewer.app and dist/SonyFocusViewer-macOS-${arch_name}.zip"
