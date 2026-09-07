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