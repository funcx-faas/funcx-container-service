import json
import logging
from pprint import pformat
from urllib.parse import urljoin
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel
import requests

from .container import Container
from .models import StatusUpdate


log = logging.getLogger("funcx_container_service")
query_container_callback_router = APIRouter()
build_callback_router = APIRouter()


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            # if the obj is uuid, we simply return the value of uuid
            return obj.hex
        return json.JSONEncoder.default(self, obj)


class container_object_json(BaseModel):
    container_id: str


class ContainerSpecReceived(BaseModel):
    container_id: str


@build_callback_router.put('<webservice_url>/v2/containers/<container_id>/status')
def updating_status(body: StatusUpdate):
    pass


def update_status(container: Container):

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
                                    f"v2/internal/containers/{container.container_spec.container_id}/status"),
                            headers={'Content-Type': 'application/json'},
                            data=json.dumps(status_dict, cls=UUIDEncoder))

    if response.status_code != 200:
        log.error(f"Updating of container status returned {response}")

    return response


def remove_build(container_id):
    pass
