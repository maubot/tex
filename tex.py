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

import matplotlib

matplotlib.use("agg")
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
        helper.copy("mode")
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
        # prevent escaping math mode
        # (' ' prevents unexpected interactions, and isn't rendered)
        formula = formula.replace("$", " \\$")

        fig = plot.figure(figsize=(0.01, 0.01))
        text = fig.text(0, 0, rf"$ {formula} $",
                        fontsize=self.config["font_size"],
                        usetex=self.config["use_tex"])
        info = ImageInfo(thumbnail_info=ThumbnailInfo())

        output = BytesIO()
        if self.config["mode"] == "svg":
            fig.savefig(output, format="svg", bbox_inches="tight")
            data = output.getvalue()

            file_name = "tex.svg"
            info.mimetype = "image/svg+xml"
            info.size = len(data)

            bb = text.get_window_extent(fig.canvas.get_renderer())
            info.width, info.height = int(bb.width), int(bb.height)

            uri = await self.client.upload_media(data, info.mimetype, file_name)
        else:
            fig.savefig(output, dpi=300, format="png", bbox_inches="tight")
            data = output.getvalue()

            file_name = "tex.png"
            info.mimetype = "image/png"
            info.size = len(data)

            output.seek(0)
            img = Image.open(output)
            info.width, info.height = img.size

            uri = await self.client.upload_media(data, info.mimetype, file_name)

        output.seek(0)
        output.truncate(0)
        fig.savefig(output, dpi=self.config["thumbnail_dpi"], format="png", bbox_inches="tight")

        data = output.getvalue()
        info.thumbnail_url = await self.client.upload_media(data, "image/png", "tex.thumb.png")
        info.thumbnail_info.mimetype = "image/png"
        info.thumbnail_info.size = len(data)
        plot.close(fig)

        output.seek(0)
        img = Image.open(output)
        info.thumbnail_info.width, info.thumbnail_info.height = img.size
        img.close()
        output.close()

        await self.client.send_image(evt.room_id, uri, info=info, file_name=file_name)
