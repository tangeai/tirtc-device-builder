idf_component_register(
    SRCS "src/session_runtime.c"
    INCLUDE_DIRS "include"
    REQUIRES device_core media_runtime platform_client runtime_config tirtc_adapter
    PRIV_REQUIRES json esp_system esp_timer
)
