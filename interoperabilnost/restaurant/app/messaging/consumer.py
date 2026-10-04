"""RabbitMQ - reservation.created i reservation.cancelled."""
import asyncio
import json
import logging
from collections.abc import Awaitable, Callable

import aio_pika

from restaurant.app.config import settings
from restaurant.app.services.inbox_service import (
    QUEUE_RESERVATION_CANCELLED,
    QUEUE_RESERVATION_CREATED,
    QUEUE_RESERVATION_UPDATED,
    ingest_reservation_cancelled,
    ingest_reservation_event,
    ingest_reservation_updated,
)

logger = logging.getLogger(__name__)


async def _listen_queue(
    queue_name: str,
    handler: Callable[[dict], Awaitable[None]],
    stop_event: asyncio.Event,
) -> None:
    while not stop_event.is_set():
        try:
            connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        except Exception as exc:
            logger.warning("RabbitMQ connect failed (%s): %s - retry za 5s", queue_name, exc)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                continue
            return

        try:
            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=1)
                queue = await channel.declare_queue(queue_name, durable=True)
                logger.info("Slušam red %s", queue_name)

                async with queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        if stop_event.is_set():
                            break
                        async with message.process():
                            try:
                                body = json.loads(message.body.decode())
                                await handler(body)
                            except Exception as exc:
                                logger.exception("Greška pri obradi %s: %s", queue_name, exc)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if stop_event.is_set():
                return
            logger.warning("Consumer %s prekinut: %s - retry za 5s", queue_name, exc)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                continue


async def _wrap_created(body: dict) -> None:
    await ingest_reservation_event(body)


async def _wrap_cancelled(body: dict) -> None:
    await ingest_reservation_cancelled(body)


async def _wrap_updated(body: dict) -> None:
    await ingest_reservation_updated(body)


async def run_reservation_consumer(stop_event: asyncio.Event) -> None:
    if not settings.rabbitmq_url:
        logger.info("RabbitMQ nije podešen - consumer ne startuje.")
        return

    await asyncio.gather(
        _listen_queue(QUEUE_RESERVATION_CREATED, _wrap_created, stop_event),
        _listen_queue(QUEUE_RESERVATION_CANCELLED, _wrap_cancelled, stop_event),
        _listen_queue(QUEUE_RESERVATION_UPDATED, _wrap_updated, stop_event),
    )
