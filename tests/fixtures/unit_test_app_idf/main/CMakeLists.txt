idf_component_register(SRCS "test_app_main.c"
                            "case_tester_example.c"
                       INCLUDE_DIRS "."
                       PRIV_REQUIRES test_utils unity
                       WHOLE_ARCHIVE)
