import logging
from pprint import pformat
from urllib.parse import urljoin

from fastapi import APIRouter
from pydantic import BaseModel
import requests

from .config import Settings
from .container import Container
from .models import BuildSpec, CompletionSpec, ContainerSpec, StatusUpdate
import pdb


log = logging.getLogger("funcx_container_service")
query_container_callback_router = APIRouter()
build_callback_router = APIRouter()

class container_object_json(BaseModel):
    container_id: str


class ContainerSpecReceived(BaseModel):
    container_id: str


@build_callback_router.put('<webservice_url>/v2/containers/<container_id>/status')
def updating_status(body: StatusUpdate):
    pass


async def update_status(container: Container):

    if container.completion_spec:
        status_dict = dict(list(container.build_spec.dict().items()) + 
                           list(container.completion_spec.dict().items()) + 
                           list(container.container_spec.dict().items()))
    else:
        status_dict = dict(list(container.build_spec.dict().items()) + 
                           list(container.container_spec.dict().items()))

    log.info(f'updating status for: {pformat(status_dict)}')


    response = requests.put(urljoin(container.settings.WEBSERVICE_URL,
                                            f"v2/containers/{container.container_spec.container_id}/status"),
                            headers={'Content-Type': 'application/json'},
                            data=status_dict)
    
    # async with httpx.AsyncClient() as client:
    #     response = await client.put(urljoin(container.settings.WEBSERVICE_URL,
    #                                         f"v2/containers/{container.container_spec.container_id}/status"),
    #                                 headers={'Content-Type': 'application/json'},
    #                                 content=status_dict)

    if response.status_code != 200:
        log.error(f"Updating of container status sent back {response}")

    return response


async def remove_build(container_id):
    pass
