FROM --platform=linux/arm64 public.ecr.aws/lambda/python:3.14-arm64

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt

COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

ENV SENDER_EMAIL=sweetmandoo@kakao.com
ENV RECIPIENT_EMAILS=chemi0110@gmail.com


CMD ["lambda_function.lambda_handler"]
