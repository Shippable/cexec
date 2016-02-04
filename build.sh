#!/bin/bash -e

readonly PROGDIR=$(readlink -m $(dirname $0))
readonly ARTIFACTS_DIR="/shippableci"

update_dir() {
  cd $PROGDIR
}

update_perms() {
  SUDO=`which sudo`
  $SUDO mkdir -p /home/shippable/build/logs
  $SUDO mkdir -p /shippableci
  $SUDO chown -R $USER:$USER /home/shippable/build/logs
  $SUDO chown -R $USER:$USER /home/shippable/build
}

update_path() {
  export PATH=$PATH:$PROGDIR/bin
  echo PATH=$PATH:$PROGDIR/bin >> /etc/environment
}

update_ssh_config() {
  mkdir -p $HOME/.ssh
  touch $HOME/.ssh/config
  # Turn off strict host key checking
  echo -e "\nHost *\n\tStrictHostKeyChecking no" >> $HOME/.ssh/config
}

update_build_dirs() {
  mkdir -p $ARTIFACTS_DIR
}

run_build() {
  /home/shippable/cexec/dist/main/main
}

main() {
  update_dir
  update_perms
  update_path
  update_ssh_config
  update_build_dirs
  run_build
}

main
