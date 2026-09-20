idf_component_register(
    SRCS "src/device_console.c"
    INCLUDE_DIRS "include"
    REQUIRES console platform_client runtime_config session_runtime wifi_manager media_runtime tirtc_adapter
    PRIV_REQUIRES esp_system
)
