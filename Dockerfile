FROM python:3.7
RUN apt-get update && \
    apt-get install -y  gcc musl-dev && \
    apt-get install -y  postgresql libffi-dev g++ make git

RUN addgroup http && useradd http -g http

WORKDIR /opt/

COPY ./requirements.txt .
RUN pip install -r ./requirements.txt

COPY ./funcx_container_service/ ./funcx_container_service/

USER http
EXPOSE 5000

CMD uvicorn funcx_container_service:app --host '0.0.0.0' --port 5000
