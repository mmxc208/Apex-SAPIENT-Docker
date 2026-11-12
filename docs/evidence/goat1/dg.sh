. <workspace>/Apex-SAPIENT-Docker/.superpowers/sdd/2026-11-11-goat-step1-pod-to-host/docker-env.sh
cd <workspace>/Apex-SAPIENT-Docker
dg() { docker compose --env-file zenoh/goat1/goat1.env -f docker-compose.goat1.yml "$@"; }
