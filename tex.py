# tex - A maubot plugin to render LaTeX as SVG
# Copyright (C) 2019 Tulir Asokan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from typing import Type
from io import BytesIO

import matplotlib.pyplot as plot
from PIL import Image

from mautrix.types import ImageInfo, ThumbnailInfo
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from maubot import Plugin, MessageEvent
from maubot.handlers import command


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("use_tex")
        helper.copy("font_size")
        helper.copy("thumbnail_dpi")
        helper.copy("command")


plot.rc("mathtext", fontset="cm")


class TexBot(Plugin):
    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    async def start(self) -> None:
        self.config.load_and_update()

    @command.new(name=lambda self: self.config["command"], help="Render LaTeX")
    @command.argument("formula", required=True, pass_raw=True)
    async def tex(self, evt: MessageEvent, formula: str) -> None:
        fig = plot.figure(figsize=(0.01, 0.01))
        text = fig.text(0, 0, rf"${formula}$",
                        fontsize=self.config["font_size"],
                        use_tex=self.config["use_tex"])

        output = BytesIO()
        fig.savefig(output, format="svg", bbox_inches="tight")
        data = output.getvalue()
        svg_uri = await self.client.upload_media(data, "image/svg+xml", "tex.svg")
        svg_len = len(data)
        output.seek(0)
        output.truncate(0)
        fig.savefig(output, dpi=self.config["thumbnail_dpi"], format="png", bbox_inches="tight")

        data = output.getvalue()
        png_uri = await self.client.upload_media(data, "image/png", "tex.png")
        png_len = len(data)
        plot.close(fig)

        output.seek(0)
        img = Image.open(output)
        png_width, png_height = img.size
        img.close()
        output.close()

        bb = text.get_window_extent(fig.canvas.get_renderer())
        await self.client.send_image(evt.room_id, svg_uri, info=ImageInfo(
            mimetype="image/svg+xml",
            size=svg_len,
            width=bb.width,
            height=bb.height,
            thumbnail_url=png_uri,
            thumbnail_info=ThumbnailInfo(
                mimetype="image/png",
                size=png_len,
                width=png_width,
                height=png_height,
            ),
        ), file_name="tex.svg")
