"""
An example of the Consumer Pull use case from the Transfer Data Plane extension:
https://github.com/eclipse-edc/Connector/tree/main/extensions/control-plane/transfer/transfer-data-plane

In this case the Provider serves as a proxy for the 
Mock HTTP API contained in the 'mock-component' folder.
The Provider sends the access token to the Consumer Backend through the Consumer. 
Then, the Consumer Backend uses the access token to send requests 
to the Mock HTTP API through the Data Plane of the Connector.
"""

import asyncio
import logging
import os
import pprint

import coloredlogs
import httpx

from edcpy.config import ConsumerProviderPairConfig
from edcpy.messaging import HttpPullMessage, messaging_app
from edcpy.orchestrator import RequestOrchestrator

# These asset names are known in advance and are used to query the provider.
# However, they could be selected dynamically by browsing the catalogue.
_ASSET_CONSUMPTION = "GET-consumption"
_ASSET_CONSUMPTION_PREDICTION = "POST-consumption-prediction"

_QUEUE_GET_TIMEOUT_SECS = 10

_logger = logging.getLogger(__name__)
_queue: asyncio.Queue[HttpPullMessage] = asyncio.Queue()


async def pull_handler(message: HttpPullMessage):
    """This handler is called when a message is received
    from the HTTP Pull queue in the Rabbit broker."""

    _logger.info(
        "Putting HTTP Pull request into the queue:\n%s", pprint.pformat(message.dict())
    )

    # Using a queue is not strictly necessary.
    # We just need an asyncio-compatible way to pass
    # the messages from the broker to the main function.
    await _queue.put(message)


async def transfer_asset(orchestrator: RequestOrchestrator, asset_query: str) -> str:
    """A helper function to handle the series of Management API
    calls that are required to transfer an asset."""

    transfer_details = await orchestrator.prepare_to_transfer_asset(
        asset_query=asset_query
    )

    transfer_process = await orchestrator.create_consumer_pull_transfer_process(
        contract_agreement_id=transfer_details.contract_agreement_id,
        asset_id=transfer_details.asset_id,
    )

    transfer_process_id = transfer_process["@id"]

    await orchestrator.wait_for_transfer_process(
        transfer_process_id=transfer_process_id
    )

    return transfer_process_id


async def request_get(orchestrator: RequestOrchestrator):
    """Demonstration of a GET request to the Mock HTTP API."""

    transfer_process_id = await transfer_asset(
        asset_query=_ASSET_CONSUMPTION, orchestrator=orchestrator
    )

    http_pull_msg = await asyncio.wait_for(
        _queue.get(), timeout=_QUEUE_GET_TIMEOUT_SECS
    )

    assert (
        http_pull_msg.id == transfer_process_id
    ), "The ID of the Transfer Process does not match the ID of the HTTP Pull message"

    async with httpx.AsyncClient() as client:
        _logger.info(
            "Sending HTTP GET request with arguments:\n%s",
            pprint.pformat(http_pull_msg.request_args),
        )

        resp = await client.request(**http_pull_msg.request_args)
        _logger.info("Response:\n%s", pprint.pformat(resp.json()))


async def request_post(orchestrator: RequestOrchestrator):
    """Demonstration of how to call a POST endpoint of the Mock HTTP API passing a JSON body."""

    transfer_process_id = await transfer_asset(
        asset_query=_ASSET_CONSUMPTION_PREDICTION, orchestrator=orchestrator
    )

    http_pull_msg = await asyncio.wait_for(
        _queue.get(), timeout=_QUEUE_GET_TIMEOUT_SECS
    )

    assert (
        http_pull_msg.id == transfer_process_id
    ), "The ID of the Transfer Process does not match the ID of the HTTP Pull message"

    async with httpx.AsyncClient() as client:
        _logger.info(
            "Sending HTTP POST request with arguments:\n%s",
            pprint.pformat(http_pull_msg.request_args),
        )

        # The body of the POST request is passed as a JSON object.
        # Previous knowledge of the request body schema is required.
        post_body = {
            "date_from": "2023-06-15T14:30:00",
            "date_to": "2023-06-15T18:00:00",
            "location": "Asturias",
        }

        resp = await client.request(**http_pull_msg.request_args, json=post_body)

        _logger.info("Response:\n%s", pprint.pformat(resp.json()))


async def main():
    # Start the Rabbit broker and set the handler for the HTTP pull messages
    # (EndpointDataReference) received on the Consumer Backend from the Provider.
    async with messaging_app(http_pull_handler=pull_handler):
        # The orchestrator contains the logic to interact with the EDC HTTP APIs:
        # https://app.swaggerhub.com/apis/eclipse-edc-bot/management-api/0.1.0-SNAPSHOT
        config = ConsumerProviderPairConfig.from_env()
        orchestrator = RequestOrchestrator(config=config)
        _logger.debug("Configuration:\n%s", pprint.pformat(config.__dict__))

        # Please note that the Mock HTTP API is a regular HTTP API
        # that is not aware of the particularities of a Data Space.
        await request_get(orchestrator=orchestrator)
        await request_post(orchestrator=orchestrator)


if __name__ == "__main__":
    coloredlogs.install(level=os.getenv("LOG_LEVEL", "DEBUG"))
    asyncio.run(main())
