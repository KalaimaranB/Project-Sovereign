#include "dpi_proxy.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <netdb.h>

static void handle_incoming_packet(int sock, const proxy_config_t *config) {
    unsigned char buffer[MAX_PACKET_SIZE + SOV_HEADER_LEN];
    struct sockaddr_in src_addr;
    socklen_t addr_len = sizeof(src_addr);

    ssize_t len = recvfrom(sock, buffer, sizeof(buffer), 0, (struct sockaddr *)&src_addr, &addr_len);
    if (len <= 0) {
        return;
    }

    /* 1. Identify Source Category comparing to cached resolved IP */
    int is_backend = (src_addr.sin_addr.s_addr == config->resolved_addr.s_addr &&
                      ntohs(src_addr.sin_port) == config->backend_port);

    if (is_backend) {
        /* --- PATH B: BACKEND RESPONSE -> OUTBOUND CLIENT --- */
        if (len < SOV_HEADER_LEN) {
            fprintf(stderr, "[%s] Backend payload too short (%ld bytes)\n", config->name, len);
            return;
        }

        /* Validate STHE Magic */
        if (memcmp(buffer, SOV_HEADER_MAGIC, SOV_HEADER_MAGIC_LEN) != 0) {
            fprintf(stderr, "[%s] Backend payload missing valid SOV magic\n", config->name);
            return;
        }

        /* Parse Target Address Matrix */
        struct sockaddr_in target_addr;
        memset(&target_addr, 0, sizeof(target_addr));
        target_addr.sin_family = AF_INET;
        
        /* Construct IP from Bytes 4-7, Port from Bytes 8-9 */
        memcpy(&target_addr.sin_addr.s_addr, buffer + 4, 4);
        memcpy(&target_addr.sin_port, buffer + 8, 2);

        /* Strip 10-byte STHE header and relay raw payload to Client */
        sendto(sock, buffer + SOV_HEADER_LEN, len - SOV_HEADER_LEN, 0, 
               (struct sockaddr *)&target_addr, sizeof(target_addr));

    } else {
        /* --- PATH A: INBOUND CLIENT -> DEEP PACKET INSPECTION -> BACKEND --- */
        
        /* Execute decoupled Protocol DPI Interface Hook */
        if (config->filter && !config->filter->inspect(buffer, len)) {
            /* DROP Vector engaged! Safe WAF logging. */
            char client_ip[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &src_addr.sin_addr, client_ip, sizeof(client_ip));
            printf("[WAF DROP] %s dropped invalid %s packet from %s:%d (%ld bytes)\n",
                   config->name, config->filter->name, client_ip, ntohs(src_addr.sin_port), len);
            return;
        }

        /* DPI Validated. Construct STHE Header dynamically. */
        unsigned char relay_buffer[MAX_PACKET_SIZE + SOV_HEADER_LEN];
        
        /* Prepend SOV\x01 Header Magic */
        memcpy(relay_buffer, SOV_HEADER_MAGIC, SOV_HEADER_MAGIC_LEN);
        
        /* Prepend Client Source IP (4 bytes) and Port (2 bytes) */
        memcpy(relay_buffer + 4, &src_addr.sin_addr.s_addr, 4);
        memcpy(relay_buffer + 8, &src_addr.sin_port, 2);
        
        /* Append original raw payload */
        if (len > MAX_PACKET_SIZE) {
             len = MAX_PACKET_SIZE; /* Bound check */
        }
        memcpy(relay_buffer + SOV_HEADER_LEN, buffer, len);

        /* Construct Target Loopback Backend sockaddr */
        struct sockaddr_in backend_addr;
        memset(&backend_addr, 0, sizeof(backend_addr));
        backend_addr.sin_family = AF_INET;
        backend_addr.sin_addr = config->resolved_addr;
        backend_addr.sin_port = htons(config->backend_port);

        /* Forward safely wrapped package to Python server */
        sendto(sock, relay_buffer, len + SOV_HEADER_LEN, 0,
               (struct sockaddr *)&backend_addr, sizeof(backend_addr));
    }
}

int run_proxy(proxy_config_t *configs, size_t count) {
    /* Perform Pre-Flight DNS Resolution targeting internal backends */
    for (size_t i = 0; i < count; i++) {
        printf("[%s] Resolving Backend Host '%s'... ", configs[i].name, configs[i].backend_host);
        
        struct hostent *he = gethostbyname(configs[i].backend_host);
        if (he == NULL || he->h_addr_list[0] == NULL) {
            fprintf(stderr, "\n\033[0;31mCRITICAL: Failed to resolve backend host '%s'\033[0m\n", configs[i].backend_host);
            return 1;
        }
        
        /* Populate config registry with resolved IP structure */
        memcpy(&configs[i].resolved_addr, he->h_addr_list[0], sizeof(struct in_addr));
        
        char resolved_ip_str[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &configs[i].resolved_addr, resolved_ip_str, sizeof(resolved_ip_str));
        printf("\033[0;32mResolved to %s\033[0m\n", resolved_ip_str);
    }

    int *socks = malloc(sizeof(int) * count);
    if (!socks) {
        perror("malloc error");
        return 1;
    }

    int max_fd = -1;

    /* Bind Public Listening Sockets */
    for (size_t i = 0; i < count; i++) {
        socks[i] = socket(AF_INET, SOCK_DGRAM, 0);
        if (socks[i] < 0) {
            perror("socket creation error");
            free(socks);
            return 1;
        }

        /* Enable fast port reuse */
        int opt = 1;
        setsockopt(socks[i], SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

        struct sockaddr_in addr;
        memset(&addr, 0, sizeof(addr));
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = INADDR_ANY;
        addr.sin_port = htons(configs[i].public_port);

        if (bind(socks[i], (struct sockaddr *)&addr, sizeof(addr)) < 0) {
            fprintf(stderr, "Bind failure on Public Port %d for %s\n", 
                    configs[i].public_port, configs[i].name);
            perror("bind error");
            free(socks);
            return 1;
        }

        if (socks[i] > max_fd) {
            max_fd = socks[i];
        }

        printf("[%s] Security Perimeter Active: Public Port %d <=> Backend Host %s:%d\n",
               configs[i].name, configs[i].public_port, configs[i].backend_host, configs[i].backend_port);
    }

    /* Standard Unix multiplexing loop */
    fd_set read_fds;
    while (1) {
        FD_ZERO(&read_fds);
        for (size_t i = 0; i < count; i++) {
            FD_SET(socks[i], &read_fds);
        }

        int activity = select(max_fd + 1, &read_fds, NULL, NULL, NULL);
        if (activity < 0) {
            perror("select loop interrupted");
            break;
        }

        for (size_t i = 0; i < count; i++) {
            if (FD_ISSET(socks[i], &read_fds)) {
                handle_incoming_packet(socks[i], &configs[i]);
            }
        }
    }

    for (size_t i = 0; i < count; i++) {
        close(socks[i]);
    }
    free(socks);
    return 0;
}
