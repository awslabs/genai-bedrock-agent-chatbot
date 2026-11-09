# Base image pinned by multi-arch index digest for reproducible, tamper-evident builds.
# Dependabot (docker ecosystem) keeps this digest current -- see .github/dependabot.yml.
FROM public.ecr.aws/lambda/python:3.15@sha256:fb2b0ee9404b4f66f7d0d02c9851cc10a5e335a0d4e8613454e974f8f0381eea

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
