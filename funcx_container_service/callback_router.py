from typing import Optional
import uuid
import datetime

from fastapi import APIRouter, FastAPI, Depends
from pydantic import BaseModel, HttpUrl
import httpx

# from .build import Build
from .models import ContainerSpec
from .config import Settings


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


@build_callback_router.post('f{Settings.webservice_url}/container/build/',
                            response_model=ContainerSpecReceived
                            )
def store_build_spec(body: ContainerSpec, 
                     settings: Settings):
    pass


@build_callback_router.get('f{Settings.webservice_url}/container/',
                           response_model=ContainerSpecReceived
                           )
def store_container(body: container_object_json):
    pass


async def register_container_spec(spec: ContainerSpec,
                                  settings: Settings):
    """
    Send container spec to webservice usings requests, get container ID as response
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(f'{settings.webservice_url}/register_container_spec',
                                     data=spec)
        
        container_id = response.json()[0]['UUID']
    return container_id


def register_container_spec_requests(spec: ContainerSpec,
                                     settings: Settings):
    """
    Send container spec to webservice usings requests, get container ID as response
    """
    import requests
    response = requests.post(f'{settings.webservice_url}/register_container_spec',
                             data=spec)
    container_id = response.json()[0]['UUID']
    return container_id


async def add_build(container_id, settings: Settings):
    build = Build()
    build.id = str(uuid.uuid4())
    build.container_hash = container_id

    # submit build back to webservice
    async with httpx.AsyncClient() as client:
        response = await client.post(f'{settings.webservice_url}/register_container_spec',
                                     data=build)
    
    # leftover from db implementation
    # db.add(build)
    # db.commit()  # needed to get relationships
    build.container.last_used = datetime.now()  # <-- # from database.add_build - but why are we setting this before writing???
    
    return build.id


async def remove_build(container_id):
    pass
