# FuncX Container Service

The Container service runs in a container using FastAPI. It's
responsible for creating and managing container environments for running
functions on funcX.

You can run the service inside a docker container.

```
$ docker build -t container_service:latest .
$ docker run -d -p 5000:5000 container_service:latest
```

Or set up a build environment with

```
$ pip install -r requirements.txt
```

Then start the server with

```
$ uvicorn funcx_container_service:app --reload
```

The full API is documented at `http://server:port/docs`.
