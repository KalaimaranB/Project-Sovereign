#include "dpi_filter.h"
#include <string.h>

#define NATNEG_MIN_LEN 8
#define NATNEG_MAGIC_LEN 6

static const unsigned char NATNEG_MAGIC[NATNEG_MAGIC_LEN] = {
    0xFD, 0xFC, 0x1E, 0x66, 0x6A, 0xB2
};

/**
 * @brief Verifies standard GameSpy NAT Negotiation binary packet structure.
 */
static int inspect_natneg(const unsigned char *data, size_t len) {
    /* 1. Bounds validation */
    if (len < NATNEG_MIN_LEN) {
        return 0;
    }

    /* 2. Magic byte sequence validation */
    if (memcmp(data, NATNEG_MAGIC, NATNEG_MAGIC_LEN) != 0) {
        return 0;
    }

    /* 3. Opcode range validation */
    unsigned char opcode = data[7];
    if (opcode > 0x10) {
        return 0;
    }

    /* Clean packet passed all validation hooks */
    return 1;
}

const dpi_filter_t dpi_filter_natneg = {
    .name = "NATNEG",
    .inspect = inspect_natneg
};
