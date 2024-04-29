# Contributing

## Workflow

We use [pre-commit](https://pre-commit.com) for code formatting, and some linter checks. You can install it by

```shell
$ pre-commit install -t pre-commit -t commit-msg
```

We use [commitizen](https://github.com/commitizen-tools/commitizen) to auto generate the [CHANGELOG.md](./CHANGELOG.md).
You don't need to install it or know anything about the tool itself, but please follow
the [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) rule when writing commit messages.

## Install Virtual Environment

We recommend using virtual environment for development. You can create one by

```shell
$ python -m venv .venv
$ source .venv/bin/activate
```

## Install Dependencies

We recommend to install the local subpackages in editable mode.

```shell
$ pip install -r requirements.txt
$ bash foreach.sh install-editable
```

## Running Tests

By default, all tests under all plugins would be run.

```shell
$ # export DONT_SKIP_JTAG_TESTS=1 (when you have a jtag connection)
$ pytest
```

## Writing Tests

Basically we're following
the [official documentation](https://docs.pytest.org/en/stable/writing_plugins.html#testing-plugins). You could also
refer to the tests under each plugin.

## Building Docs

We use `sphinx` with espressif theme to build the docs. The docstring is written in `Google` style. Here's an [example](https://www.sphinx-doc.org/en/master/usage/extensions/example_google.html).

For building locally, you need to install the dependencies first.

```shell
$ pip install -r docs/requirements.txt
```

Then you can build the docs by

```shell
$ cd docs
$ make html
```

For documentation preview, you may use any browser you prefer. The executable has to be searchable in `PATH`. For example we're using firefox here.

```shell
$ firefox _build/html/index.html
```
