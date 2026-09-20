#include "device_console.h"

#include <stdio.h>
#include <string.h>

#include "device/device_media.h"
#include "esp_check.h"
#include "esp_console.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "media_runtime.h"
#include "platform_client.h"
#include "runtime_config.h"
#include "session_runtime.h"
#include "tirtc_adapter.h"
#include "wifi_manager.h"

static esp_console_repl_t *s_repl;

static int command_status(int argc, char **argv)
{
    (void)argc;
    (void)argv;
    printf("Wi-Fi: %s", wifi_manager_connected() ? "connected" : "disconnected");
    if (wifi_manager_provisioning()) {
        printf(" (SoftAP %s)", wifi_manager_provisioning_ssid());
    }
    printf("\nTiRTC: state=%d connection=%s\n",
           (int)tirtc_adapter_state(),
           tirtc_adapter_has_connection() ? "active" : "none");
    printf("       audio subscription=%s; video=unsupported\n",
           tirtc_adapter_audio_subscribed() ? "active" : "inactive");
    printf("Platform: api=%s mqtt=%s\n",
           platform_client_ready() ? "ready" : "offline",
           platform_client_mqtt_connected() ? "connected" : "disconnected");
    if (platform_client_provisioning()) {
        printf("Binding: waiting for H5, verification code=%s\n",
               platform_client_verification_code());
    }
    printf("Session: %s service=%s uplink=%s\n",
           device_session_state_name(session_runtime_state()),
           device_service_name(session_runtime_service()),
           media_runtime_uplink_active() ? "active" : "stopped");
    const device_media_config_t *media = media_runtime_config();
    if (media != NULL) {
        printf("Media: audio=%s/%luHz file=%s\n",
               device_audio_codec_name(media->audio.codec),
               (unsigned long)media->audio.sample_rate_hz,
               media->audio.asset_path);
        printf("       video=unsupported\n");
    }
    return 0;
}

static int command_wifi_set(int argc, char **argv)
{
    if (argc != 3) {
        printf("usage: wifi-set <ssid> <password>; use \"\" for an open network\n");
        return 1;
    }
    char error[80];
    if (!wifi_manager_credentials_valid(argv[1], argv[2], error, sizeof(error))) {
        printf("invalid Wi-Fi config: %s\n", error);
        return 1;
    }
    esp_err_t err = wifi_manager_save_credentials(argv[1], argv[2]);
    if (err != ESP_OK) {
        printf("save failed: %s\n", esp_err_to_name(err));
        return 1;
    }
    printf("Wi-Fi config saved; restarting...\n");
    vTaskDelay(pdMS_TO_TICKS(300));
    esp_restart();
    return 0;
}

static int command_wifi_clear(int argc, char **argv)
{
    (void)argc;
    (void)argv;
    esp_err_t err = wifi_manager_forget_credentials();
    if (err != ESP_OK) {
        printf("clear failed: %s\n", esp_err_to_name(err));
        return 1;
    }
    printf("Wi-Fi config cleared; restarting into SoftAP mode...\n");
    vTaskDelay(pdMS_TO_TICKS(300));
    esp_restart();
    return 0;
}

static int command_tirtc_set(int argc, char **argv)
{
    if (argc < 3 || argc > 4) {
        printf("usage: tirtc-set <device_id> <device_secret> [client_id]\n");
        return 1;
    }
    runtime_tirtc_config_t config = {0};
    if (strlen(argv[1]) >= sizeof(config.device_id) ||
        strlen(argv[2]) >= sizeof(config.device_secret) ||
        (argc >= 4 && strlen(argv[3]) >= sizeof(config.client_id))) {
        printf("one or more arguments are too long\n");
        return 1;
    }
    (void)snprintf(config.device_id, sizeof(config.device_id), "%s", argv[1]);
    (void)snprintf(config.device_secret, sizeof(config.device_secret), "%s", argv[2]);
    if (argc >= 4) (void)snprintf(config.client_id, sizeof(config.client_id), "%s", argv[3]);
    esp_err_t err = runtime_config_save_tirtc(&config);
    if (err != ESP_OK) {
        printf("save failed: %s\n", esp_err_to_name(err));
        return 1;
    }
    printf("TiRTC credentials saved (secret not displayed); restarting...\n");
    vTaskDelay(pdMS_TO_TICKS(300));
    esp_restart();
    return 0;
}

static int command_tirtc_clear(int argc, char **argv)
{
    (void)argc;
    (void)argv;
    esp_err_t err = runtime_config_clear_tirtc();
    if (err != ESP_OK) {
        printf("clear failed: %s\n", esp_err_to_name(err));
        return 1;
    }
    printf("TiRTC credentials cleared; restarting...\n");
    vTaskDelay(pdMS_TO_TICKS(300));
    esp_restart();
    return 0;
}

static int command_restart(int argc, char **argv)
{
    (void)argc;
    (void)argv;
    printf("restarting...\n");
    vTaskDelay(pdMS_TO_TICKS(200));
    esp_restart();
    return 0;
}

static int print_session_result(esp_err_t result)
{
    if (result != ESP_OK) {
        printf("command rejected: %s\n", esp_err_to_name(result));
        return 1;
    }
    return 0;
}

static int command_ai_press(int argc, char **argv)
{
    (void)argv;
    if (argc != 1) {
        printf("usage: ai-press\n");
        return 1;
    }
    return print_session_result(session_runtime_ai_press());
}

static int command_ai_release(int argc, char **argv)
{
    (void)argv;
    if (argc != 1) {
        printf("usage: ai-release\n");
        return 1;
    }
    return print_session_result(session_runtime_ai_release());
}

static int command_voip_connect(int argc, char **argv)
{
    if (argc != 3) {
        printf("usage: voip-connect <service_description> <token>\n");
        return 1;
    }
    return print_session_result(session_runtime_voip_connect(argv[1], argv[2]));
}

static int command_voip_call(int argc, char **argv)
{
    (void)argv;
    if (argc != 1) {
        printf("usage: voip-call\n");
        return 1;
    }
    return print_session_result(session_runtime_voip_call_default());
}

static int command_device_call(int argc, char **argv)
{
    (void)argv;
    if (argc != 1) {
        printf("usage: call\n");
        return 1;
    }
    return print_session_result(session_runtime_device_call_default());
}

static int command_device_call_direct(int argc, char **argv)
{
    if (argc != 3) {
        printf("usage: call-direct <remote_device_id> <token>\n");
        return 1;
    }
    return print_session_result(session_runtime_device_call(argv[1], argv[2]));
}

static int command_contacts(int argc, char **argv)
{
    (void)argv;
    if (argc != 1) {
        printf("usage: contacts\n");
        return 1;
    }
    return print_session_result(session_runtime_contacts());
}

static int command_accept(int argc, char **argv)
{
    (void)argc; (void)argv;
    return print_session_result(session_runtime_accept());
}

static int command_reject(int argc, char **argv)
{
    (void)argc; (void)argv;
    return print_session_result(session_runtime_reject());
}

static int command_cancel(int argc, char **argv)
{
    (void)argc; (void)argv;
    return print_session_result(session_runtime_cancel());
}

static int command_hangup(int argc, char **argv)
{
    (void)argc; (void)argv;
    return print_session_result(session_runtime_hangup());
}

static esp_err_t register_command(const char *name,
                                  const char *help,
                                  esp_console_cmd_func_t function)
{
    const esp_console_cmd_t command = {
        .command = name,
        .help = help,
        .func = function,
    };
    return esp_console_cmd_register(&command);
}

esp_err_t device_console_start(void)
{
    if (s_repl != NULL) {
        return ESP_OK;
    }
    ESP_ERROR_CHECK(esp_console_register_help_command());
    ESP_ERROR_CHECK(register_command("status", "Show Wi-Fi, TiRTC and media status", command_status));
    ESP_ERROR_CHECK(register_command("wifi-set", "wifi-set <ssid> <password>", command_wifi_set));
    ESP_ERROR_CHECK(register_command("wifi-clear", "Clear Wi-Fi config and enter SoftAP", command_wifi_clear));
    ESP_ERROR_CHECK(register_command("tirtc-set", "Diagnostic: pre-load device credentials", command_tirtc_set));
    ESP_ERROR_CHECK(register_command("tirtc-clear", "Clear credentials and restart verification binding", command_tirtc_clear));
    ESP_ERROR_CHECK(register_command("ai-press", "Start AI PTT and keep talking", command_ai_press));
    ESP_ERROR_CHECK(register_command("ai-release", "Release AI PTT and end conversation", command_ai_release));
    ESP_ERROR_CHECK(register_command("voip-call", "Call the first authorized VoIP contact", command_voip_call));
    ESP_ERROR_CHECK(register_command("voip-connect", "Low-level VoIP WHIP connect", command_voip_connect));
    ESP_ERROR_CHECK(register_command("contacts", "List device-call contacts", command_contacts));
    ESP_ERROR_CHECK(register_command("call", "Call the first device contact", command_device_call));
    ESP_ERROR_CHECK(register_command("call-direct", "Low-level device P2P diagnostic call", command_device_call_direct));
    ESP_ERROR_CHECK(register_command("accept", "Accept a pending call", command_accept));
    ESP_ERROR_CHECK(register_command("reject", "Reject a pending call", command_reject));
    ESP_ERROR_CHECK(register_command("cancel", "Cancel an outgoing call", command_cancel));
    ESP_ERROR_CHECK(register_command("hangup", "Hang up the active session", command_hangup));
    ESP_ERROR_CHECK(register_command("restart", "Restart the device", command_restart));

    esp_console_repl_config_t repl_config = ESP_CONSOLE_REPL_CONFIG_DEFAULT();
    repl_config.prompt = "tirtc> ";
    repl_config.max_cmdline_length = 512;

#if defined(CONFIG_ESP_CONSOLE_UART_DEFAULT) || defined(CONFIG_ESP_CONSOLE_UART_CUSTOM)
    esp_console_dev_uart_config_t device = ESP_CONSOLE_DEV_UART_CONFIG_DEFAULT();
    ESP_RETURN_ON_ERROR(esp_console_new_repl_uart(&device, &repl_config, &s_repl),
                        "device_console", "create UART REPL");
#elif defined(CONFIG_ESP_CONSOLE_USB_CDC)
    esp_console_dev_usb_cdc_config_t device = ESP_CONSOLE_DEV_CDC_CONFIG_DEFAULT();
    ESP_RETURN_ON_ERROR(esp_console_new_repl_usb_cdc(&device, &repl_config, &s_repl),
                        "device_console", "create USB CDC REPL");
#elif defined(CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG)
    esp_console_dev_usb_serial_jtag_config_t device =
        ESP_CONSOLE_DEV_USB_SERIAL_JTAG_CONFIG_DEFAULT();
    ESP_RETURN_ON_ERROR(esp_console_new_repl_usb_serial_jtag(&device, &repl_config, &s_repl),
                        "device_console", "create USB Serial/JTAG REPL");
#else
#error Unsupported console transport
#endif

    return esp_console_start_repl(s_repl);
}
