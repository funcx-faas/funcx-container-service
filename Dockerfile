FROM python:3.7-alpine
RUN apk update && \
    apk add --no-cache gcc musl-dev linux-headers && \
    apk add postgresql-dev libffi-dev g++ make libressl-dev git

# Create a group and user
RUN addgroup -S uwsgi && adduser -S uwsgi -G uwsgi

WORKDIR /opt/funcx-container-service

COPY ./requirements.txt .
RUN pip install -r requirements.txt
RUN  pip uninstall -y funcx && \
     pip install "git+https://github.com/funcx-faas/funcX.git@dev#egg=funcx&subdirectory=funcx_sdk"

RUN pip install --disable-pip-version-check uwsgi

COPY uwsgi.ini .
COPY ./funcx_container_service/ ./funcx_container_service/
COPY web-entrypoint.sh .

USER uwsgi
EXPOSE 5000

CMD sh web-entrypoint.sh
