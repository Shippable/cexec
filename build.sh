#!/bin/bash -e

readonly PROGDIR=$(readlink -m $(dirname $0))
IS_APT_UPDATED=false
IS_UBUNTU=false
HAS_APT_GET=false

warn_config() {
  echo "********************************************************************"
  echo "*                           WARNING                                *"
  echo "*                                                                  *"
  echo "* You are not running Ubuntu. This configuration is not supported. *"
  echo "*                                                                  *"
  echo "********************************************************************"
}

check_ubuntu() {
  IS_UBUNTU=false
  {
    LSB_RELEASE=$(lsb_release -a)
    echo $LSB_RELEASE | grep Ubuntu
    if [ "$?" == 0 ]; then
      IS_UBUNTU=true
      echo "Ubuntu confirmed"
    else
      warn_config
    fi
  } || {
    warn_config
  }
}

check_apt_get() {
  {
    echo "Looking for apt-get..."
    APT_GET=$(which apt-get)
  } || {
    HAS_APT_GET=false
    echo "Could not find apt-get. Missing build system dependencies will not be automatically installed."
  }
  if [ ! -z "$APT_GET" ]; then
    HAS_APT_GET=true
    echo "Found apt-get at $APT_GET"
  fi
}

update_apt() {
  if [ "$HAS_APT_GET" == false ]; then return; fi
  if [ "$IS_APT_UPDATED" == true ]; then return; fi
  $SUDO apt-get update
  IS_APT_UPDATED=true
}

check_sudo() {
  if [ "$HAS_APT_GET" == false ]; then return; fi
  echo "Looking for sudo..."
  {
    SUDO=$(which sudo)
  } || {
    echo "Could not find sudo. Installing..."
  }

  if [ -z "$SUDO" ]; then
    update_apt
    apt-get install -y sudo
    echo "Installed sudo"
    SUDO=$(which sudo)
  else
    echo "Found sudo at $SUDO"
  fi
}

check_git() {
  if [ "$HAS_APT_GET" == false  ]; then return; fi
  echo "Looking for git..."
  {
    GIT=$(which git)
  } || {
    echo "Could not find git. Installing git..."
  }

  if [ -z "$GIT" ]; then
    update_apt
    $SUDO apt-get install -y git
    echo "Installed git-core"
  else
    echo "Found git at $GIT"
  fi
}

check_ssh_agent() {
  if [ "$HAS_APT_GET" == false ]; then return; fi
  echo "Looking for ssh-agent"
  {
    SSH_AGENT=$(which ssh-agent)
  } || {
    echo "Could not find ssh-agent. Installing..."
  }

  if [ -z "$SSH_AGENT" ]; then
    update_apt
    $SUDO apt-get install -y openssh-client
    echo "Installed openssh-client"
  else
    echo "Found ssh-agent at $SSH_AGENT"
  fi
}

check_python() {
  if [ "$HAS_APT_GET" == false ]; then return; fi
  echo "Looking for python..."
  {
    PYTHON=$(which python)
  } || {
    echo "Could not find python. Installing..."
  }

  if [ -z "$PYTHON" ]; then
    update_apt
    $SUDO apt-get install -y python
    echo "Installed python"
  else
    echo "Found python at $PYTHON"
  fi
}

update_dir() {
  cd $PROGDIR
}

update_perms() {
  local build_user=$(whoami)
  $SUDO mkdir -p /shippableci
  $SUDO chown -R $build_user:$build_user /shippableci

  $SUDO mkdir -p /tmp/ssh
  $SUDO chown -R $build_user:$build_user /tmp/ssh
  $SUDO chown -R $build_user:$build_user /home/shippable/cache
}

copy_bin_dir() {
  $SUDO cp $PROGDIR/bin/* /usr/local/bin/
}

update_ssh_config() {
  mkdir -p $HOME/.ssh
  touch $HOME/.ssh/config
  # Turn off strict host key checking
  echo -e "\nHost *\n\tStrictHostKeyChecking no" >> $HOME/.ssh/config
}

check_uuid_binary(){
  if [ ! -f "/proc/sys/kernel/random/uuid" ]; then
    echo "/proc/sys/kernel/random/uuid was not found. Are you using a linux-based image?"
    exit 1
  fi
}

run_build() {
  local use_default_arch=true
  if [ ! -z "$SHIPPABLE_NODE_ARCHITECTURE" ]; then
    if [ -f /home/shippable/cexec/dist/"$SHIPPABLE_NODE_ARCHITECTURE"/linux/main/main ]; then
      use_default_arch=false
    else
      echo "cexec binary not present in $SHIPPABLE_NODE_ARCHITECTURE folder..."
    fi
  fi
  if [ "$use_default_arch" == true ]; then
    echo "Running build using the default, x86_64, binary..."
    /home/shippable/cexec/dist/main/main
  else
    /home/shippable/cexec/dist/"$SHIPPABLE_NODE_ARCHITECTURE"/linux/main/main
  fi
}

main() {
  check_ubuntu
  check_apt_get
  check_sudo
  check_git
  check_ssh_agent
  check_python
  update_dir
  update_perms
  copy_bin_dir
  update_ssh_config
  check_uuid_binary
  run_build
}

main

