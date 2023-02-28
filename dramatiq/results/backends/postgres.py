import asyncio
import datetime
import time
import typing

import psycopg
from psycopg import AsyncConnection, Notify
from psycopg.sql import SQL, Identifier

from ..backend import DEFAULT_TIMEOUT, ResultBackend, ResultMissing, ResultTimeout

# Types

MessageData = typing.Dict[str, typing.Any]
Result = typing.Any


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
        connection=None
    ):
        super().__init__(namespace=namespace, encoder=encoder)

        self.url = url
        self.connection_params = connection_params or {}
        self.connection: AsyncConnection
        self.gen: typing.AsyncGenerator[Notify, None]
        asyncio.new_event_loop().run_until_complete(self.connect(connection))

    async def connect(self, connection):
        """_summary_

        Args:
            connection (_type_): _description_

        Raises:
            Exception: _description_
        """
        # creating connection
        if not connection:
            if self.url is not None:
                self.connection = await psycopg.AsyncConnection.connect(
                    self.url, autocommit=True
                )
            else:
                self.connection = await psycopg.AsyncConnection.connect(
                    **self.connection_params, autocommit=True
                )
        else:
            self.connection = connection

        # postgres listener
        self.gen = self.connection.notifies()
        await self.connection.execute("LISTEN dramatiq")  # we need to keep requesting

        # Create the result table if it doesn't exist
        await self.connection.execute(
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

    def get_result(self, message, *, block=False, timeout=None) -> MessageData:
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
            loop = asyncio.new_event_loop()
            wait = asyncio.wait_for(
                self._get_result(message_key, block), timeout=timeout / 1000
            )
            data = loop.run_until_complete(wait)

        except IndexError as error:
            raise ResultMissing(message) from error
        except asyncio.TimeoutError as error:
            raise ResultTimeout(message) from error

        return self.unwrap_result(self.encoder.decode(data))

    async def _get_result(self, message_key: str, block: bool):

        if block:
            future = asyncio.Future()

            while not (
                future.done() and not future.cancelled() and future.exception() is None
            ):
                # TODO look for better method to poll data on the driver level with self
                async for notify in self.gen:
                    print(
                        notify,
                        notify.payload,
                        message_key,
                        notify.payload == message_key,
                    )
                    if notify.payload == message_key:
                        future.set_result(True)
                        break

            await future

        exe = await self.connection.execute(
            SQL("SELECT result, expires_at FROM {} WHERE message_key=%s").format(
                Identifier(self.namespace)
            ),
            (message_key,),
        )
        all_data = await exe.fetchone()

        data = all_data[0]

        time_check = all_data[1]
        if time_check:
            if time_check < datetime.datetime.now().astimezone():
                data = None
        return data

    def _store(self, message_key: str, result: Result, ttl: int):
        async def async_store(message_key: str, result: Result, ttl: int):
            expires_at = datetime.datetime.now().astimezone() + datetime.timedelta(
                milliseconds=ttl
            )
            await self.connection.execute(
                SQL(
                    "INSERT INTO {} (message_key, result, expires_at) VALUES (%s, %s, %s)"
                ).format(Identifier(self.namespace)),
                (
                    message_key,
                    self.encoder.encode(result),
                    expires_at,
                ),
            )
            await self.connection.execute(
                "SELECT pg_notify(%s, %s)", ["dramatiq", message_key]
            )
            await self.connection.commit()

        result = async_store(message_key, result, ttl)
        loop = asyncio.new_event_loop()
        loop.run_until_complete(result)
