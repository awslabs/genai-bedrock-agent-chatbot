FROM public.ecr.aws/lambda/python:3.11@sha256:58834a0d4d7f86326b6c91d516c66fbe8e91ccd3646ceba4025a66a7a8906e81
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