#!/bin/bash -e

readonly VE_LOCATION=/tmp/cexec_pkg_ve

init_ve() {
  virtualenv -p /usr/bin/python $VE_LOCATION
  source $VE_LOCATION/bin/activate
  pip install pyinstaller
  pip install -r requirements.txt
}

package() {
  sudo rm -r dist
  pyinstaller --clean --hidden-import=requests main.py
}

main() {
  init_ve
  package
}

main
