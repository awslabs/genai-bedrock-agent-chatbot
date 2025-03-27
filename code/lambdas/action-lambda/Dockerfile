FROM public.ecr.aws/lambda/python:3.11@sha256:c35bfe03ea7916f02afdb1ac07940b1bf08a84b14fe7f47ee384b6ed0f4ce222
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