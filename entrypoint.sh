#!/bin/sh

# Verify .env was mounted (optional)
if [ -z "$DISCORD_TOKEN" ]; then
    echo "ERROR: Environment variables not loaded!"
    echo "Did you forget '--env-file .env'?"
    exit 1
fi

exec "$@"