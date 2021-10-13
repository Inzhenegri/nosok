from importlib import import_module
import os
import logging
from pathlib import Path

import discord
from discord_components.client import DiscordComponents
import sqlalchemy as sa
from discord.ext import commands

from base import Base, Session, BASE_PREFIX
from handlers import YDLHandler, YTAPIHandler

use_deprecated = False


class Config(Base):
    __tablename__ = 'config'

    guild_id = sa.Column('guild_id', sa.BigInteger, unique=True, primary_key=True)
    prefix = sa.Column('prefix', sa.String, server_default='!')


if use_deprecated and 'GOOGLE_API_TOKEN' in os.environ.keys():
    google_api_token = os.environ.get('GOOGLE_API_TOKEN')
    yt_handler = YTAPIHandler(google_api_token)
else:
    from youtube_dl.utils import std_headers

    std_headers['Aser-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                                'Chrome/51.0.2704.103 Safari/537.36'


def get_prefix(_, msg: discord.Message) -> str:
    with Session.begin() as s:
        res = s.query(Config).filter_by(guild_id=msg.guild.id).first()
        return res.prefix if res is not None else BASE_PREFIX


class MusicBot(commands.Bot):
    def __init__(self, command_prefix):
        super().__init__(command_prefix, case_insensetive=True)
        self._logger = None

    def setup(self):
        for cls in [import_module(f'cogs.{i.stem}').__dict__[i.stem.title()] for i in Path('./cogs/').glob('*.py')]:
            exec(f'{cls.__name__.lower()} = cls()')
            self.add_cog(eval(cls.__name__.lower()))

    def run(self):
        self.setup()
        TOKEN = os.getenv('TOKEN')
        super().run(TOKEN, reconnect=True)
    
    async def on_ready(self):
        DiscordComponents(self)

        logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s - %(levelname)s - %(name)s:\t%(message)s',
                    datefmt='%y.%b.%Y %H:%M:%S')
        _logger = logging.getLogger('index')
        self._logger = _logger
        self._logger.warning('Bot has been successfully launched')

    async def shutdown(self):
        self._logger.warning('The bot has been shut down...')
        await super().close()

    async def close(self):
        await self.shutdown()

bot = MusicBot(get_prefix)
