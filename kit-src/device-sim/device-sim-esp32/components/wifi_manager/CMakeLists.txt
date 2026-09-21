idf_component_register(
    SRCS "src/wifi_manager.c" "src/wifi_captive_dns.c" "src/wifi_history.c"
    INCLUDE_DIRS "include"
    PRIV_INCLUDE_DIRS "src"
    REQUIRES esp_wifi esp_netif esp_event nvs_flash
    PRIV_REQUIRES esp_http_server json esp_system esp_timer lwip
    EMBED_TXTFILES "web/setup.html"
)
