# Copyright (C) 2022 xunleii
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
""""gRPC display API library"""

import abc
import asyncio
import string
import sys
import grpc

from StBoite.protos.v1.stboite_display_pb2_grpc import RenderingServiceServicer, add_RenderingServiceServicer_to_server  # noqa: E501
from StBoite.protos.v1.stboite_display_pb2 import RenderingRequest, RenderingResponse  # noqa: E501

from typing import Optional


class GRPCDisplay(RenderingServiceServicer):
    """Abstract class to simplify the use of the gRPC API for embedded API
    """

    _server: grpc.aio.Server
    __pre_stop: asyncio.Task

    def __init__(self, listen_addr: string):
        self._server = grpc.aio.server()
        self._server.add_insecure_port(listen_addr)

        add_RenderingServiceServicer_to_server(self, self._server)

        async def wait_until_cancel():
            try:
                await asyncio.sleep(sys.float_info.max)
            except asyncio.CancelledError:
                pass
        self.__pre_stop = asyncio.get_event_loop().create_task(wait_until_cancel())  # noqa: E501

    async def start(self) -> None:
        """Starts the gRPC server.

        This method may only be called once. (i.e. it is not idempotent).
        """
        return await self._server.start()

    async def wait_for_termination(self,
                                   timeout: Optional[float] = None) -> bool:
        """Continues current coroutine once the server stops.

        This is an EXPERIMENTAL API.

        The wait will not consume computational resources during blocking, and
        it will block until one of the two following conditions are met:

        1) The server is stopped or terminated;
        2) A timeout occurs if timeout is not `None`.

        The timeout argument works in the same way as `threading.Event.wait()`.
        https://docs.python.org/3/library/threading.html#threading.Event.wait

        Args:
          timeout: A floating point number specifying a timeout for the
            operation in seconds.

        Returns:
          A bool indicates if the operation times out.
        """
        return await asyncio.wait(
            [asyncio.create_task(self._server.wait_for_termination(timeout)),
             self.__pre_stop],
            return_when=asyncio.FIRST_COMPLETED
        )

    def pre_stop(self):
        """Prepare the stop of this server.

        This method use used to stop synchronously the server when a signal is
        caught by asyncio.

        Args:
          grace: A duration of time in seconds or None.
        """
        self.__pre_stop.cancel()

    async def stop(self, grace: Optional[float] = None) -> None:
        """Stops this Server.

        This method immediately stops the server from servicing new RPCs in
        all cases.

        If a grace period is specified, this method returns immediately and all
        RPCs active at the end of the grace period are aborted. If a grace
        period is not specified (by passing None for grace), all existing RPCs
        are aborted immediately and this method blocks until the last RPC
        handler terminates.

        This method is idempotent and may be called at any time. Passing a
        smaller grace value in a subsequent call will have the effect of
        stopping the Server sooner (passing None will have the effect of
        stopping the server immediately). Passing a larger grace value in a
        subsequent call will not have the effect of stopping the server later
        (i.e. the most restrictive grace value is used).

        Args:
          grace: A duration of time in seconds or None.
        """
        return await self._server.stop(grace)

    @abc.abstractclassmethod
    async def DisplayRendering(
        self,
        request: RenderingRequest,
        context: grpc.aio.ServicerContext
    ) -> RenderingResponse:
        """Displays the encapsulated image on the device.
        """
