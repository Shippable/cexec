#!/bin/bash -e

readonly PROGDIR=$(readlink -m $(dirname $0))
readonly ARTIFACTS_DIR="/shippableci"
readonly SUDO=`which sudo`

check_git() {
  echo "Looking for git..."
  {
    GIT=$(which git)
  } || {
    echo "Could not find git. Installing git-core..."
  }

  if [ -z "$GIT" ]; then
    $SUDO apt-get install -y git-core
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

update_build_dirs() {
  mkdir -p $ARTIFACTS_DIR
}

run_build() {
  /home/shippable/cexec/dist/main/main
}

main() {
  check_git
  check_ssh_agent
  check_python
  update_dir
  update_perms
  update_path
  update_ssh_config
  update_build_dirs
  run_build
}

main
