#!/bin/bash -e

readonly VE_LOCATION=/tmp/cexec_pkg_ve

init_ve() {
  local arch=$(uname -m)
  virtualenv -p /usr/bin/python $VE_LOCATION
  source $VE_LOCATION/bin/activate
  # TODO: remove this check once pyinstaller 3.4 is released
  if [ "$arch" != "aarch64" ]; then
    pip install pyinstaller==3.3
  fi
  pip install -r requirements.txt
}

package() {
  local arch=$(uname -m)
  sudo rm -r dist/$arch/linux || true
  pyinstaller --distpath dist/$arch/linux --clean --hidden-import=requests main.py
  if [ "$arch" == "x86_64" ]; then
    sudo rm -r dist/main || true
    mkdir -p dist/main
    sudo cp -rf dist/$arch/linux/main/. dist/main/
  fi
}

main() {
  init_ve
  package
}

main

