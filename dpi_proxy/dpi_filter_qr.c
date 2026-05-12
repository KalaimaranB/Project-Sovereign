#include "dpi_filter.h"
#include <ctype.h>

/**
 * @brief Deep Packet Inspection for the GameSpy Query & Reporting (QR) protocol.
 * 
 * Verifies opcode boundaries and validates that string-heavy Heartbeat payloads
 * are properly null-terminated and contain only printable ASCII vectors.
 */
static int inspect_qr(const unsigned char *data, size_t len) {
    if (len < 1) {
        return 0; /* Dropped: Empty payload */
    }

    unsigned char opcode = data[0];
    
    /* Valid GameSpy Client Opcodes: 0x00 (Query) through 0x09 (Available Check) */
    if (opcode > 0x09) {
        return 0;
    }

    /* Availability (0x09) probes can omit session IDs, others require at least session (4 bytes) */
    if (opcode != 0x09) {
        if (len < 5) {
            return 0; /* Payload too short to contain session ID header */
        }
    }

    /* Target Vector: Heartbeat (0x03) key-value payload string inspection */
    if (opcode == 0x03) {
        size_t payload_len = len - 5;
        if (payload_len == 0) {
            return 1; /* Valid empty payload */
        }

        const unsigned char *payload = data + 5;
        int found_null = 0;

        for (size_t i = 0; i < payload_len; i++) {
            unsigned char c = payload[i];
            if (c == '\0') {
                found_null = 1;
            } else {
                /* Enforce strictly readable, printable ASCII or whitespace. */
                if (!isprint(c) && !isspace(c)) {
                    return 0; /* Drop: non-printable binary injections */
                }
            }
        }

        /* All Heartbeats must contain at least one Null delimiter separating keys */
        if (!found_null) {
            return 0; /* Drop: Un-terminated malicious payload sequence */
        }

    } else if (opcode == 0x09) {
        /* Availability check payload is a standard Null-Terminated gamename string */
        if (len < 6) {
            return 0;
        }

        const unsigned char *payload = data + 5;
        size_t payload_len = len - 5;
        int found_null = 0;

        for (size_t i = 0; i < payload_len; i++) {
            unsigned char c = payload[i];
            if (c == '\0') {
                found_null = 1;
                break; /* Clean break upon termination */
            }
            if (!isprint(c) && !isspace(c)) {
                return 0;
            }
        }

        if (!found_null) {
            return 0; /* Must contain terminating Null byte */
        }
    }

    /* Valid state verified */
    return 1;
}

const dpi_filter_t dpi_filter_qr = {
    .name = "QR",
    .inspect = inspect_qr
};
