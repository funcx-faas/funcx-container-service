# FuncX Container Service

The Container service runs in a container using FastAPI. It's
responsible for creating and managing container environments for running
functions on funcX.

A configuration file (titled '.env') is required at the top level of the
repository which houses the configuration settings necessary to run
the serivce. This file uses the VAR=VAL syntax and currently requires the
following VARs defined:

```
WEBSERVICE_URL=<url for the webserivce that issues requests to the container service>
```

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

The full API is documented at `http://server:port/docs`. This includes definitions of 
callback routes, which are examplars of externally hosted routes that the container 
service will rely on for complete functionality. 


The Docker daemon needs to be running (with the control socket)
bind mounted into the container if applicable. Also requires Singularity 3.x
in the build environment.
