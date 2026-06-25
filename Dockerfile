# Entorno Linux x86-64 para correr el motor cabt (libcg.so es ELF x86-64; no carga en macOS/M1).
# Build:  docker build --platform=linux/amd64 -t ptcg-cabt .
# Run:    docker run --platform=linux/amd64 --rm -v "$PWD":/work -w /work ptcg-cabt python smoke_test.py
FROM --platform=linux/amd64 python:3.11-slim

RUN pip install --no-cache-dir kaggle-environments trueskill numpy

WORKDIR /work
CMD ["python", "smoke_test.py"]
