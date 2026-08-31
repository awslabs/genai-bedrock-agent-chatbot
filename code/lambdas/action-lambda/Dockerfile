# Base image pinned by multi-arch index digest for reproducible, tamper-evident builds.
# Dependabot (docker ecosystem) keeps this digest current -- see .github/dependabot.yml.
FROM public.ecr.aws/lambda/python:3.14@sha256:899f14ad6c71edb8db32cc194aace9eb9af77a3a6ad991526c01d282564a5a39

COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Single layer: upgrade build tooling, then install pinned runtime dependencies.
# Embeddings and LLM inference are served by the Bedrock API (llama-index-embeddings-bedrock
# / llama-index-llms-bedrock), so no local model runtime (torch) is required.
RUN pip install --upgrade pip setuptools wheel --no-cache-dir \
    && pip install -r requirements.txt --no-cache-dir

COPY . ${LAMBDA_TASK_ROOT}

HEALTHCHECK --interval=600s --timeout=2s --retries=12 \
    CMD ["cat", "requirements.txt"]
USER 1001
CMD ["index.get_response"]
