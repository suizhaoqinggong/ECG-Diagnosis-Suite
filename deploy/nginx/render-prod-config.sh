#!/bin/sh

set -eu

template="/etc/nginx/templates/default.conf.template"

case "${ENABLE_TLS:-False}" in
  True|true|1)
    : "${TLS_CERT_FILENAME:?TLS_CERT_FILENAME is required when ENABLE_TLS=true}"
    : "${TLS_KEY_FILENAME:?TLS_KEY_FILENAME is required when ENABLE_TLS=true}"

    if [ ! -f "/etc/nginx/certs/${TLS_CERT_FILENAME}" ]; then
      echo "Missing TLS certificate: /etc/nginx/certs/${TLS_CERT_FILENAME}" >&2
      exit 1
    fi

    if [ ! -f "/etc/nginx/certs/${TLS_KEY_FILENAME}" ]; then
      echo "Missing TLS private key: /etc/nginx/certs/${TLS_KEY_FILENAME}" >&2
      exit 1
    fi

    template="/etc/nginx/templates/default.tls.conf.template"
    ;;
esac

envsubst '$APP_DOMAIN $CLIENT_MAX_BODY_SIZE $TLS_CERT_FILENAME $TLS_KEY_FILENAME' \
  < "$template" \
  > /etc/nginx/conf.d/default.conf
