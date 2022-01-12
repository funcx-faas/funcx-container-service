import logging
from pprint import pformat
from urllib.parse import urljoin

from fastapi import APIRouter
from pydantic import BaseModel
import httpx

from .config import Settings
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


@build_callback_router.put(f'{Settings().WEBSERVICE_URL.strip("/")}/v2/containers/[container_id]/status')
def register_build_start(body: BuildSpec):
    pass


async def register_build(build_spec: BuildSpec, settings: Settings):

    """
    Generates and assigns a uuid as a 'build_id' that, in combination with the
    container_id, can be used to track the building of a container.
    """

    build_dict = {}
    build_dict['container_id'] = str(build_spec.container_id)
    build_dict['build_id'] = str(build_spec.build_id)
    build_dict['RUN_ID'] = str(build_spec.RUN_ID)

    build_dict['build_status'] = 'queued'

    # submit build back to webservice

    log.info(pformat(build_dict))

    async with httpx.AsyncClient() as client:
        response = await client.put(urljoin(
            settings.WEBSERVICE_URL,
            f"v2/containers/{build_spec.container_id}/status"),
            json=build_dict)

        if response.status_code != 200:
            log.error(f"register build sent back {response}")

    # leftover from db implementation
    # db.add(build)
    # db.commit()  # needed to get relationships
    # build.container.last_used = datetime.now()  # <-- # from database.add_build
    # - but why are we setting this before writing???

    return response


@build_callback_router.put(f'{Settings().WEBSERVICE_URL.strip("/")}/v2/containers/[container_id]/status')
def register_build_completion(body: BuildCompletionSpec):
    pass


async def register_build_complete(completion_spec, settings: Settings):

    async with httpx.AsyncClient() as client:
        response = await client.put(urljoin(
            settings.WEBSERVICE_URL,
            f"v2/containers/{completion_spec.container_id}/status"),
            json=completion_spec)

        if response.status_code != 200:
            log.error(f"register build complete sent back {response}")


async def remove_build(container_id):
    pass
