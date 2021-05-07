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

if [[ -n "$REPO_URL" ]]; then
  export REPO_URL="--repository-url $REPO_URL"
fi

action=${1:-"install"}

for pkg in $DEFAULT_PACKAGES; do
  pushd "$pkg"
  if [ "$action" = "install" ]; then
    pip install -e .
  elif [ "$action" = "build" ]; then
    python setup.py sdist bdist_wheel
  elif [ "$action" = "publish" ]; then
    python -m twine upload "$REPO_URL" --verbose dist/*
  else
    echo "invalid argument. valid choices: install/build/publish"
    exit 1
  fi
  popd
done
