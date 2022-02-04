FROM docker:dind-rootless

ENV PYTHONUNBUFFERED=1
USER root

RUN apk add --update --no-cache python3 py3-ruamel.yaml.clib && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools

#RUN apt-get update && \
#    apt-get install -y  gcc musl-dev && \
#    apt-get install -y  postgresql libffi-dev g++ make git

RUN addgroup http && adduser http -G http -D

WORKDIR /opt/

COPY ./requirements.txt .
RUN pip install -r ./requirements.txt

COPY main.py ./main.py
COPY ./funcx_container_service/ ./funcx_container_service/

USER rootless
EXPOSE 8000

CMD PYTHONPATH=./funcx_container_service python main.py