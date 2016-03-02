#!/bin/bash -e

readonly PROGDIR=$(readlink -m $(dirname $0))
IS_APT_UPDATED=false

update_apt() {
  if [ "$IS_APT_UPDATED" == true ]; then return; fi
  $SUDO apt-get update
  IS_APT_UPDATED=true
}

check_sudo() {
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

run_build() {
  /home/shippable/cexec/dist/main/main
}

main() {
  check_sudo
  check_git
  check_ssh_agent
  check_python
  update_dir
  update_perms
  update_path
  update_ssh_config
  run_build
}

main
