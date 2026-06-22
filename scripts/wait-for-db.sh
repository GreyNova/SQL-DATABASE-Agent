#!/bin/bash
# Waits until a TCP host:port accepts connections. Used in compose `command`.
set -e
host="$1"
port="$2"
for i in $(seq 1 30); do
    if pg_isready -h "$host" -p "$port" -U postgres >/dev/null 2>&1; then
        echo "✓ $host:$port is ready."
        exit 0
    fi
    echo "… waiting for $host:$port ($i/30)"
    sleep 2
done
echo "✗ $host:$port not reachable after 60s."
exit 1
