cmake_minimum_required(VERSION 3.16)

project(DreamCLI VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(DREAMCLI_LIB_SOURCES
    "${CMAKE_CURRENT_SOURCE_DIR}/src/environment.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/interpreter.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/lexer.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/parser.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/token.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/value.cpp"
)

file(GLOB DREAMCLI_COMMAND_SOURCES CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/src/commands/*.cpp"
)

add_library(dreamcli_lib STATIC
    ${DREAMCLI_LIB_SOURCES}
    ${DREAMCLI_COMMAND_SOURCES}
)

target_include_directories(dreamcli_lib PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_options(dreamcli_lib PRIVATE -Wall -Wextra -Wpedantic)

add_executable(dscript src/main.cpp)

target_link_libraries(dscript PRIVATE dreamcli_lib)

target_compile_options(dscript PRIVATE -Wall -Wextra -Wpedantic)
