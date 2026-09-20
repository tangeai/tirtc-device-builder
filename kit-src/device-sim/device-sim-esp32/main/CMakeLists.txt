idf_component_register(
    SRCS "app_main.c"
    INCLUDE_DIRS "."
    PRIV_REQUIRES device_console nvs_flash esp_system device_core media_runtime
                  platform_client runtime_config session_runtime tirtc_adapter wifi_manager
)
