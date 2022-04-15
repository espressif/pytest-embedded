set -eo

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

for pkg in $DEFAULT_PACKAGES; do
  pushd "$pkg"
  if [ "$action" = "install" ]; then
    rm -rf ./build
    if [ "$pkg" = "pytest-embedded-idf" ]; then
      pip install -e ".[serial]"
    else
      pip install -e .
    fi
  elif [ "$action" = "uninstall" ]; then
    pip uninstall -y $pkg
  elif [ "$action" = "build" ]; then
    python setup.py sdist bdist_wheel
  elif [ "$action" = "publish" ]; then
    python -m twine upload --verbose dist/* || res=1
  else
    echo "invalid argument. valid choices: install/uninstall/build/publish"
    exit 1
  fi
  popd
done

exit $res
