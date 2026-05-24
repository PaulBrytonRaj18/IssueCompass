#!/bin/sh
set -eu

usage() {
    cat <<EOF
Usage: $(basename "$0") <encrypt|decrypt>

Encrypt or decrypt .env files using GPG.
Uses symmetric encryption (AES256) with a password.

Examples:
  ./scripts/encrypt-env.sh encrypt   # encrypts .env -> .env.gpg
  ./scripts/encrypt-env.sh decrypt   # decrypts .env.gpg -> .env

The script operates on the .env file in the project root directory.
EOF
    exit 1
}

CMD="${1:-}"
[ -z "$CMD" ] && usage

DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$DIR/.env"
ENV_GPG="$DIR/.env.gpg"

case "$CMD" in
encrypt)
    if [ ! -f "$ENV_FILE" ]; then
        echo "Error: $ENV_FILE not found"
        exit 1
    fi
    gpg --symmetric --cipher-algo AES256 --output "$ENV_GPG" "$ENV_FILE"
    echo "Encrypted -> $ENV_GPG"
    ;;
decrypt)
    if [ ! -f "$ENV_GPG" ]; then
        echo "Error: $ENV_GPG not found"
        exit 1
    fi
    gpg --decrypt --output "$ENV_FILE" "$ENV_GPG"
    echo "Decrypted -> $ENV_FILE"
    ;;
*)
    usage
    ;;
esac
