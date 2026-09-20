cmake_minimum_required(VERSION 3.16)

# 生成器把 SDK 复制到 third_party/tirtc，使生成工程可以离开本仓库独立构建。
# 高级用户仍可通过 -DTIRTC_SDK_DIR=<path> 指向另一份兼容 SDK。
set(TIRTC_SDK_DIR "${CMAKE_CURRENT_LIST_DIR}/third_party/tirtc"
    CACHE PATH "TiRTC ESP32-S3 SDK root")

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(@PROJECT_NAME@)
