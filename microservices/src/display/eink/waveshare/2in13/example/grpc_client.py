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
import grpc
import logging
import os

from PIL import Image, ImageDraw, ImageChops, ImageFont

from stboite.grpc.v1.stboite_display_pb2_grpc import RenderingServiceStub
from stboite.grpc.v1.stboite_display_pb2 import RenderingRequest, RenderingResponse

async def run(addr: str) -> None:
    async with grpc.aio.insecure_channel(target=addr) as channel:
        stub = RenderingServiceStub(channel)

        curdir = os.path.dirname(os.path.realpath(__file__))
        image = Image.new('RGBA', (250, 122), '#ffffff')

        # SyncThings logo
        imagedir = os.path.join(curdir, 'assets/images')
        logo = Image.open(os.path.join(imagedir, 'logo.syncthings.bmp'))
        image.paste(logo, (10, 31))

        response = await stub.DisplayRendering(RenderingRequest(
            type=RenderingRequest.PixelType.RGBA,
            width=250,
            height=122,
            data=image.tobytes(),
        ))
        print(f"status: {RenderingResponse.StatusCode.Name(response.status)}, details: {response.details}") # noqa


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("--addr", help="gRPC API address.", default="localhost:48765")  # noqa: E501
    args = parser.parse_args()

    logging.basicConfig()
    asyncio.run(run(args.addr))
