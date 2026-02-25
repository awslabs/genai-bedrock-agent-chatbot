FROM public.ecr.aws/lambda/python:3.13
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --upgrade pip setuptools wheel --no-cache-dir
RUN pip install -r requirements.txt --no-cache-dir
RUN pip install --pre torch --no-cache-dir --index-url https://download.pytorch.org/whl/nightly/cpu
COPY . ${LAMBDA_TASK_ROOT}
HEALTHCHECK --interval=600s --timeout=2s --retries=12 \
    CMD ["cat", "requirements.txt"]
USER 1001
CMD ["index.get_response"]
