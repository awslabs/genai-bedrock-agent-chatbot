FROM public.ecr.aws/lambda/python:3.13@sha256:1ef8416e080a80b98b8ca15e6d16cd952d04a4cfd82ad749f009e2c23cbda59a
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --upgrade pip setuptools wheel --no-cache-dir
RUN pip install -r requirements.txt --no-cache-dir
RUN pip install --pre torch --no-cache-dir --index-url https://download.pytorch.org/whl/nightly/cpu
COPY . ${LAMBDA_TASK_ROOT}
CMD ["index.get_response"]
USER 1001
HEALTHCHECK --interval=600s --timeout=2s --retries=12 \
    CMD ["cat", "requirements.txt"]