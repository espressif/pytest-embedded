set -eo

DEFAULT_PACKAGES=" \
  pytest-embedded \
  pytest-embedded-serial \
  pytest-embedded-serial-esp \
  pytest-embedded-idf \
"

if [[ -z "$TWINE_PASSWORD" ]]; then
  export TWINE_PASSWORD="$CI_JOB_TOKEN"
fi

if [[ -z "$TWINE_USERNAME" ]]; then
  export TWINE_USERNAME=gitlab-ci-token
fi

action=${1:-"install"}

for pkg in $DEFAULT_PACKAGES; do
  pushd "$pkg"
  if [ "$action" = "install" ]; then
    rm -rf ./build
    pip install -e .
  elif [ "$action" = "uninstall" ]; then
    pip uninstall -y $pkg
  elif [ "$action" = "build" ]; then
    python setup.py sdist bdist_wheel
  elif [ "$action" = "publish" ]; then
    python -m twine upload --repository-url $REPO_URL --verbose dist/*
  else
    echo "invalid argument. valid choices: install/uninstall/build/publish"
    exit 1
  fi
  popd
done
