from typing import Optional

from fastapi import APIRouter, FastAPI, Depends
from pydantic import BaseModel, HttpUrl
import httpx

from .models import ContainerSpec
from .config import Settings

import pdb

# app = FastAPI()


class ContainerSpecReceived(BaseModel):
    container_id: str


class InvoiceEvent(BaseModel):
    description: str
    paid: bool


class InvoiceEventReceived(BaseModel):
    ok: bool


build_callback_router = APIRouter()


@build_callback_router.post('f{settings.webservice_url}/containers/build/', 
                            response_model=ContainerSpecReceived
                            )
def store_build_spec(body: ContainerSpec, 
                     settings: Settings):
    pdb.set_trace()
    pass


# @app.post("/invoices/", callbacks=invoices_callback_router.routes)
# def create_invoice(invoice: Invoice, callback_url: Optional[HttpUrl] = None):
    """
    Create an invoice.

    This will (let's imagine) let the API user (some external developer) create an
    invoice.

    And this path operation will:

    * Send the invoice to the client.
    * Collect the money from the client.
    * Send a notification back to the API user (the external developer), as a callback.
        * At this point is that the API will somehow send a POST request to the
            external API with the notification of the invoice event
            (e.g. "payment successful").
    """
    # Send the invoice, collect the money, send the notification (the callback)
#     return {"msg": "Invoice received"}


async def register_container_spec(spec: ContainerSpec,
                                  settings: Settings):
    """
    Send container spec to webservice usings requests, get container ID as response
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(f'{settings.webservice_url}/register_container_spec',
                                     data=spec)
    return response


def register_container_spec_requests(spec: ContainerSpec,
                                     settings: Settings):
    """
    Send container spec to webservice usings requests, get container ID as response
    """
    import requests
    response = requests.post(f'{settings.webservice_url}/register_container_spec',
                             data=spec)
    return response
