# Contributing

## Workflow

We use [pre-commit](https://pre-commit.com) for code formatting, and some linter checks. You can install it by

```shell
$ pre-commit install
```

We use [commitizen](https://github.com/commitizen-tools/commitizen) to auto generate the [CHANGELOG.md](./CHANGELOG.md).
You don't need to install it or know anything about the tool itself, but please follow
the [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) rule when writing commit messages.

## Running Tests

By default, all tests under all plugins would be run.

```shell
$ pip install -r requirements.txt
$ bash foreach.sh install
$ # export DONT_SKIP_QEMU_TESTS=1 (when qemu-system-xtensa is ready)
$ # export DONT_SKIP_JTAG_TESTS=1 (when you have a jtag connection)
$ pytest
```

## Writing Tests

Basically we're following
the [official documentation](https://docs.pytest.org/en/stable/writing_plugins.html#testing-plugins). You could also
refer to the tests under each plugin.

## Building Docs

We use `mkdocs` and `mkdocstring` with theme `mkdocs-material` to build docs.

### Test Docs Locally

```shell
$ cd docs
$ pip install -r requirements.txt
$ mkdocs serve # For preview
$ mkdocs build # For build
```
