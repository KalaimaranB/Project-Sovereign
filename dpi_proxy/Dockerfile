# ============================================
# STAGE 1: Build the Security Binary
# ============================================
FROM alpine:3.19 AS builder

# Install GCC tooling chain
RUN apk add --no-cache gcc musl-dev make

WORKDIR /app

# Copy filter logic, proxy routines, and GNU make configuration
COPY Makefile *.c *.h ./

# Execute strict optimized compilation
RUN make clean && make all

# ============================================
# STAGE 2: Hardened Production Shell
# ============================================
FROM alpine:3.19

WORKDIR /app

# Extract single dynamic binary from builder layer
COPY --from=builder /app/sovereign_dpi_proxy /usr/local/bin/sovereign_dpi_proxy

# Expose GameSpy Public Network Boundaries
EXPOSE 27900/udp
EXPOSE 27901/udp

# Standard entrypoint maps directly to CLI daemon
ENTRYPOINT ["sovereign_dpi_proxy"]
