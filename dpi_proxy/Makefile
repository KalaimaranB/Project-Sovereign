CC = gcc
CFLAGS = -Wall -Wextra -O3 -std=c99

SRC = dpi_filter_natneg.c dpi_filter_qr.c dpi_proxy.c
OBJ = $(SRC:.c=.o)

MAIN_SRC = main.c
BIN = sovereign_dpi_proxy

TEST_SRC = tests/test_filters.c
TEST_BIN = test_runner

.PHONY: all clean test test_build

all: $(BIN)

$(BIN): $(OBJ)
	$(CC) $(CFLAGS) $(OBJ) $(MAIN_SRC) -o $(BIN)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

test_build: $(OBJ)
	$(CC) $(CFLAGS) $(OBJ) $(TEST_SRC) -o $(TEST_BIN)

test: test_build
	./$(TEST_BIN)

clean:
	rm -f *.o $(TEST_BIN)
