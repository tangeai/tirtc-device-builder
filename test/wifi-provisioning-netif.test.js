import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const WIFI_MANAGER = join(
  ROOT,
  "kit-src/device-sim/device-sim-esp32/components/wifi_manager/src/wifi_manager.c",
);

test("provisioning IP setup handles every DHCP server state", {
  skip: process.platform === "win32" ? "requires a POSIX C compiler" : false,
}, () => {
  const source = readFileSync(WIFI_MANAGER, "utf8");
  const start = source.indexOf("static esp_err_t configure_provisioning_netif(");
  const end = source.indexOf("\nstatic esp_err_t start_provisioning(", start);
  assert.ok(start >= 0 && end > start, "provisioning function must exist");
  const functionSource = source.slice(start, end);

  const harness = `
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

typedef int esp_err_t;
typedef enum {
    ESP_NETIF_DHCP_INIT,
    ESP_NETIF_DHCP_STARTED,
    ESP_NETIF_DHCP_STOPPED
} esp_netif_dhcp_status_t;
typedef struct { int addr; } esp_ip4_addr_t;
typedef struct {
    esp_ip4_addr_t ip;
    esp_ip4_addr_t gw;
    esp_ip4_addr_t netmask;
} esp_netif_ip_info_t;
typedef struct {
    uint8_t type;
    union { esp_ip4_addr_t ip4; } u_addr;
} esp_ip_addr_t;
typedef struct {
    esp_ip_addr_t ip;
} esp_netif_dns_info_t;
typedef struct {
    esp_netif_dhcp_status_t status;
    int stop_calls;
    int set_calls;
    int start_calls;
    int dns_calls;
    int option_calls;
} esp_netif_t;

#define ESP_OK 0
#define ESP_ERR_INVALID_ARG 0x102
#define ESP_ERR_ESP_NETIF_DHCP_NOT_STOPPED 0x5007
#define ESP_IPADDR_TYPE_V4 0
#define ESP_NETIF_DNS_MAIN 0
#define ESP_NETIF_OP_SET 1
#define ESP_NETIF_DOMAIN_NAME_SERVER 6
#define WIFI_SETUP_IP_A 192
#define WIFI_SETUP_IP_B 168
#define WIFI_SETUP_IP_C 6
#define WIFI_SETUP_IP_D 1

static esp_err_t esp_netif_dhcps_get_status(esp_netif_t *netif,
                                            esp_netif_dhcp_status_t *status)
{
    *status = netif->status;
    return ESP_OK;
}

static esp_err_t esp_netif_dhcps_stop(esp_netif_t *netif)
{
    netif->stop_calls++;
    if (netif->status == ESP_NETIF_DHCP_STOPPED) return 0x5006;
    netif->status = ESP_NETIF_DHCP_STOPPED;
    return ESP_OK;
}

static void esp_netif_set_ip4_addr(esp_ip4_addr_t *addr, int a, int b, int c, int d)
{
    addr->addr = (a << 24) | (b << 16) | (c << 8) | d;
}

static esp_err_t esp_netif_set_ip_info(esp_netif_t *netif,
                                      const esp_netif_ip_info_t *info)
{
    netif->set_calls++;
    if (netif->status != ESP_NETIF_DHCP_STOPPED) {
        return ESP_ERR_ESP_NETIF_DHCP_NOT_STOPPED;
    }
    if (info->ip.addr != ((192 << 24) | (168 << 16) | (6 << 8) | 1)) {
        return ESP_ERR_INVALID_ARG;
    }
    return ESP_OK;
}

static esp_err_t esp_netif_set_dns_info(esp_netif_t *netif,
                                        int slot,
                                        const esp_netif_dns_info_t *dns)
{
    netif->dns_calls++;
    if (slot != ESP_NETIF_DNS_MAIN) return ESP_ERR_INVALID_ARG;
    if (dns->ip.type != ESP_IPADDR_TYPE_V4) return ESP_ERR_INVALID_ARG;
    if (dns->ip.u_addr.ip4.addr != ((192 << 24) | (168 << 16) | (6 << 8) | 1)) {
        return ESP_ERR_INVALID_ARG;
    }
    return ESP_OK;
}

static esp_err_t esp_netif_dhcps_option(esp_netif_t *netif,
                                        int op,
                                        int option_id,
                                        const void *data,
                                        int len)
{
    netif->option_calls++;
    if (op != ESP_NETIF_OP_SET || option_id != ESP_NETIF_DOMAIN_NAME_SERVER) {
        return ESP_ERR_INVALID_ARG;
    }
    if (data == NULL || len != 1 || *(const uint8_t *)data != 1) {
        return ESP_ERR_INVALID_ARG;
    }
    return ESP_OK;
}

static esp_err_t esp_netif_dhcps_start(esp_netif_t *netif)
{
    netif->start_calls++;
    netif->status = ESP_NETIF_DHCP_INIT;
    return ESP_OK;
}

${functionSource}

static int check_state(esp_netif_dhcp_status_t initial, int expected_stops)
{
    esp_netif_t netif = { .status = initial };
    esp_err_t result = configure_provisioning_netif(&netif);
    if (result != ESP_OK || netif.stop_calls != expected_stops ||
        netif.set_calls != 1 || netif.start_calls != 1 ||
        netif.dns_calls != 1 || netif.option_calls != 1 ||
        netif.status != ESP_NETIF_DHCP_INIT) {
        fprintf(stderr,
                "state=%d result=0x%x stops=%d sets=%d starts=%d dns=%d option=%d final=%d\\n",
                initial, result, netif.stop_calls, netif.set_calls,
                netif.start_calls, netif.dns_calls, netif.option_calls,
                netif.status);
        return 1;
    }
    return 0;
}

int main(void)
{
    if (check_state(ESP_NETIF_DHCP_INIT, 1)) return 1;
    if (check_state(ESP_NETIF_DHCP_STARTED, 1)) return 1;
    if (check_state(ESP_NETIF_DHCP_STOPPED, 0)) return 1;
    if (configure_provisioning_netif(NULL) != ESP_ERR_INVALID_ARG) return 1;
    return 0;
}
`;

  const temporary = mkdtempSync(join(tmpdir(), "tirtc-dhcp-regression-"));
  try {
    const harnessPath = join(temporary, "dhcp-repro.c");
    const executable = join(temporary, "dhcp-repro");
    writeFileSync(harnessPath, harness);
    const compile = spawnSync(
      "cc",
      ["-std=c11", "-Wall", "-Wextra", "-Werror", harnessPath, "-o", executable],
      { encoding: "utf8" },
    );
    assert.equal(compile.status, 0, compile.stderr);
    const run = spawnSync(executable, [], { encoding: "utf8" });
    assert.equal(run.status, 0, run.stderr);
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
});
