cmake_minimum_required(VERSION 3.16)
project(DreamStudioProcessManager LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(DreamStudioProcessManager
    src/main.cpp
    src/process.cpp
    src/processor.cpp
    src/system.cpp
)

target_include_directories(DreamStudioProcessManager PRIVATE include)

if(WIN32)
    target_link_libraries(DreamStudioProcessManager PRIVATE psapi pdh)
elseif(UNIX)
    target_link_libraries(DreamStudioProcessManager PRIVATE pthread)
endif()
