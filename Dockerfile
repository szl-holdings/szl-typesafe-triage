# Copyright 2026 SZL Holdings. SPDX-License-Identifier: Apache-2.0
# Deterministic Python software only: no weights, training scripts or credentials.
FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    TRIAGE_TRUSTED_AUTHORITIES=szlholdings-szl-typesafe-triage.hf.space \
    TRIAGE_ALLOW_LOOPBACK_PROBES=1 \
    TRIAGE_FRAME_ANCESTOR=https://huggingface.co
WORKDIR /app
COPY src/szl_triage/*.py /app/src/szl_triage/
COPY src/szl_triage/providers/*.py /app/src/szl_triage/providers/
COPY src/szl_triage/data/triage_policy.v3.json /app/src/szl_triage/data/triage_policy.v3.json
COPY SOURCE_BINDING.json /app/SOURCE_BINDING.json
USER 1000:1000
EXPOSE 7860
CMD ["python", "-m", "szl_triage.public_server"]
