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

# api <method> <path> [json-body]: body to $WORK/resp, status to $STATUS
STATUS=""
api() {
  local method="$1" path="$2" body="${3:-}"
  if [ -n "$body" ]; then
    STATUS="$(curl -s -o "$WORK/resp" -w '%{http_code}' -X "$method" -H "@$WORK/auth.hdr" \
      -H 'Content-Type: application/json' --data-binary "$body" "$PORTAL$path")" || STATUS="000"
  else
    STATUS="$(curl -s -o "$WORK/resp" -w '%{http_code}' -X "$method" -H "@$WORK/auth.hdr" "$PORTAL$path")" || STATUS="000"
  fi
}

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

cn_of() {
  openssl x509 -in "$1" -noout -subject -nameopt RFC2253 2>/dev/null | sed -n 's/.*CN=\([^,\/]*\).*/\1/p'
}

# 2. list the machines
api GET /api/machines
[ "$STATUS" = "200" ] || die "listing machines failed: HTTP $STATUS, code $(errcode)"
python3 -I -c '
import json, sys
for m in json.load(open(sys.argv[1])).get("machines", []):
    print(m.get("system_handle", ""), m.get("slot_id", ""))
' "$WORK/resp" > "$WORK/machines.txt" || die "cannot read the machine list"

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
[ "$BAD" = 0 ] || exit 1

# 4. the grant, only when something is to be enrolled
if [ -n "$TODO" ]; then
  api GET "/api/machines/grant/$CUSTODIAN"
  if [ "$STATUS" = "200" ]; then
    :
  elif [ "$STATUS" = "404" ] && [ "$(errcode)" = "no_grant" ]; then
    api POST /api/machines/grant "$(python3 -I -c '
import json, sys
print(json.dumps({"custodian": sys.argv[1], "quota": int(sys.argv[2]), "affiliation": sys.argv[3]}))
' "$CUSTODIAN" "$QUOTA" "$AFFILIATION")"
    [ "$STATUS" = "200" ] || die "setting the grant failed: HTTP $STATUS, code $(errcode)"
  else
    die "reading the grant failed: HTTP $STATUS, code $(errcode)"
  fi
fi

# 5. enrol the missing handles
mkdir -p "$OUT/pki" || die "cannot create $OUT/pki"
CA_DONE=0
while IFS=: read -r handle stem class autonomy var; do
  case "$TODO " in *" $handle "*) ;; *) continue ;; esac
  body="$(python3 -I -c '
import json, sys
print(json.dumps({"machine_handle": sys.argv[1], "node_class": sys.argv[2], "autonomy": sys.argv[3], "custodian": sys.argv[4]}))
' "$handle" "$class" "$autonomy" "$CUSTODIAN")"
  api POST /api/machines/enroll "$body"
  [ "$STATUS" = "200" ] || die "$handle: enrolment refused: HTTP $STATUS, code $(errcode)"
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
  code="$(curl -s -o "$WORK/bundle.tgz" -w '%{http_code}' "$PORTAL$burl")" || code="000"
  burl=""
  [ "$code" = "200" ] || die "$handle: enrolled as $anchor, but the bundle download failed: HTTP $code"
  tar -xzf "$WORK/bundle.tgz" -C "$stage" 2>/dev/null || die "$handle: enrolled as $anchor, but the bundle is not a readable tar.gz"
  rm -f "$WORK/bundle.tgz"
  [ -s "$stage/$anchor-cert.pem" ] || die "$handle: enrolled as $anchor, but the bundle has no $anchor-cert.pem"
  [ -s "$stage/$anchor-key.pem" ] || die "$handle: enrolled as $anchor, but the bundle has no $anchor-key.pem"
  root=""
  for f in "$stage"/*.pem; do
    [ -f "$f" ] || continue
    case "$(basename "$f")" in "$anchor-cert.pem"|"$anchor-key.pem") ;; *) root="$f"; break ;; esac
  done
  [ -n "$root" ] || die "$handle: enrolled as $anchor, but the bundle has no root certificate"
  [ "$(cn_of "$stage/$anchor-cert.pem")" = "$anchor" ] || die "$handle: enrolled as $anchor, but the certificate's common name differs"

  cp "$stage/$anchor-key.pem" "$OUT/pki/$stem.key" && chmod 600 "$OUT/pki/$stem.key" \
    && cp "$stage/$anchor-cert.pem" "$OUT/pki/$stem.pem" || die "$handle: cannot write files below $OUT/pki"
  if [ "$CA_DONE" = 0 ]; then
    cp "$root" "$OUT/pki/ca.pem" || die "cannot write $OUT/pki/ca.pem"
    CA_DONE=1
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
