# Headless Apex server (no Qt GUI).
# Build context = this repo; the Apex source comes from the named context "apex"
# (docker-compose.yml sets it from APEX_DIR, default ../Apex-SAPIENT-Middleware).
FROM python:3.11-slim
WORKDIR /apex
COPY --from=apex requirements.txt .
# The lock file's hashes cover Windows/x86 wheels only for some packages, so install by version.
RUN sed -e 's/ *\\$//' -e '/--hash/d' requirements.txt > req.txt \
 && pip install --no-cache-dir -r req.txt
COPY --from=apex pyproject.toml readme.md ./
COPY --from=apex sapient_apex_api sapient_apex_api
COPY --from=apex sapient_apex_server sapient_apex_server
COPY --from=apex sapient_apex_replay sapient_apex_replay
COPY --from=apex sapient_apex_gui sapient_apex_gui
COPY --from=apex sapient_apex_qt_helpers sapient_apex_qt_helpers
COPY --from=apex sapient_msg sapient_msg
RUN pip install --no-cache-dir --no-deps .
# Default config; docker-compose.yml mounts apex_config.json over it.
COPY apex_config.json /config/apex_config.json
# 5000-5004, 5010, 5020: SAPIENT TCP ports; 8080: REST API
EXPOSE 5000 5001 5002 5003 5004 5010 5020 8080
VOLUME /apex/data
CMD ["apex", "/config/apex_config.json"]
