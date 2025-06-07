FROM public.ecr.aws/lambda/python:3.11@sha256:4c04b142654ce3d1b8d705880bf5c720599b5984fd4c751763f09f1682308490
RUN yum update --security -y && yum clean all
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --upgrade pip setuptools wheel --no-cache-dir
RUN pip install -r requirements.txt --no-cache-dir
RUN pip install --pre torch==2.1.2+cpu --no-cache-dir --index-url https://download.pytorch.org/whl/test
COPY . ${LAMBDA_TASK_ROOT}
CMD ["index.get_response"]
USER 1001
HEALTHCHECK --interval=600s --timeout=2s --retries=12 \
    CMD ["cat", "requirements.txt"]