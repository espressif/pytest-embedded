idf_component_register(SRCS "hello_world_main.c"
                       INCLUDE_DIRS ""
                       REQUIRES spi_flash espcoredump)

target_compile_options(${COMPONENT_LIB} PRIVATE -w)
