#ifndef DPI_PROXY_H
#define DPI_PROXY_H

#include "dpi_filter.h"
#include <arpa/inet.h>

#define MAX_PACKET_SIZE 4096
#define SOV_HEADER_MAGIC "SOV\x01"
#define SOV_HEADER_MAGIC_LEN 4
#define SOV_HEADER_LEN 10 /* SOV\x01 (4) + IP (4) + PORT (2) */

/**
 * @brief Multi-Port routing mapping for a single microservice proxy target.
 */
typedef struct {
    const char *name;
    int public_port;             /* The public port opened to the internet */
    const char *backend_host;    /* Dynamic hostname / IP string of python server */
    int backend_port;            /* The internal port where the python server runs */
    const dpi_filter_t *filter;  /* Protocol-specific DPI rule registry */
    
    /* Cached runtime resolved vector to avoid UDP DNS storms */
    struct in_addr resolved_addr;
} proxy_config_t;

/**
 * @brief Single-Threaded Multiplexing Event Loop handler.
 * 
 * Satisfies Single Responsibility for standard IO socket primitives.
 */
int run_proxy(proxy_config_t *configs, size_t count);

#endif /* DPI_PROXY_H */
