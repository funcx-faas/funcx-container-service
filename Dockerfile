FROM python:3.7-alpine
RUN apk update && \
    apk add --no-cache gcc musl-dev linux-headers && \
    apk add postgresql-dev libffi-dev g++ make libressl-dev git

# Create a group and user
RUN addgroup -S http && adduser -S http -G http

WORKDIR /opt/

COPY ./requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

COPY ./funcx_container_service/ ./

USER http
EXPOSE 5000

CMD uvicorn funcx_container_service:app --host '0.0.0.0' --port 5000
