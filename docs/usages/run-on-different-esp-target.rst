############################################
 Tests in ESP-IDF Projects with ESP Targets
############################################

.. note::

   This guide only applies to ``--embedded-services esp,idf``.

For projects which depend on ESP-IDF, a common use case is to run tests on different ESP targets. This guide will show you how to run tests locally, and on CI, on different ESP targets.

*********************************************
 Getting Started - Select the Target via CLI
*********************************************

Here's an example on a minimal project which based on ESP-IDF, with the following folder structure:

.. code:: bash

   project/
   ├── CMakeLists.txt
   └── main/
       ├── CMakeLists.txt
       └── main.c

We could add a test case to the project. Usually we put it under the ``tests`` directory:

.. code:: python

   # test_hello_world.py
   def test_hello_world(dut):
       dut.expect('Hello World!')

The current folder structure looks like this:

.. code:: bash

   project/
   ├── CMakeLists.txt
   ├── main/
   │   ├── CMakeLists.txt
   │   └── main.c
   └── tests/
       └── test_hello_world.py

To run the test on ESP targets, we shall build the project first:

.. code:: bash

   idf.py set-target esp32 build

The current folder structure looks like this:

.. code:: bash

   project/
   ├── CMakeLists.txt
   ├── build/  # built binaries for esp32
   ├── main/
   │   ├── CMakeLists.txt
   │   └── main.c
   └── tests/
       └── test_hello_world.py

Then we can run the test on ESP32 by passing the CLI argument:

.. code:: bash

   pytest --target esp32 --embedded-services esp,idf

When running the same test on ESP32S2, we need to build the project again. In order to not overwrite the previous build, we can create a new build folder:

.. code:: bash

   idf.py -B build_esp32s2 set-target esp32s2 build

The current folder structure looks like this:

.. code:: bash

   project/
   ├── CMakeLists.txt
   ├── build/          # built binaries for esp32
   ├── build_esp32s2/  # built binaries for esp32s2
   ├── main/
   │   ├── CMakeLists.txt
   │   └── main.c
   └── tests/
       └── test_hello_world.py

Then we can run the test on ESP32S2 by passing the CLI argument:

.. code:: bash

   pytest --target esp32s2 --build-dir build_esp32s2 --embedded-services esp,idf

The ``--build-dir`` argument is used to specify the build directory to flash to the target automatically.

**********************************************
 Simplify the CLI Call - Using ``pytest.ini``
**********************************************

You may notice that in the above example, we need to specify the ``-embedded-services esp,idf`` every time we run the test on a different target. To simplify this, we can create a ``pytest.ini`` file under the project's root directory:

.. code:: ini

   [pytest]
   addopts =
     --embedded-services esp,idf

The current folder structure looks like this:

.. code:: bash

   project/
   ├── CMakeLists.txt
   ├── build/          # built binaries for esp32
   ├── build_esp32s2/  # built binaries for esp32s2
   ├── main/
   │   ├── CMakeLists.txt
   │   └── main.c
   ├── tests/
   │   └── test_hello_world.py
   └── pytest.ini

Then we can run the test on ESP32 by passing the CLI argument:

.. code:: bash

   pytest --target esp32

****************************************************
 One Step Further - Customizing the Build Directory
****************************************************

You may notice that in the above example, we need to specify the build directory every time we run the test on a different target. To simplify this, we can customize the a conftest.py file to set the build directory based on the target:

.. code:: python

   # conftest.py
   def build_dir(request, target):
       return f"build_{target}"

Now when we're running the test case on ESP32S2, we can simply run:

.. code:: bash

   pytest --target esp32s2

The build directory will be automatically set to ``build_esp32s2``.

Run the test case on ESP32 will fail, since we built it under the ``build`` directory and the test case is expecting the binaries under the ``build_esp32`` directory. Don't forget to pass the ``-B`` argument to build the project under a different build directory, as what we did in the previous example for ESP32S2.

***************
 Running on CI
***************

To run the test on CI, you can use the same approach as running locally. Basically, you need two types of jobs: "build jobs" and "test jobs".

In the build jobs, you build the project for different targets. Usually you can run it on linux machine, and build the project with the ESP-IDF docker image.

Here we provide a GitHub Actions example:

.. code:: yaml

   name: Build and Test Application

   on:
     pull_request:
       paths:
         - "src/**/*.c"
     push:
       branches:
         - main

   env:
     IDF_PATH: /opt/esp/idf

   defaults:
     run:
       shell: bash

   jobs:
     build:
       name: Build Test App
       strategy:
         fail-fast: false
         matrix:
           # choose the version of ESP-IDF to use for the build
           idf-branch:
             - release-v5.0
             - latest
           # choose the target to build for
           target:
             - esp32
             - esp32c3
       runs-on: ubuntu-22.04
       container:
         image: espressif/idf:${{ matrix.idf-branch }}
       steps:
         - uses: actions/checkout@v3
         - name: Build Test Application with ESP-IDF
           run: |
             . $IDF_PATH/export.sh
             idf.py -B build_${{ matrix.target }} set-target ${{ matrix.target }} build
         - name: Upload files to artifacts for run-target job
           uses: actions/upload-artifact@v4
           with:
             name: built_binaries_${{ matrix.target }}_${{ matrix.idf-branch }}
             path: |
               **/build**/bootloader/bootloader.bin
               **/build**/partition_table/partition-table.bin
               **/build**/*.bin
               **/build**/*.elf
               **/build**/flasher_args.json
             if-no-files-found: error

In the test jobs, you run the test cases on different targets. Usually you need to register a self-hosted runner that connects to the ESP targets, and run the test cases on the runner.

Here we provide a GitHub Actions example:

.. code:: yaml

   name: Build and Test Application

   on:
     pull_request:
       paths:
         - "src/**/*.c"
     push:
       branches:
         - main

   env:
     IDF_PATH: /opt/esp/idf
     test_dirs: examples

   defaults:
     run:
       shell: bash

   jobs:
     build:
       .. # same as above
     target-test:
       name: Run Test App on ESP Target
       needs: build
       strategy:
         fail-fast: false
         matrix:
           # choose the version of ESP-IDF to use for the build
           idf-branch:
             # - release-v5.0
             # - release-v5.1
             - latest
           # choose the target to build for
           target:
             - esp32
             - esp32c3
       runs-on: ubuntu-22.04
       container:
         image: hfudev/qemu:main
       steps:
         - uses: actions/checkout@v3
         - uses: actions/download-artifact@v2
           with:
             name: built_binaries_${{ matrix.target }}_${{ matrix.idf-branch }}
         - name: Install Python packages
           run: |
             . $IDF_PATH/export.sh
             pip install \
               pytest-embedded-idf \
               pytest-embedded-qemu
         - name: Run Test App on target
           run: |
             . $IDF_PATH/export.sh
             pytest ${{ env.test_dirs }} \
               --target ${{ matrix.target }} \
               --embedded-services idf,qemu \
               --junit-xml test_${{ matrix.target }}_${{ matrix.idf-branch }}.xml \
               --build-dir build_${{ matrix.target }}_${{ matrix.idf-branch }}
         - uses: actions/upload-artifact@v2
           if: always()
           with:
             name: test_${{ matrix.target }}_${{ matrix.idf-branch }}_junit
             path: test_${{ matrix.target }}_${{ matrix.idf-branch }}.xml
