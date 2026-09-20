if(NOT DEFINED TIRTC_SDK_DIR OR TIRTC_SDK_DIR STREQUAL "")
    if(DEFINED ENV{TIRTC_SDK_DIR} AND NOT "$ENV{TIRTC_SDK_DIR}" STREQUAL "")
        set(TIRTC_SDK_DIR "$ENV{TIRTC_SDK_DIR}")
    else()
        # IDF evaluates component CMake files once in an early requirements
        # subprocess where project cache variables are not propagated.
        get_filename_component(TIRTC_SDK_DIR
            "${CMAKE_CURRENT_LIST_DIR}/../../../sdk/espressif-esp32s3/2.5.0"
            ABSOLUTE)
    endif()
endif()

set(TIRTC_HEADER "${TIRTC_SDK_DIR}/include/tirtc/tiRTC.h")
set(TIRTC_LIBRARY "${TIRTC_SDK_DIR}/lib/libTiRTC.a")
set(TIRTC_CONTRACT "${TIRTC_SDK_DIR}/manifest/build-contract.env")

foreach(required_file IN ITEMS "${TIRTC_HEADER}" "${TIRTC_LIBRARY}" "${TIRTC_CONTRACT}")
    if(NOT EXISTS "${required_file}")
        message(FATAL_ERROR "Incomplete TiRTC ESP32 SDK, missing: ${required_file}")
    endif()
endforeach()

file(STRINGS "${TIRTC_HEADER}" TIRTC_VERSION_LINES
     REGEX "^#define TIRTC_VERSION_(MAJOR|MINOR|PATCH)")
message(STATUS "TiRTC SDK root: ${TIRTC_SDK_DIR}")
message(STATUS "TiRTC SDK version macros: ${TIRTC_VERSION_LINES}")

idf_component_register(
    INCLUDE_DIRS "${TIRTC_SDK_DIR}/include"
    REQUIRES freertos esp_http_client esp_netif esp_timer hal json lwip mbedtls soc
)

if(CMAKE_BUILD_EARLY_EXPANSION)
    return()
endif()

function(tirtc_read_contract contract_key output_variable)
    file(STRINGS "${TIRTC_CONTRACT}" contract_line REGEX "^${contract_key}=")
    if(contract_line STREQUAL "")
        message(FATAL_ERROR "TiRTC build contract is missing ${contract_key}")
    endif()
    string(REGEX REPLACE "^[^=]+=" "" contract_value "${contract_line}")
    set(${output_variable} "${contract_value}" PARENT_SCOPE)
endfunction()

tirtc_read_contract("CONFIG_FREERTOS_HZ" TIRTC_CONTRACT_FREERTOS_HZ)
tirtc_read_contract("CONFIG_FREERTOS_USE_TRACE_FACILITY" TIRTC_CONTRACT_TRACE)
tirtc_read_contract("CONFIG_FREERTOS_USE_STATS_FORMATTING_FUNCTIONS" TIRTC_CONTRACT_STATS_FORMAT)
tirtc_read_contract("CONFIG_FREERTOS_GENERATE_RUN_TIME_STATS" TIRTC_CONTRACT_RUNTIME_STATS)
tirtc_read_contract("STATIC_SEMAPHORE_T_SIZE" TIRTC_CONTRACT_STATIC_SEMAPHORE_SIZE)

if(NOT "${CONFIG_FREERTOS_HZ}" STREQUAL "${TIRTC_CONTRACT_FREERTOS_HZ}")
    message(FATAL_ERROR
        "TiRTC requires CONFIG_FREERTOS_HZ=${TIRTC_CONTRACT_FREERTOS_HZ}, "
        "project has ${CONFIG_FREERTOS_HZ}")
endif()

if(TIRTC_CONTRACT_TRACE STREQUAL "off" AND CONFIG_FREERTOS_USE_TRACE_FACILITY)
    message(FATAL_ERROR "TiRTC SDK requires CONFIG_FREERTOS_USE_TRACE_FACILITY=n")
endif()
if(TIRTC_CONTRACT_STATS_FORMAT STREQUAL "off" AND CONFIG_FREERTOS_USE_STATS_FORMATTING_FUNCTIONS)
    message(FATAL_ERROR "TiRTC SDK requires CONFIG_FREERTOS_USE_STATS_FORMATTING_FUNCTIONS=n")
endif()
if(TIRTC_CONTRACT_RUNTIME_STATS STREQUAL "off" AND CONFIG_FREERTOS_GENERATE_RUN_TIME_STATS)
    message(FATAL_ERROR "TiRTC SDK requires CONFIG_FREERTOS_GENERATE_RUN_TIME_STATS=n")
endif()

target_compile_definitions(${COMPONENT_LIB} INTERFACE
    TIRTC_SDK_STATIC_SEMAPHORE_SIZE=${TIRTC_CONTRACT_STATIC_SEMAPHORE_SIZE}
)

add_library(tirtc_esp32s3_prebuilt STATIC IMPORTED GLOBAL)
set_target_properties(tirtc_esp32s3_prebuilt PROPERTIES
    IMPORTED_LOCATION "${TIRTC_LIBRARY}"
)

# TiRTC references IDF network/crypto archives and those archives reference one
# another. Keep them in one linker group; otherwise static-library ordering can
# leave lwIP or mbedTLS symbols unresolved.
add_library(tirtc_esp32s3_link_bundle INTERFACE)
target_link_libraries(tirtc_esp32s3_link_bundle INTERFACE
    "-Wl,--start-group"
    tirtc_esp32s3_prebuilt
    $<TARGET_FILE:__idf_lwip>
    $<TARGET_FILE:__idf_mbedtls>
    $<TARGET_FILE:mbedcrypto>
    $<TARGET_FILE:mbedtls>
    $<TARGET_FILE:mbedx509>
    $<TARGET_FILE:everest>
    $<TARGET_FILE:p256m>
    $<TARGET_FILE:__idf_hal>
    $<TARGET_FILE:__idf_soc>
    "-Wl,--end-group"
)

target_link_libraries(${COMPONENT_LIB} INTERFACE tirtc_esp32s3_link_bundle)
