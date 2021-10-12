from enum import Enum
import os

import discord
from dotenv import load_dotenv
from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.declarative import as_declarative
from sqlalchemy.orm import sessionmaker

load_dotenv('.env')
engine = create_engine(os.environ.get('POSTGRES_URL'))
Session = sessionmaker(bind=engine)


BASE_PREFIX = os.environ.get('BASE_PREFIX')
API_KEY = os.environ.get('API_KEY')
BASE_COLOR = discord.Colour.from_rgb(241, 184, 19)
ERROR_COLOR = discord.Colour.from_rgb(255, 0, 0)


class Handler(Enum):
    YTAPI = 0
    YDL = 1


HANDLERS_DATA = [
    {
        "title": "YouTube API",
        "description": "A handler, working with the YouTube API. The API's quota is limited."
    },
    {
        "title": "YouTube DL",
        "description": "An unofficial YouTube API that works with YouTube's audio streams. The API's quota is unlimited."
    }
]


@as_declarative(
    metadata=MetaData(bind=engine)
)
class Base:
    __tablename__ = ...
