cmake_minimum_required(VERSION 3.16)

set(EXTRA_COMPONENT_DIRS
    "$ENV{IDF_PATH}/tools/test_apps/components")

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(case_tester_example)
