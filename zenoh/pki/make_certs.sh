#!/bin/sh
# Create a local CA and one key and CA-signed certificate per pod 1 identity.
# Usage: make_certs.sh OUT_DIR
# Writes ca.pem, ca.key, and <name>.pem, <name>.key for each name below, with CN and SAN DNS = name.
# Safe to re-run: valid files are kept, and only a missing, expired or foreign certificate is reissued.
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: $0 OUT_DIR" >&2
    exit 2
fi
out=$1

NAMES="router.p1.h1 fusion.p1.h1 radar.p1.h1 camera.p1.h1 vehicle.p1.h1 recorder.p1.h1 bridge.p1.h1"
CA_DAYS=3650
CERT_DAYS=825

mkdir -p "$out"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

new_key() {
    (umask 077; openssl genrsa -out "$1" 2048 2>/dev/null)
}

cert_is_valid() {
    # openssl verify rejects a certificate that is expired or not issued by this CA.
    [ -f "$out/$1.key" ] && [ -f "$out/$1.pem" ] &&
        openssl verify -CAfile "$out/ca.pem" "$out/$1.pem" >/dev/null 2>&1
}

# A missing or expiring CA is replaced; certificates it had issued then fail
# cert_is_valid below and are reissued.
if ! { [ -f "$out/ca.key" ] && [ -f "$out/ca.pem" ] &&
    openssl x509 -checkend 86400 -noout -in "$out/ca.pem" >/dev/null 2>&1; }; then
    cat >"$work/ca.cnf" <<CNF
[req]
distinguished_name = dn
prompt = no
x509_extensions = v3
[dn]
CN = apex-sapient-local-ca
[v3]
basicConstraints = critical, CA:TRUE
keyUsage = critical, keyCertSign, cRLSign
subjectKeyIdentifier = hash
CNF
    new_key "$out/ca.key"
    openssl req -x509 -new -sha256 -days "$CA_DAYS" -key "$out/ca.key" \
        -config "$work/ca.cnf" -out "$out/ca.pem"
fi

for name in $NAMES; do
    cert_is_valid "$name" && continue
    cat >"$work/$name.cnf" <<CNF
[req]
distinguished_name = dn
prompt = no
[dn]
CN = $name
[v3]
basicConstraints = critical, CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth
subjectAltName = DNS:$name
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid
CNF
    new_key "$out/$name.key"
    openssl req -new -sha256 -key "$out/$name.key" -config "$work/$name.cnf" -out "$work/$name.csr"
    openssl x509 -req -sha256 -days "$CERT_DAYS" -in "$work/$name.csr" \
        -CA "$out/ca.pem" -CAkey "$out/ca.key" -set_serial "0x$(openssl rand -hex 16)" \
        -extfile "$work/$name.cnf" -extensions v3 -out "$out/$name.pem" 2>/dev/null
done

echo "certificates in $out"
