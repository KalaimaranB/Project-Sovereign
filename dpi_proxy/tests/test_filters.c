#include "../dpi_filter.h"
#include <stdio.h>
#include <string.h>

#define RUN_TEST(test_func) \
    do { \
        printf("Running %s... ", #test_func); \
        if (test_func()) { \
            printf("\033[0;32mPASSED\033[0m\n"); \
            passed++; \
        } else { \
            printf("\033[0;31mFAILED\033[0m\n"); \
            failed++; \
        } \
        total++; \
    } while (0)

#define ASSERT_TRUE(cond) \
    do { \
        if (!(cond)) { \
            fprintf(stderr, "Assertion Failed: %s at line %d\n", #cond, __LINE__); \
            return 0; \
        } \
    } while(0)

#define ASSERT_FALSE(cond) \
    do { \
        if (cond) { \
            fprintf(stderr, "Assertion Failed (Expected False): %s at line %d\n", #cond, __LINE__); \
            return 0; \
        } \
    } while(0)

/* Test Vectors: NatNeg */
static int test_natneg_valid_init(void) {
    unsigned char pkt[] = {
        0xFD, 0xFC, 0x1E, 0x66, 0x6A, 0xB2, /* Magic */
        0x00, 0x00, /* Extra + Opcode INIT */
        0x11, 0x22, 0x33, 0x44
    };
    ASSERT_TRUE(dpi_filter_natneg.inspect(pkt, sizeof(pkt)));
    return 1;
}

static int test_natneg_invalid_magic(void) {
    unsigned char pkt[] = {
        0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, /* Corrupt Magic */
        0x00, 0x00,
        0x11, 0x22, 0x33, 0x44
    };
    ASSERT_FALSE(dpi_filter_natneg.inspect(pkt, sizeof(pkt)));
    return 1;
}

static int test_natneg_too_short(void) {
    unsigned char pkt[] = { 0xFD, 0xFC, 0x1E };
    ASSERT_FALSE(dpi_filter_natneg.inspect(pkt, sizeof(pkt)));
    return 1;
}

static int test_natneg_invalid_opcode(void) {
    unsigned char pkt[] = {
        0xFD, 0xFC, 0x1E, 0x66, 0x6A, 0xB2,
        0x00, 0x25, /* Opcode 0x25 exceeds max 0x10 */
        0x11
    };
    ASSERT_FALSE(dpi_filter_natneg.inspect(pkt, sizeof(pkt)));
    return 1;
}

/* Test Vectors: QR */
static int test_qr_valid_heartbeat(void) {
    unsigned char pkt[] = {
        0x03, /* Opcode */
        0x01, 0x02, 0x03, 0x04, /* Session ID */
        'k', 'e', 'y', '\0', 'v', 'a', 'l', '\0'
    };
    ASSERT_TRUE(dpi_filter_qr.inspect(pkt, sizeof(pkt)));
    return 1;
}

static int test_qr_heartbeat_missing_null(void) {
    unsigned char pkt[] = {
        0x03,
        0x01, 0x02, 0x03, 0x04,
        'n', 'o', 'n', 'u', 'l', 'l'
    };
    ASSERT_FALSE(dpi_filter_qr.inspect(pkt, sizeof(pkt)));
    return 1;
}

static int test_qr_heartbeat_binary_injection(void) {
    unsigned char pkt[] = {
        0x03,
        0x01, 0x02, 0x03, 0x04,
        'k', 'e', 'y', 0xFF, 'v', 'a', 'l', '\0' /* Contains 0xFF binary character */
    };
    ASSERT_FALSE(dpi_filter_qr.inspect(pkt, sizeof(pkt)));
    return 1;
}

static int test_qr_valid_availability_probe(void) {
    unsigned char pkt[] = {
        0x09, /* Opcode */
        0x00, 0x00, 0x00, 0x00, /* Leading zeros */
        'm', 'a', 'r', 'i', 'o', 'k', 'a', 'r', 't', '\0'
    };
    ASSERT_TRUE(dpi_filter_qr.inspect(pkt, sizeof(pkt)));
    return 1;
}

static int test_qr_availability_missing_null(void) {
    unsigned char pkt[] = {
        0x09,
        0x00, 0x00, 0x00, 0x00,
        'g', 'a', 'm', 'e' /* Missing Null terminator */
    };
    ASSERT_FALSE(dpi_filter_qr.inspect(pkt, sizeof(pkt)));
    return 1;
}

static int test_qr_invalid_opcode(void) {
    unsigned char pkt[] = {
        0x99, /* Invalid Client Opcode */
        0x01, 0x02
    };
    ASSERT_FALSE(dpi_filter_qr.inspect(pkt, sizeof(pkt)));
    return 1;
}

int main(void) {
    int total = 0;
    int passed = 0;
    int failed = 0;

    printf("========================================\n");
    printf("   EXECUTING C DPI FILTER UNIT TESTS    \n");
    printf("========================================\n");

    /* NatNeg Runners */
    RUN_TEST(test_natneg_valid_init);
    RUN_TEST(test_natneg_invalid_magic);
    RUN_TEST(test_natneg_too_short);
    RUN_TEST(test_natneg_invalid_opcode);

    /* QR Runners */
    RUN_TEST(test_qr_valid_heartbeat);
    RUN_TEST(test_qr_heartbeat_missing_null);
    RUN_TEST(test_qr_heartbeat_binary_injection);
    RUN_TEST(test_qr_valid_availability_probe);
    RUN_TEST(test_qr_availability_missing_null);
    RUN_TEST(test_qr_invalid_opcode);

    printf("========================================\n");
    printf("TEST SUMMARY: %d Total, %d Passed, %d Failed\n", total, passed, failed);
    printf("========================================\n");

    return (failed > 0) ? 1 : 0;
}
