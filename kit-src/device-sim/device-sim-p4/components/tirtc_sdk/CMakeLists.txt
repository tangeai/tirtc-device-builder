# The P4 archive lives in the versioned kit SDK tree; generated projects
# materialize it under third_party/tirtc. Both are located through the same
# resolution order: TIRTC_SDK_DIR (CMake/env) > third_party/tirtc > kit SDK.
# Resolve before idf_component_register: the include dirs reference it.
if(NOT DEFINED TIRTC_SDK_DIR OR TIRTC_SDK_DIR STREQUAL "")
    if(DEFINED ENV{TIRTC_SDK_DIR} AND NOT "$ENV{TIRTC_SDK_DIR}" STREQUAL "")
        set(TIRTC_SDK_DIR "$ENV{TIRTC_SDK_DIR}")
    else()
        set(_TIRTC_DEVICE_SIM_SDK "${CMAKE_CURRENT_LIST_DIR}/../../../sdk/espressif-esp32p4/2.5.0")
        set(_TIRTC_THIRD_PARTY_SDK "${CMAKE_CURRENT_LIST_DIR}/../../../third_party/tirtc")
        if(EXISTS "${_TIRTC_THIRD_PARTY_SDK}/lib/libTiRTC.a")
            set(TIRTC_SDK_DIR "${_TIRTC_THIRD_PARTY_SDK}")
        else()
            set(TIRTC_SDK_DIR "${_TIRTC_DEVICE_SIM_SDK}")
        endif()
    endif()
endif()
set(TIRTC_HEADER "${TIRTC_SDK_DIR}/include/tirtc/tiRTC.h")
set(TIRTC_LIBRARY "${TIRTC_SDK_DIR}/lib/libTiRTC.a")
set(TIRTC_CONTRACT "${TIRTC_SDK_DIR}/manifest/build-contract.env")

idf_component_register(
    INCLUDE_DIRS "${TIRTC_SDK_DIR}/include" "include"
    REQUIRES freertos esp_http_client esp_netif esp_timer hal json lwip mbedtls soc
)

if(NOT EXISTS "${TIRTC_LIBRARY}")
    message(FATAL_ERROR "TiRTC static library not found: ${TIRTC_LIBRARY}")
endif()

# TiRTC 2.5.0 P4 package (vendor baseline 9b4e35c7). Not interchangeable with
# the S3 SDK.
if(NOT IDF_TARGET STREQUAL "esp32p4")
    message(FATAL_ERROR "XiaoTai P4 requires the ESP32-P4 target")
endif()
if(NOT IDF_VERSION_MAJOR EQUAL 5 OR NOT IDF_VERSION_MINOR EQUAL 5 OR
   NOT IDF_VERSION_PATCH EQUAL 4)
    message(FATAL_ERROR "The pinned TiRTC P4 baseline requires ESP-IDF 5.5.4")
endif()
if(NOT CONFIG_FREERTOS_HZ EQUAL 1000 OR
   CONFIG_FREERTOS_USE_TRACE_FACILITY OR CONFIG_FREERTOS_GENERATE_RUN_TIME_STATS OR
   CONFIG_FREERTOS_USE_STATS_FORMATTING_FUNCTIONS)
    message(FATAL_ERROR "TiRTC P4 requires 1000 Hz ticks and disabled trace/runtime stats")
endif()
file(SHA256 "${TIRTC_LIBRARY}" TIRTC_LIB_SHA256)
if(NOT TIRTC_LIB_SHA256 STREQUAL
   "9b4e35c7a2cb203fc463417739199429057c8b036936faa11f844c726455301f")
    message(FATAL_ERROR "TiRTC archive differs from the pinned P4 baseline; review its ABI before updating the contract")
endif()

add_library(tirtc_single_prebuilt STATIC IMPORTED)
file(STRINGS "${TIRTC_CONTRACT}" TIRTC_SEMAPHORE_CONTRACT
    REGEX "^STATIC_SEMAPHORE_T_SIZE=[0-9]+$")
if(NOT TIRTC_SEMAPHORE_CONTRACT STREQUAL "STATIC_SEMAPHORE_T_SIZE=84")
    message(FATAL_ERROR "Pinned P4 archive requires an 84-byte StaticSemaphore_t (see the kit SDK README)")
endif()
target_compile_definitions(${COMPONENT_LIB} INTERFACE TIRTC_SDK_STATIC_SEMAPHORE_SIZE=84)
set_target_properties(tirtc_single_prebuilt PROPERTIES IMPORTED_LOCATION "${TIRTC_LIBRARY}")

# libwebrtc_nosctp.a is bundled into libTiRTC.a; the app links this SDK archive only.
add_library(tirtc_link_bundle INTERFACE)
target_link_libraries(tirtc_link_bundle INTERFACE
    "-Wl,--start-group"
    tirtc_single_prebuilt
    $<TARGET_FILE:__idf_lwip>
    $<TARGET_FILE:__idf_mbedtls>
    $<TARGET_FILE:mbedcrypto>
    $<TARGET_FILE:mbedtls>
    $<TARGET_FILE:mbedx509>
    $<TARGET_FILE:everest>
    $<TARGET_FILE:p256m>
    $<TARGET_FILE:__idf_hal>
    $<TARGET_FILE:__idf_soc>
    "-Wl,--end-group")

target_link_libraries(${COMPONENT_LIB} INTERFACE tirtc_link_bundle)
