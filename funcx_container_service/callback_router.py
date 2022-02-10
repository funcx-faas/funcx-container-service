import logging
from pprint import pformat
from urllib.parse import urljoin

from fastapi import APIRouter
from pydantic import BaseModel
import httpx

from .config import Settings
from .container import Container
from .models import ContainerSpec, BuildSpec, BuildCompletionSpec

log = logging.getLogger("funcx_container_service")


class container_object_json(BaseModel):
    container_id: str


class ContainerSpecReceived(BaseModel):
    container_id: str


class InvoiceEvent(BaseModel):
    description: str
    paid: bool


class InvoiceEventReceived(BaseModel):
    ok: bool


query_container_callback_router = APIRouter()


build_callback_router = APIRouter()


async def register_container_spec(spec: ContainerSpec,
                                  settings: Settings):
    """
    Send container spec to webservice usings requests, get container ID as response
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(f'{settings.WEBSERVICE_URL.strip("/")}/register_container_spec',
                                     data=spec)
    container_id = response.json()['UUID']

    return container_id


def register_container_spec_requests(spec: ContainerSpec,
                                     settings: Settings):
    """
    Send container spec to webservice usings requests, get container ID as response
    """
    import requests
    response = requests.post(f'{settings.WEBSERVICE_URL.strip("/")}/register_container_spec',
                             data=spec)
    container_id = response.json()[0]['UUID']
    return container_id


@build_callback_router.put('<webservice_url>/v2/containers/<container_id>/status')
def register_build(body: BuildSpec):
    pass


async def register_building(container: Container, settings: Settings):

    build_spec = BuildSpec(container_id=container.container_id,
                           build_id=container.build_id,
                           RUN_ID=container.RUN_ID,
                           build_status=container.build_status)

    log.info(f'registering build for: {pformat(build_spec)}')

    async with httpx.AsyncClient() as client:
        response = await client.put(urljoin(
            settings.WEBSERVICE_URL,
            f"v2/containers/{build_spec.container_id}/status"),
            headers={'Content-Type': 'application/json'},
            content=build_spec.json())

        if response.status_code != 200:
            log.error(f"register build sent back {response}")

    return response


@build_callback_router.put('<webservice_url>/v2/containers/<container_id>/status')
def register_build_start(body: BuildSpec):
    pass


async def register_build_starting(container: Container, settings: Settings):

    build_spec = BuildSpec(container_id=container.container_id,
                           build_id=container.build_id,
                           RUN_ID=container.RUN_ID,
                           build_status=container.build_status)

    log.info(f'registering build start for: {pformat(build_spec)}')

    async with httpx.AsyncClient() as client:
        response = await client.put(urljoin(
            settings.WEBSERVICE_URL,
            f"v2/containers/{build_spec.container_id}/status"),
            headers={'Content-Type': 'application/json'},
            content=build_spec.json())

        if response.status_code != 200:
            log.error(f"register build start sent back {response}")


@build_callback_router.put('<webservice_url>/v2/containers/<container_id>/status')
def register_build_completion(body: BuildCompletionSpec):
    pass


async def register_build_complete(completion_spec: BuildCompletionSpec, settings: Settings):

    async with httpx.AsyncClient() as client:
        log.info(f'updating status with message: {pformat(completion_spec)}')
        response = await client.put(urljoin(
            settings.WEBSERVICE_URL,
            f"v2/containers/{completion_spec.container_id}/status"),
            headers={'Content-Type': 'application/json'},
            content=completion_spec.json())

        if response.status_code != 200:
            log.error(f"register build complete sent back {response}")


async def remove_build(container_id):
    pass
