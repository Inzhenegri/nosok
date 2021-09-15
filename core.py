import os

import sqlalchemy as sa
from sqlalchemy.orm import Session
from googleapiclient.discovery import build
from pytube import YouTube
import typing

from base import Base, engine


class Config(Base):
    __tablename__ = 'config'

    id = sa.Column('config_id', sa.Integer, primary_key=True)
    created_at = sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now())
    guild_id = sa.Column('guild_id', sa.Integer, unique=True)
    prefix = sa.Column('prefix', sa.String)


class YoutubeHandler:
    def __init__(self, api_key: str, scheme: str = 'https'):
        self._scheme = scheme
        self._service = build('youtube', 'v3', developerKey=api_key)

    def get_urls(self, query: str, max_results: int = 5) -> typing.Generator:
        response = self._service.search().list(
            q=query,
            part='id, snippet',
            maxResults=max_results).execute()

        for i in response.get('items'):
            yield self._scheme + '://youtube.com/watch?v=' + i['id']['videoId'], i['snippet']  # url, info

    def get_url(self, query: str) -> tuple:
        return self.get_urls(query).__next__()

    def get_stream(self, query: str = '', url: str = '') -> str:
        if not query and not url:
            raise ValueError('Neither query nor url given')

        if not url:
            url = self.get_url(query)[0]

        streams = YouTube(url).streams.filter(type='audio')
        return max(streams, key=lambda x: x.bitrate).url


google_api_token = None
yt_handler = YoutubeHandler(google_api_token)