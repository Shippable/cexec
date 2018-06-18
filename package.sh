#!/bin/bash -e

export BINARY_ARCHITECTURE="$1"
readonly VE_LOCATION=/tmp/cexec_pkg_ve

init_ve() {
  local arch=$(uname -m)
  virtualenv -p /usr/bin/python $VE_LOCATION
  source $VE_LOCATION/bin/activate
  pip install pyinstaller==3.3.1
  pip install -r requirements.txt
}

package() {
  local arch=$(uname -m)
  # 32-bit binaries are built on 32-bit docker containers running on 64-bit
  # machines. So, aarch32 is explicitly sent to package.sh, so that the binary
  # is added in the correct folder.
  if [ ! -z "$BINARY_ARCHITECTURE" ]; then
    arch="$BINARY_ARCHITECTURE"
  fi
  sudo rm -r dist/$arch/linux || true
  pyinstaller --distpath dist/$arch/linux --clean --hidden-import=requests main.py
  # x86_64 is the default architecture. So, the binary is copied to the default
  # path dist/main/
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

