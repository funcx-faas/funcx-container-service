# FuncX Container Service

The Container service runs in a container using FastAPI. It's
responsible for creating and managing container environments for running
functions on funcX.

## Configuring the service

A configuration file (titled '.env') is required at the top level of the
repository which houses the configuration settings necessary to run
the serivce. This file uses the VAR=VAL syntax and currently requires the
following VARs defined:

```
WEBSERVICE_URL=<url for the webserivce that issues requests to the container service>
REGISTRY_USERNAME=<registry username>
REGISTRY_PWD=<registry password>
REGISTRY_URL=<url to registry>
```
`WEBSERVICE_URL` is the webservice for the funcx service that registers the user submission for a container build via the sdk

The `REGISTRY` variables define the access information for the registry to which the resulting image built by the container service should be stored


## Running the service

## Development Setups
For the full container service experience you will want a local instance of the
funcX webservice running, along with a compatible version of the funcX SDK.

### Install the container_service branch of the sdk:
In a clean virtual environment install the container service development 
branch of the funcX SDK
```shell
pip install git+https://github.com/funcx-faas/funcX.git@container_service#subdirectory=funcx_sdk
```

### Run the Container Service
There are two options for running the container service. If you just need it
to be available, you can run a published docker image:
```shell
docker run --rm -it --env WEBSERVICE_URL=http://host.docker.internal:5000 -p 8000:8000 funcx/container-service:dev
```
This uses a macOS Docker feature for accessing the host's ports from within a 
docker container.

For development and debugging purposes, you can run the Container Service in
pyCharm or other IDE. For this, setup a runtime configuration that runs the 
script `main.py`. You will need to provide an environment variable to the 
process that sets `WEBSERVICE_URL=http://localhost:5000`

### Run the FuncX Web Service
Likewise, there are the same two options for running the web service. If you
just want to run the webservice you can use the container_service tagged 
image. In this case, you need to provide the service with a config file. A 
working config file is checked into _this_ repo, `web_svc_app.conf`. This 
gets mounted into the container and run as:
```shell
docker run --rm -it -p 5000:5000 \
       --mount "type=bind,source=$(pwd)/web_svc_app.conf,target=/opt/app.conf" \
       --env APP_CONFIG_FILE=/opt/app.conf \
       funcx/web-service:container_service
```

For development and debugging you can run the web service in pyCharm. That
IDE directly supports flask apps. Just add an environment variable,
```
APP_CONFIG_FILE=../funcx-container-service/web_svc_app.conf
```
The web app will be running on port 5000 and expecting the container service 
on port 8000.

### Taking the Container Service out for a Spin
With the container service enabled SDK, it's easy to submit a container 
build request:
```python
from funcx import ContainerSpec, FuncXClient

fxc = FuncXClient(funcx_service_address="http://localhost:5000/v2")
container_uuid = fxc.build_container(
    ContainerSpec(
        name="MyContainer",
        apt=[
            "dvipng",
            "ghostscript"
        ],
        pip=[
            "cycler==0.10.0"
        ],
    )
)

print(f"Building {container_uuid}")
print(f"status is {fxc.get_container_build_status(container_uuid)}")
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

## Testing

Two types of tests so far;
	use `pytest -m "not integration_test" tests/resources` to only run
	unit tests.
	
	To run integration tests, start docker as above and use
	`pytest -m "integration_test" tests/resources`
	
	
	



