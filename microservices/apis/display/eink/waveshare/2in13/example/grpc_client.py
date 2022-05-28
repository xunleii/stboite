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
from datetime import datetime, timedelta
import socket
import string
import grpc
import logging
import random
import os
import timeago

from PIL import Image, ImageDraw, ImageChops, ImageFont

from StBoite.display.v1 import RenderingRequest, RenderingResponse  # noqa: E501
from StBoite.protos.v1.stboite_display_pb2_grpc import RenderingServiceStub


async def run(addr: string) -> None:
    async with grpc.aio.insecure_channel(target=addr) as channel:
        stub = RenderingServiceStub(channel)

        # -------------------------------------------
        curdir = os.path.dirname(os.path.realpath(__file__))

        # Prepare font
        fontdir = os.path.join(curdir, 'assets/fonts') # noqa
        roboto = os.path.join(fontdir, 'Roboto-Bold.ttf')
        roboto14 = ImageFont.truetype(roboto, 14)
        roboto11 = ImageFont.truetype(roboto, 11)

        # Prepare background
        imagedir = os.path.join(curdir, 'assets/images')
        background = Image.open(os.path.join(imagedir, 'home.background.bmp'))

        # Write information
        date = Image.new('RGBA', (250, 122))
        ImageDraw.Draw(date).text(
            (1, 0),
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            font=roboto14,
            fill="#000"
        )

        ip = Image.new('RGBA', (250, 122))
        ImageDraw.Draw(ip).text(
            (61, 27),
            f"IP: {socket.gethostbyname(socket.gethostname())}",
            font=roboto14,
            fill="#000"
        )

        peers = Image.new('RGBA', (250, 122))
        ImageDraw.Draw(peers).text(
            (76, 50),
            f"Peers: {random.randint(0, 8)}/8",
            font=roboto14,
            fill="#000"
        )

        time_ranges = [60, 86400, 604800, 2.628e+6, 3.156e+7, 3.156e+8]
        max_seconds = time_ranges[random.randint(0, len(time_ranges)-1)]
        last_usage_date = timedelta(seconds=random.randint(0, max_seconds)) # noqa
        last_sync = Image.new('RGBA', (250, 122))
        ImageDraw.Draw(last_sync).text(
            (76, 75),
            f"Last sync: {timeago.format(last_usage_date)}",
            font=roboto14,
            fill="#000"
        )

        usage = Image.new('RGBA', (250, 122), "#fff0")
        ImageDraw.Draw(usage).text(
            (61, 97),
            "Usage:",
            font=roboto14,
            fill="#000"
        )

        percent = random.randint(0, 100)
        bar = Image.new('1', (109, 13), "#000")
        if percent < 100:
            ImageDraw.Draw(bar).rectangle(
                (1+107*(percent/100), 1, 107, 11),
                fill="#fff"
            )
        percentTxt = Image.new('1', (109, 13), "#fff")
        ImageDraw.Draw(percentTxt).text(
            (44, 0),
            f"{percent}%",
            font=roboto11,
            fill="#000"
        )

        # Make the percentage white over the progress bar
        usage.paste(ImageChops.invert(ImageChops.logical_xor(bar, percentTxt)), (106, 99)) # noqa

        # Merge all layers
        image = Image.new('RGBA', (250, 122))
        image.paste(background)
        image.paste(ip, (0, 0), ip)
        image.paste(date, (0, 0), date)
        image.paste(peers, (0, 0), peers)
        image.paste(last_sync, (0, 0), last_sync)
        image.paste(usage, (0, 0), usage)
        # -------------------------------------------

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
