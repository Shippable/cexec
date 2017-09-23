#!/bin/bash -e

readonly VE_LOCATION=/tmp/cexec_pkg_ve

init_ve() {
  virtualenv -p /usr/bin/python $VE_LOCATION
  source $VE_LOCATION/bin/activate
  pip install pyinstaller
  pip install -r requirements.txt
}

package() {
  local arch=$(uname -m)
  if [ "$arch" == "x86_64" ]; then
    if [ -d dist/main ]; then
      sudo rm -r dist/main
    fi
    pyinstaller --clean --hidden-import=requests main.py
  fi
  if [ -d dist/$arch/linux ]; then
    sudo rm -r dist/$arch/linux
  fi
  pyinstaller --distpath dist/$arch/linux --clean --hidden-import=requests main.py
}

main() {
  init_ve
  package
}

main
