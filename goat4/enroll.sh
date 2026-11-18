#!/bin/bash
# Enrol the three step 4 machines at a goatnet portal and write their files.
#   goat4/enroll.sh <secrets-file> [--portal <url>] [--out <dir>]
# Needs: bash 3.2, curl, tar, openssl, python3 (standard library, JSON only).
# The operator key is read from the line CUASLAB_PORTAL_OPERATOR_API_KEY= in the
# secrets file. It reaches curl through a header file, never the command line,
# and is never printed or kept. API keys and bundle tokens are not kept either.
set -u

PORTAL="https://portal.cuaslab.cuaslab.lan"
OUT="zenoh/goat4"
CUSTODIAN="richard@cuaslab.lan"
QUOTA=5
AFFILIATION="cuaslab-lab"
# handle:file-stem:node-class:autonomy:env-variable
MACHINES="pod1-bridge:pod1:POD:remote:FABRIC_POD1_ID
host-fusion:host-fusion:FUSION:supervised:FABRIC_HOST_FUSION_ID
host-recorder:host-recorder:FUSION:supervised:FABRIC_HOST_RECORDER_ID"

die() { echo "enroll.sh: $*" >&2; exit 1; }

SECRETS=""
while [ $# -gt 0 ]; do
  case "$1" in
    --portal) [ $# -ge 2 ] || die "--portal needs a value"; PORTAL="$2"; shift 2 ;;
    --out) [ $# -ge 2 ] || die "--out needs a value"; OUT="$2"; shift 2 ;;
    -*) die "unknown option $1" ;;
    *) [ -z "$SECRETS" ] || die "one secrets file only"; SECRETS="$1"; shift ;;
  esac
done
[ -n "$SECRETS" ] || die "usage: enroll.sh <secrets-file> [--portal <url>] [--out <dir>]"
[ -r "$SECRETS" ] || die "cannot read the secrets file"
PORTAL="${PORTAL%/}"

umask 077
WORK="$(mktemp -d "${TMPDIR:-/tmp}/goat4-enroll.XXXXXX")" || die "no temporary directory"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# 1. the operator key, from one line, into a header file
KEY="$(grep '^[[:space:]]*\(export[[:space:]]\{1,\}\)\{0,1\}CUASLAB_PORTAL_OPERATOR_API_KEY=' "$SECRETS" | tail -n 1 \
  | sed -e 's/^[^=]*=//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e "s/^\"\(.*\)\"\$/\1/" -e "s/^'\(.*\)'\$/\1/")"
[ -n "$KEY" ] || die "no CUASLAB_PORTAL_OPERATOR_API_KEY line with a value in the secrets file"
printf 'Authorization: Bearer %s\n' "$KEY" > "$WORK/auth.hdr"
KEY=""

# curl's own error text is discarded: it could name a URL, and a bundle URL
# carries a token. Only the exit code is reported.
CURL_OPTS="-sS --connect-timeout 10 --max-time 60"

# api <method> <path> [json-body]: body to $WORK/resp, status to $STATUS
STATUS=""
api() {
  local method="$1" path="$2" body="${3:-}" rc
  rm -f "$WORK/resp"
  if [ -n "$body" ]; then
    STATUS="$(curl $CURL_OPTS -o "$WORK/resp" -w '%{http_code}' -X "$method" -H "@$WORK/auth.hdr" \
      -H 'Content-Type: application/json' --data-binary "$body" "$PORTAL$path" 2>/dev/null)"
  else
    STATUS="$(curl $CURL_OPTS -o "$WORK/resp" -w '%{http_code}' -X "$method" -H "@$WORK/auth.hdr" "$PORTAL$path" 2>/dev/null)"
  fi
  rc=$?
  if [ "$rc" != 0 ]; then STATUS="curl-exit-$rc"; fi
  [ -f "$WORK/resp" ] || : > "$WORK/resp"
}

is2xx() { case "$1" in 2[0-9][0-9]) return 0 ;; *) return 1 ;; esac; }

# jget <file> <key>: top-level string field, empty when missing
jget() {
  python3 -I -c '
import json, sys
try:
    v = json.load(open(sys.argv[1])).get(sys.argv[2], "")
except Exception:
    v = ""
print(v if isinstance(v, str) else "")
' "$1" "$2"
}

errcode() { local c; c="$(jget "$WORK/resp" code)"; echo "${c:-none}"; }

fp_of() {
  openssl x509 -in "$1" -noout -fingerprint -sha256 2>/dev/null | sed 's/^.*=//'
}

cn_of() {
  openssl x509 -in "$1" -noout -subject -nameopt RFC2253 2>/dev/null | sed -n 's/.*CN=\([^,\/]*\).*/\1/p'
}

# 2. list the machines
api GET /api/machines
is2xx "$STATUS" || die "listing machines failed: HTTP $STATUS, code $(errcode)"
python3 -I -c '
import json, sys
d = json.load(open(sys.argv[1]))
if not isinstance(d, dict) or not isinstance(d.get("machines"), list):
    sys.exit(1)
for m in d["machines"]:
    print(m.get("system_handle", ""), m.get("slot_id", ""))
' "$WORK/resp" > "$WORK/machines.txt" || die "the machine list has no machines key; nothing was enrolled"

# 3. decide per handle, before anything is written to the portal
TODO=""
ANCHORS="$WORK/anchors.txt"
: > "$ANCHORS"
BAD=0
while IFS=: read -r handle stem class autonomy var; do
  live="$(awk -v h="$handle" '$1 == h { print $2; exit }' "$WORK/machines.txt")"
  have=0
  [ -s "$OUT/pki/$stem.pem" ] && [ -s "$OUT/pki/$stem.key" ] && have=1
  if grep -q "^$handle " "$WORK/machines.txt"; then
    if [ "$have" = 1 ]; then
      cn="$(cn_of "$OUT/pki/$stem.pem")"
      if [ -z "$live" ] || [ "$cn" != "$live" ]; then
        echo "enroll.sh: $handle: the certificate in $OUT/pki/$stem.pem does not match the portal's slot" >&2
        BAD=1
      else
        echo "$handle $live $var" >> "$ANCHORS"
      fi
    else
      echo "enroll.sh: $handle holds a live slot at the portal but its files are missing in $OUT/pki; nothing was enrolled" >&2
      BAD=1
    fi
  else
    TODO="$TODO $handle"
  fi
done <<EOF
$MACHINES
EOF
if [ -s "$ANCHORS" ] && [ ! -s "$OUT/pki/ca.pem" ]; then
  echo "enroll.sh: handles are present but $OUT/pki/ca.pem is missing or empty; nothing was enrolled" >&2
  BAD=1
fi
[ "$BAD" = 0 ] || exit 1

# 4. the grant, only when something is to be enrolled
if [ -n "$TODO" ]; then
  api GET "/api/machines/grant/$CUSTODIAN"
  if is2xx "$STATUS"; then
    :
  elif [ "$STATUS" = "404" ] && [ "$(errcode)" = "no_grant" ]; then
    api POST /api/machines/grant "$(python3 -I -c '
import json, sys
print(json.dumps({"custodian": sys.argv[1], "quota": int(sys.argv[2]), "affiliation": sys.argv[3]}))
' "$CUSTODIAN" "$QUOTA" "$AFFILIATION")"
    is2xx "$STATUS" || die "setting the grant failed: HTTP $STATUS, code $(errcode)"
  else
    die "reading the grant failed: HTTP $STATUS, code $(errcode)"
  fi
fi

# 5. enrol the missing handles
mkdir -p "$OUT/pki" || die "cannot create $OUT/pki"
CA_DONE=0
rc=0
# with a handle already skipped, the existing ca.pem is the root every bundle must match
CA_FP=""
if [ -s "$ANCHORS" ]; then
  CA_FP="$(fp_of "$OUT/pki/ca.pem")"
  [ -n "$CA_FP" ] || die "$OUT/pki/ca.pem is not a readable certificate"
  CA_DONE=1
fi
while IFS=: read -r handle stem class autonomy var; do
  case "$TODO " in *" $handle "*) ;; *) continue ;; esac
  body="$(python3 -I -c '
import json, sys
print(json.dumps({"machine_handle": sys.argv[1], "node_class": sys.argv[2], "autonomy": sys.argv[3], "custodian": sys.argv[4]}))
' "$handle" "$class" "$autonomy" "$CUSTODIAN")"
  api POST /api/machines/enroll "$body"
  is2xx "$STATUS" || die "$handle: enrolment refused: HTTP $STATUS, code $(errcode)"
  anchor="$(jget "$WORK/resp" slot_id)"
  burl="$(jget "$WORK/resp" bundle_url)"
  rm -f "$WORK/resp"
  case "$anchor" in
    [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]) ;;
    *) die "$handle: the portal's slot_id is not 32 lower-case hex characters" ;;
  esac
  case "$burl" in /api/org-bundle/*) ;; *) die "$handle: enrolled as $anchor, but the answer has no usable bundle_url" ;; esac

  stage="$WORK/stage-$stem"
  mkdir -p "$stage"
  code="$(curl $CURL_OPTS -o "$WORK/bundle.tgz" -w '%{http_code}' "$PORTAL$burl" 2>/dev/null)"
  rc=$?
  burl=""
  [ "$rc" = 0 ] || code="curl-exit-$rc"
  [ "$code" = "200" ] || die "$handle: enrolled as $anchor, but the bundle download failed: $code"
  tar -xzf "$WORK/bundle.tgz" -C "$stage" 2>/dev/null || die "$handle: enrolled as $anchor, but the bundle is not a readable tar.gz"
  rm -f "$WORK/bundle.tgz"
  [ -s "$stage/$anchor-cert.pem" ] || die "$handle: enrolled as $anchor, but the bundle has no $anchor-cert.pem"
  [ -s "$stage/$anchor-key.pem" ] || die "$handle: enrolled as $anchor, but the bundle has no $anchor-key.pem"
  [ "$(cn_of "$stage/$anchor-cert.pem")" = "$anchor" ] || die "$handle: enrolled as $anchor, but the certificate's common name differs"

  openssl pkey -in "$stage/$anchor-key.pem" -noout >/dev/null 2>&1 \
    || die "$handle: enrolled as $anchor, but the bundle's key does not parse"
  kpub="$(openssl pkey -in "$stage/$anchor-key.pem" -pubout 2>/dev/null)"
  cpub="$(openssl x509 -in "$stage/$anchor-cert.pem" -pubkey -noout 2>/dev/null)"
  [ -n "$kpub" ] && [ "$kpub" = "$cpub" ] \
    || die "$handle: enrolled as $anchor, but the bundle's key does not match its certificate"
  kpub=""; cpub=""
  # the root: a *.pem other than cert and key that is an X.509 certificate and
  # that the leaf verifies against. Public keys and other files are skipped.
  root=""; nroots=0
  for f in "$stage"/*.pem; do
    [ -f "$f" ] || continue
    case "$(basename "$f")" in "$anchor-cert.pem"|"$anchor-key.pem") continue ;; esac
    openssl x509 -in "$f" -noout >/dev/null 2>&1 || continue
    openssl verify -CAfile "$f" "$stage/$anchor-cert.pem" >/dev/null 2>&1 || continue
    root="$f"; nroots=$((nroots + 1))
  done
  [ "$nroots" -ge 1 ] || die "$handle: enrolled as $anchor, but the bundle has no root certificate that the leaf verifies against"
  [ "$nroots" -le 1 ] || die "$handle: enrolled as $anchor, but the bundle has more than one root certificate candidate"
  rootfp="$(fp_of "$root")"
  [ -n "$rootfp" ] || die "$handle: enrolled as $anchor, but the root certificate cannot be read"
  if [ -n "$CA_FP" ] && [ "$rootfp" != "$CA_FP" ]; then
    die "$handle: enrolled as $anchor, but the bundle's root differs from the one already in use (pki/ca.pem or an earlier bundle)"
  fi

  cp "$stage/$anchor-key.pem" "$OUT/pki/$stem.key" && chmod 600 "$OUT/pki/$stem.key" \
    && cp "$stage/$anchor-cert.pem" "$OUT/pki/$stem.pem" || die "$handle: cannot write files below $OUT/pki"
  if [ "$CA_DONE" = 0 ]; then
    cp "$root" "$OUT/pki/ca.pem" || die "cannot write $OUT/pki/ca.pem"
    CA_DONE=1
    CA_FP="$rootfp"
  fi
  rm -rf "$stage"
  echo "$handle $anchor $var" >> "$ANCHORS"
done <<EOF
$MACHINES
EOF

# 6. goat4.env last, then the report
ENVTMP="$WORK/goat4.env"
: > "$ENVTMP"
while IFS=: read -r handle stem class autonomy var; do
  anchor="$(awk -v h="$handle" '$1 == h { print $2; exit }' "$ANCHORS")"
  [ -n "$anchor" ] || die "$handle: no anchor known"
  echo "$var=$anchor" >> "$ENVTMP"
  echo "$handle $anchor"
done <<EOF
$MACHINES
EOF
cp "$ENVTMP" "$OUT/goat4.env" || die "cannot write $OUT/goat4.env"
echo "wrote $OUT/goat4.env"
