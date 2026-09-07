cmake_minimum_required(VERSION 3.16)

project(binary_inspector
    VERSION 0.1.0
    LANGUAGES C
)

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_library(binary_inspector SHARED
    src/inspector.c
)

target_include_directories(binary_inspector
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

set_target_properties(binary_inspector PROPERTIES
    OUTPUT_NAME "inspector"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../native/build/lib"
    ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../native/build/lib"
    C_VISIBILITY_PRESET default
    VISIBILITY_INLINES_HIDDEN OFF
)

target_compile_options(binary_inspector PRIVATE
    -fPIC -O2 -Wall -Wextra
)