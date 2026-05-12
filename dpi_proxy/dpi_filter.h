#ifndef DPI_FILTER_H
#define DPI_FILTER_H

#include <stddef.h>

/**
 * @brief Unified Interface for Deep Packet Inspection filters.
 * 
 * Satisfies the SOLID Liskov Substitution and Interface Segregation principles.
 */
typedef struct {
    const char *name;
    
    /**
     * @brief Inspects raw binary payload for protocol violations.
     * 
     * @param data The raw UDP packet contents.
     * @param len The size of the packet in bytes.
     * @return 1 if the packet is completely valid and should be forwarded.
     * @return 0 if the packet is malformed, invalid, or abusive (drop).
     */
    int (*inspect)(const unsigned char *data, size_t len);
} dpi_filter_t;

/* Registered protocol filters */
extern const dpi_filter_t dpi_filter_natneg;
extern const dpi_filter_t dpi_filter_qr;

#endif /* DPI_FILTER_H */
