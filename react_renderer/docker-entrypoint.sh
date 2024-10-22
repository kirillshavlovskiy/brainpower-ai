#!/bin/bash
set -e

# Function to clean up Node processes
cleanup() {
    echo "Cleaning up..."
    pkill -f "node" || true
}

# Setup cleanup on script exit
trap cleanup EXIT

# Function to retry commands
retry() {
    local n=0
    local max=5
    local delay=15
    while true; do
        "$@" && break || {
            if [[ $n -lt $max ]]; then
                ((n++))
                echo "Command failed. Attempt $n/$max:"
                sleep $delay;
            else
                echo "The command has failed after $n attempts."
                return 1
            fi
        }
    done
}

# Initialize container
echo "Initializing container..."
rm -f package-lock.json yarn.lock
retry yarn install

# Start the application
echo "Starting application..."
exec "$@"