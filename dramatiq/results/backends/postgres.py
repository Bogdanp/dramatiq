import asyncio
import datetime
import time
from typing import Optional

import psycopg
from psycopg import AsyncConnection, AsyncCursor
from psycopg.sql import SQL, Identifier

from ..backend import DEFAULT_TIMEOUT, ResultBackend, ResultMissing, ResultTimeout


class PostgresBackend(ResultBackend):
    """A result backend for PostgreSQL.
    Parameters:
      namespace(str): A string with which to prefix result keys.
      encoder(Encoder): The encoder to use when storing and retrieving
        result data.  Defaults to :class:`.JSONEncoder`.
      connection_params(dict): A dictionary of parameters to pass to the
        `psycopg.connect()` function.
      url(str): An optional connection URL.  If both a URL and
        connection parameters are provided, the URL is used.
    """

    def __init__(
        self,
        *,
        namespace="dramatiq_results",
        encoder=None,
        connection_params=None,
        url=None,
    ):
        super().__init__(namespace=namespace, encoder=encoder)

        self.url = url
        self.connection_params = connection_params or {}
        self.connection: AsyncConnection = None
        self.cursor: AsyncCursor = None

    async def connect(self):
        if not self.connection:
            if self.url is not None:
                self.connection = await psycopg.AsyncConnection.connect(self.url)
            else:
                self.connection = await psycopg.AsyncConnection.connect(
                    **self.connection_params
                )

            self.cursor = self.connection.cursor()

            # Create the result table if it doesn't exist
            await self.cursor.execute(
                SQL(
                    "CREATE TABLE IF NOT EXISTS {} ("
                    "message_key VARCHAR(256) PRIMARY KEY,"
                    "result BYTEA NOT NULL,"
                    "created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),"
                    "expires_at TIMESTAMP WITH TIME ZONE NULL"
                    ")"
                ).format(Identifier(self.namespace)),
            )

        # Because of the way sessions interact with notifications (see NOTIFY documentation),
        # you should keep the connection in autocommit mode
        # if you wish to receive or send notifications in a timely manner.
        if not self.connection.autocommit:
            raise Exception("psycopg postgres connection must have autocommit=True")

    def get_result(self, message, *, block=False, timeout=None):
        """Get a result from the backend.
        Parameters:
          message(Message)
          block(bool): Whether or not to block until a result is set.
          timeout(int): The maximum amount of time, in ms, to wait for
            a result when block is True.  Defaults to 10 seconds.
        Raises:
          ResultMissing: When block is False and the result isn't set.
          ResultTimeout: When waiting for a result times out.
        Returns:
          object: The result.
        """

        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        message_key = self.build_message_key(message)

        try:
            loop  = asyncio.new_event_loop()
            x = asyncio.wait_for(
                self._get_result(message_key, block), timeout=timeout / 1000
            )
            data = loop.run_until_complete(x)

        except IndexError:
            raise ResultMissing(message)
        except asyncio.TimeoutError:
            raise ResultTimeout(message)

        return self.unwrap_result(self.encoder.decode(data))

    async def _get_result(self, message_key, block):
        await self.connect()

        def check_notification(notify):
            if notify.payload == message_key:
                future.set_result(True)

        if block:
            future = asyncio.Future()
            self.connection.add_notify_handler(check_notification)
            await self.connection.execute("LISTEN dramatiq") # we need to keep requesting
            await self.connection.commit()
            while not (future.done() and not future.cancelled() and future.exception() is None):
                # TODO look for better method to poll data on the driver level with self
                await self.connection.execute("SELECT 1")
                time.sleep(1)
            await future

        await self.cursor.execute(
            SQL("SELECT result, expires_at FROM {} WHERE message_key=%s").format(
                Identifier(self.namespace)
            ),
            (message_key,),
        )
        all_data = await self.cursor.fetchall()

        data = all_data[0][0]

        time_check = all_data[0][1]
        if time_check:
            if time_check < datetime.datetime.now().astimezone():
                data = None
        return data

    def _store(self, message_id, result, ttl):

        async def async_store(message_id, result, ttl):
            await self.connect()
            expires_at = datetime.datetime.now().astimezone() + datetime.timedelta(
                milliseconds=ttl
            )
            await self.cursor.execute(
                SQL(
                    "INSERT INTO {} (message_key, result, expires_at) VALUES (%s, %s, %s)"
                ).format(Identifier(self.namespace)),
                (
                    message_id,
                    self.encoder.encode(result),
                    expires_at,
                ),
            )
            await self.connection.execute(
                "SELECT pg_notify(%s, %s)", ["dramatiq", message_id]
            )
            await self.connection.commit()

        result = async_store(message_id, result, ttl)
        loop  = asyncio.new_event_loop()
        loop.run_until_complete(result)
