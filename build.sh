#!/bin/bash -e

readonly PROGDIR=$(readlink -m $(dirname $0))
readonly ARTIFACTS_DIR="/shippableci"
readonly SUDO=`which sudo`

update_dir() {
  cd $PROGDIR
}

update_perms() {
  $SUDO mkdir -p /shippableci
  $SUDO chown -R $USER:$USER /shippableci

  $SUDO mkdir -p /tmp/ssh
  $SUDO chown -R $USER:$USER /tmp/ssh
}

update_path() {
  export PATH=$PATH:$PROGDIR/bin
  echo PATH=$PATH:$PROGDIR/bin | $SUDO tee -a /etc/environment
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
