FROM python:3.7
RUN apt-get update && \
    apt-get install -y  gcc musl-dev && \
    apt-get install -y  postgresql libffi-dev g++ make git

RUN addgroup http && useradd http -g http

WORKDIR /opt/

COPY ./requirements.txt .
RUN pip install -r ./requirements.txt

COPY main.py ./main.py
COPY ./funcx_container_service/ ./funcx_container_service/

USER http
EXPOSE 8000
ENV PYTHONUNBUFFERED=1

CMD PYTHONPATH=./funcx_container_service python main.py