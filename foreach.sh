#!/bin/bash

set -euo pipefail

DEFAULT_PACKAGES=" \
  pytest-embedded \
  pytest-embedded-serial \
  pytest-embedded-serial-esp \
  pytest-embedded-idf \
  pytest-embedded-jtag \
  pytest-embedded-qemu \
  pytest-embedded-arduino \
  pytest-embedded-wokwi \
  pytest-embedded-nuttx \
"

action=${1:-"install"}
res=0

# one-time command
pip install -U pip
if [ "$action" = "build" ]; then
  pip install -U flit
elif [ "$action" = "publish" ]; then
  pip install -U flit
fi

# for-loop each package
for pkg in $DEFAULT_PACKAGES; do
  pushd "$pkg"
  if [ "$action" = "install-editable" ]; then
    pip install -e .
  elif [ "$action" = "install" ]; then
    pip install .
  elif [ "$action" = "uninstall" ]; then
    pip uninstall -y $pkg
  elif [ "$action" = "build" ]; then
    flit build
  elif [ "$action" = "publish" ]; then
    flit publish
  else
    echo "invalid argument. valid choices: install-editable/install/uninstall/build/publish"
    exit 1
  fi
  popd
done

exit $res
