# ZeroS reports server for Cloud Run (see README.md). Standard library only,
# so the image holds Python and main.py and nothing else.
#
# SPDX-License-Identifier: Apache-2.0

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY main.py .

USER nobody
CMD ["python", "-I", "main.py"]
