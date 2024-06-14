cmake_minimum_required(VERSION 3.20)
project(test_package LANGUAGES C CXX)

find_package(Simd REQUIRED CONFIG)

# set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreaded)
add_executable(${PROJECT_NAME} test_package.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE Simd::Simd)
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_17)
