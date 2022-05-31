#!/usr/bin/env python3
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

import argparse
import asyncio
from datetime import datetime
from enum import Enum
import grpc
import logging
import signal
import string
from typing import Optional

from PIL import Image
from stboite.display.v1 import GRPCDisplay
from stboite.grpc.v1. import RenderingRequest, RenderingResponse
from TP_lib import epd2in13_V2


class eInk_Waveshare_2in13(GRPCDisplay):
    """Implements the gRPC display server to the eInk Waveshare 2.13inch screen
    """
    class Mode(Enum):
        DEEP_SLEEP = 0
        PARTIAL_UPDATE = 1
        FULL_UPDATE = 2

    __epd: epd2in13_V2.EPD_2IN13_V2
    __lock = asyncio.Lock()

    __current_mode: Mode = Mode.DEEP_SLEEP
    __frame_before_refresh: int = 0
    __last_frame: any
    __last_refresh: datetime
    __running: bool = True

    def __init__(self, listen_addr: string):
        super().__init__(listen_addr=listen_addr)

        self.__epd = epd2in13_V2.EPD_2IN13_V2()
        self.__full_update_mode()
        self.__epd.Clear(0xFF)
        # TODO: display a splashscreen
        self.__last_refresh = datetime.now()

    async def wait_for_termination(self,
                                   timeout: Optional[float] = None) -> None:
        return await asyncio.gather(
            self.__eink_loop(),
            super().wait_for_termination(timeout)
        )

    def pre_stop(self):
        self.__running = False
        return super().pre_stop()

    async def stop(self, grace: Optional[float] = None) -> None:
        async def stop():
            self.__epd.sleep()
            await asyncio.sleep(grace)
            self.__epd.Dev_exit()
        return await asyncio.gather(stop(), super().stop(grace))

    async def DisplayRendering(
        self,
        request: RenderingRequest,
        context: grpc.aio.ServicerContext
    ) -> RenderingResponse:
        mode = RenderingRequest.PixelType.Name(request.type)
        size = (request.width, request.height)
        data = request.data

        if size != (250, 122):
            return RenderingResponse(
                status=RenderingResponse.DIMENSION_NOT_ALLOWED,
                details="rendering frame dimension size must be exactly 250x122px"  # noqa: E501
            )

        self.__last_frame = self.__epd.getbuffer(Image.frombytes(mode, size, data))  # noqa: E501
        self.__frame_before_refresh -= 1

        async with self.__lock:
            if self.__frame_before_refresh < 0 or self.__current_mode is self.Mode.DEEP_SLEEP:  # noqa: E501
                self.__frame_before_refresh = 15
                self.__full_display()
            else:
                self.__partial_display()

        return RenderingResponse(status=RenderingResponse.OK)

    async def __eink_loop(self) -> None:
        """Asynchronous loop running in parallel to the gRPC server and
        handling some precautions given by Waveshare:

         - For the screen that supports partial update, please note that
           you cannot refresh the screen with the partial mode all the time.
           After several partial updating, you need to fully refresh the
           screen once. Otherwise, the screen display effect will be
           abnormal, which cannot be repaired!

         - When using the e-Paper, it is recommended that the refresh interval
           be at least 180s, and refresh at least once every 24 hours.
        """

        while self.__running:
            # NOTE: to reduce energy & CPU consumption, the loop will only run
            #       once each 5 seconds
            await asyncio.sleep(5)

            elapsed = datetime.now() - self.__last_refresh

            if elapsed.total_seconds() < 60:
                # NOTE: ignore deep sleep if the screen as been refreshed the
                #       last minute
                continue

            if self.__current_mode is self.Mode.DEEP_SLEEP and elapsed.days > 0:  # noqa: E501
                self.__logging.debug("last frame has been displayed 1 day ago, screen update required")  # noqa: E501
                async with self.__lock:
                    self.__full_display()
                    self.__sleep_mode()
                    continue

            if self.__current_mode is self.Mode.DEEP_SLEEP:
                # NOTE: already in deep sleep mode, ignore
                continue

            async with self.__lock:
                self.__logging.debug("last frame has been displayed 1 min ago, enter in deep sleep mode")  # noqa: E501
                self.__sleep_mode()

    def __sleep_mode(self) -> None:
        if self.__current_mode is not self.Mode.DEEP_SLEEP:
            self.__logging.debug("eInk screen entering in deep sleep mode (low consumption).")  # noqa: E501
            self.__epd.sleep()
            self.__current_mode = self.Mode.DEEP_SLEEP

    def __full_update_mode(self) -> None:
        if self.__current_mode is not self.Mode.FULL_UPDATE:
            self.__logging.debug("eInk screen entering in full update mode.")  # noqa: E501
            self.__epd.init(self.__epd.FULL_UPDATE)
            self.__current_mode = self.Mode.FULL_UPDATE

    def __partial_update_mode(self) -> None:
        if self.__current_mode is not self.Mode.PARTIAL_UPDATE:
            self.__logging.debug("eInk screen entering in partial update mode.")  # noqa: E501
            self.__epd.init(self.__epd.PART_UPDATE)
            self.__current_mode = self.Mode.PARTIAL_UPDATE

    def __full_display(self) -> None:
        self.__full_update_mode()
        self.__epd.displayPartBaseImage(self.__last_frame)
        self.__last_refresh = datetime.now()

    def __partial_display(self) -> None:
        self.__partial_update_mode()
        self.__epd.displayPartial_Wait(self.__last_frame)
        self.__last_refresh = datetime.now()

    @property
    def __logging(self) -> logging.Logger:
        return logging.getLogger("eInk_Waveshare_2in13")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="gRPC API for Waveshare 2.13inch eInk screen.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("-l", "--listen-addr", help="Address to listen on for gRPC API.", default="[::]:48765")  # noqa: E501
    parser.add_argument("--log-level", help="Log severity.", choices=["fatal", "error", "warning", "info", "debug"], default="info")  # noqa: E501
    args = parser.parse_args()

    logging.basicConfig(level=logging.getLevelName(args.log_level.upper()))
    loop = asyncio.get_event_loop()

    server = eInk_Waveshare_2in13(args.listen_addr)
    loop.add_signal_handler(signal.SIGINT, server.pre_stop)
    loop.add_signal_handler(signal.SIGTERM, server.pre_stop)

    try:
        logging.info("starting server on %s", args.listen_addr)
        loop.run_until_complete(server.start())
        loop.run_until_complete(server.wait_for_termination())
    finally:
        loop.run_until_complete(server.stop(5))
        loop.close()
