# Contributing

## Running Tests

By default, all tests under all plugins would be run.

```shell
$ pip install -r requirements.txt
$ bash foreach.sh install
$ export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
$ # export DONT_SKIP_SERIAL_TESTS=1 (when you connected to an espressif board)
$ # export DONT_SKIP_SERIAL_TESTS=1 (when qemu-system-xtensa is ready)
$ pytest
```

## Writing Tests

Basically we're following
the [official documentation](https://docs.pytest.org/en/stable/writing_plugins.html#testing-plugins). You could also
refer to the tests under each plugin.

## Building Docs

### Building Docs Locally

```shell
$ cd docs
$ pip install -r requirements.txt
$ make html
```

### Adding new Plugins

You could use `sphinx-apidoc` to generate the initial version of a new plugin's api reference page. (Or you could write
it manually)

```shell
$ pip install sphinx-apidoc
$ sphinx-apidoc -o plugins <new_package_path>
```
