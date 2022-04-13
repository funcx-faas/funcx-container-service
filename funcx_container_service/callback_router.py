import logging
from pprint import pformat
from urllib.parse import urljoin

from fastapi import APIRouter
from pydantic import BaseModel
import requests

from .container import Container
from .models import StatusUpdate


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
        status_dict = dict(list(container.build_spec.dict().items())
                           + list(container.completion_spec.dict().items())
                           + list(container.container_spec.dict().items()))
    else:
        status_dict = dict(list(container.build_spec.dict().items())
                           + list(container.container_spec.dict().items()))

    if hasattr(container, 'err_msg'):
        status_dict['err_msg'] = container.err_msg

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
        log.error(f"Updating of container status returned {response}")

    return response


async def remove_build(container_id):
    pass
