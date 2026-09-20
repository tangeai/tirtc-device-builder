cmake_minimum_required(VERSION 3.16)

set(_TIRTC_DEFAULT_SDK_DIR
    "${CMAKE_CURRENT_LIST_DIR}/../sdk/espressif-esp32s3/2.5.0")

if(NOT DEFINED TIRTC_SDK_DIR OR TIRTC_SDK_DIR STREQUAL "")
    if(DEFINED ENV{TIRTC_SDK_DIR} AND NOT "$ENV{TIRTC_SDK_DIR}" STREQUAL "")
        set(TIRTC_SDK_DIR "$ENV{TIRTC_SDK_DIR}")
    else()
        set(TIRTC_SDK_DIR "${_TIRTC_DEFAULT_SDK_DIR}")
    endif()
endif()

get_filename_component(TIRTC_SDK_DIR "${TIRTC_SDK_DIR}" ABSOLUTE
                       BASE_DIR "${CMAKE_CURRENT_LIST_DIR}")
set(TIRTC_SDK_DIR "${TIRTC_SDK_DIR}" CACHE PATH "TiRTC SDK root" FORCE)

if(NOT DEFINED DEVICE_MEDIA_DIR OR DEVICE_MEDIA_DIR STREQUAL "")
    set(DEVICE_MEDIA_DIR "${CMAKE_CURRENT_LIST_DIR}/media")
endif()
get_filename_component(DEVICE_MEDIA_DIR "${DEVICE_MEDIA_DIR}" ABSOLUTE
                       BASE_DIR "${CMAKE_CURRENT_LIST_DIR}")
if(NOT EXISTS "${DEVICE_MEDIA_DIR}/media_profile.json")
    message(FATAL_ERROR "DEVICE_MEDIA_DIR has no media_profile.json: ${DEVICE_MEDIA_DIR}")
endif()
set(DEVICE_MEDIA_DIR "${DEVICE_MEDIA_DIR}" CACHE PATH "Media profile directory" FORCE)
message(STATUS "Device media directory: ${DEVICE_MEDIA_DIR}")

set(EXTRA_COMPONENT_DIRS
    "${CMAKE_CURRENT_LIST_DIR}/../common/device_core"
)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(device_sim_esp32)

spiffs_create_partition_image(media "${DEVICE_MEDIA_DIR}" FLASH_IN_PROJECT)
