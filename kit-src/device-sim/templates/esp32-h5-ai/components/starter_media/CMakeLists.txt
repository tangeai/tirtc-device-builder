idf_component_register(
    SRCS "src/starter_media.c"
    INCLUDE_DIRS "include"
    REQUIRES starter_tirtc
    PRIV_REQUIRES freertos log
)
