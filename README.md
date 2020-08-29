# FuncX Container Service

The Container service runs in a container on Flask behind uWSGI. It's
responsible for creating and managing container environments for running
functions on funcX.

## Routes

This service will have the following routes:

### /environment

This route accepts a POST with a payload containing environment details to
create new containers, and a GET to retrieve environment state and details.

#### POST

Request payload:

```
{
  'name': '<ENVIRONMENT-NAME>',
  'docker-image': '<DOCKER-IMAGE>',
}
```

Response payload:

```
{
  'uuid': '<ENVIRONMENT-UUID>'
}
```

The environment identifier will be used to run functions in the created
environment.

#### GET

Gets the state of the environment. To return build logs, etc., pass the query
parameter `?log=true`.

## Docker Container

You can run the service inside a docker container.

```
>> docker build -t container_service:latest .
>> docker run -d -p 5000:5000 container_service:latest
```
