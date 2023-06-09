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
"

action=${1:-"install"}
res=0

pip install flit

for pkg in $DEFAULT_PACKAGES; do
  pushd "$pkg"
  if [ "$action" = "install" ]; then
    flit install -s
  elif [ "$action" = "uninstall" ]; then
    pip uninstall -y $pkg
  elif [ "$action" = "build" ]; then
    flit build
  elif [ "$action" = "publish" ]; then
    flit upload
  else
    echo "invalid argument. valid choices: install/uninstall/build/publish"
    exit 1
  fi
  popd
done

exit $res
