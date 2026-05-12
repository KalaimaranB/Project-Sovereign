#include "dpi_proxy.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_ARGS_PAIRS 10

static void print_usage(const char *prog) {
    printf("Project Sovereign DPI Proxy Daemon\n");
    printf("Usage: %s [public_port] [backend_host] [backend_port] [protocol] ...\n", prog);
    printf("Valid protocols: 'qr', 'natneg'\n");
    printf("Example: %s 27900 127.0.0.1 37900 qr 27901 127.0.0.1 37901 natneg\n", prog);
}

int main(int argc, char *argv[]) {
    proxy_config_t configs[MAX_ARGS_PAIRS];
    size_t count = 0;

    /* We now require 4 parameters per mapping rule (+1 for binary path) */
    if (argc > 1 && (argc - 1) % 4 != 0) {
        print_usage(argv[0]);
        return 1;
    }

    if (argc == 1) {
        /* Default Standard Loopback Topology Mapping */
        configs[0].name = "GS-QR";
        configs[0].public_port = 27900;
        configs[0].backend_host = "127.0.0.1";
        configs[0].backend_port = 37900;
        configs[0].filter = &dpi_filter_qr;

        configs[1].name = "GS-NATNEG";
        configs[1].public_port = 27901;
        configs[1].backend_host = "127.0.0.1";
        configs[1].backend_port = 37901;
        configs[1].filter = &dpi_filter_natneg;
        
        count = 2;
    } else {
        /* Custom 4-Parameter Parsing Loop */
        for (int i = 1; i < argc; i += 4) {
            if (count >= MAX_ARGS_PAIRS) break;

            int pub = atoi(argv[i]);
            const char *host = argv[i+1];
            int back = atoi(argv[i+2]);
            const char *proto = argv[i+3];

            const dpi_filter_t *target_filter = NULL;
            const char *name_tag = "CUSTOM";

            if (strcmp(proto, "qr") == 0) {
                target_filter = &dpi_filter_qr;
                name_tag = "GS-QR";
            } else if (strcmp(proto, "natneg") == 0) {
                target_filter = &dpi_filter_natneg;
                name_tag = "GS-NATNEG";
            } else {
                fprintf(stderr, "Error: Unknown protocol '%s'. Must be 'qr' or 'natneg'.\n", proto);
                return 1;
            }

            configs[count].name = name_tag;
            configs[count].public_port = pub;
            configs[count].backend_host = host;
            configs[count].backend_port = back;
            configs[count].filter = target_filter;
            count++;
        }
    }

    printf("🚀 Project Sovereign WAF Edge Daemon starting...\n");
    return run_proxy(configs, count);
}
