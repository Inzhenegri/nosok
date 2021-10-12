import asyncio
import re
import typing
from collections import defaultdict

import discord
from discord.embeds import Embed
from discord.ext import commands
from discord_components.interaction import InteractionType

import exceptions
from handlers import YDLHandler, YTAPIHandler
import utils
from base import API_KEY, BASE_COLOR, ERROR_COLOR, HANDLERS_DATA, Handler
from core import bot
from utils import get_handlers_components, get_track_components, is_connected, send_embed


URL_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s(" \
            r")<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"


class Queue:
    def __init__(self):
        self._tracks: list[tuple] = []
        self._loop: int = 0  # 0 - None; 1 - Current queue; 2 - Current track
        self.now_playing: int = 0
        self.play_next: bool = True

    def add(self, url: str, title: str, mention: discord.User.mention) -> None:
        self._tracks.append((url, title, mention))

    def get_next(self) -> typing.Optional[tuple]:
        self.now_playing += int(self._loop != 2)
        if self.now_playing >= len(self._tracks):
            if self._loop == 0:
                self.now_playing = -1
                self.play_next = False
                return None
            else:
                self.now_playing = 0

        return self._tracks[self.now_playing]

    def __len__(self):
        return len(self._tracks)

    def remove(self, index: int) -> tuple:
        return self._tracks.pop(index)

    def clear(self) -> None:
        self._tracks.clear()

    @property
    def is_empty(self) -> bool:
        return not bool(self._tracks)

    @property
    def queue(self) -> list:
        return self._tracks

    @property
    def current(self) -> typing.Optional[tuple]:
        return self._tracks[self.now_playing] if len(self._tracks) > 0 else None

    @property
    def loop(self):
        return self._loop

    @property
    def previous(self):
        return self._tracks[self.now_playing - 2]

    @loop.setter
    def loop(self, value: int):
        self._loop = value


class Music(commands.Cog):
    def __init__(self):
        self._queues: defaultdict[Queue] = defaultdict(Queue)
        self.handler = None
        self.preferred_handler = Handler.YDL
        self._yt = YDLHandler({
            'simulate': True,
            'quiet': True,
            'format': 'bestaudio/best'
        }) if self.preferred_handler == Handler.YDL else YTAPIHandler(API_KEY)

    @commands.command(aliases=['j'])
    async def join(self, ctx: commands.Context, voice_channel: discord.VoiceChannel = None) -> None:
        """
        Makes the bot join your current voice channel
        """
        if ctx.voice_client:
            await utils.send_embed(
                ctx=ctx,
                description='I am already connected to a voice channel!',
                color=ERROR_COLOR,
            )
            raise exceptions.AlreadyConnected

        voice = ctx.author.voice
        if not voice:
            await utils.send_embed(
                ctx=ctx,
                description='Connect to a voice channel first',
                color=ERROR_COLOR
            )
            raise exceptions.UserNotConnected

        if voice_channel:
            await voice_channel.connect()
        else:
            await voice.channel.connect()

    @commands.command(aliases=['s'])
    @commands.check(is_connected)
    async def stop(self, ctx: commands.Context) -> None:
        """
        Stops bot from playing the current song.
        """
        q: Queue = self._queues[ctx.guild.id]
        q.play_next = False
        ctx.voice_client.stop()

    @commands.command(aliases=['l'])
    @commands.check(is_connected)
    async def leave(self, ctx: commands.Context) -> None:
        """
        Makes bot leave your current channel.
        """
        voice = ctx.voice_client
        if voice.is_playing():
            await self.stop(ctx)
        await voice.disconnect()

    @commands.command(aliases=['ps'])
    @commands.check(is_connected)
    async def pause(self, ctx: commands.Context) -> None:
        """
        Pauses current song. Use `play` command to resume.
        """
        voice = ctx.voice_client
        if voice.is_playing():
            voice.pause()
        else:
            await utils.send_embed(
                ctx=ctx,
                description='I am not playing yet!',
                color=ERROR_COLOR
            )

    @commands.command(aliases=['c'])
    @commands.check(is_connected)
    async def current(self, ctx: commands.Context) -> None:
        """
        Displays current playing song.
        """
        voice = ctx.voice_client
        if not voice.is_playing():
            await utils.send_embed(
                ctx=ctx,
                description='I am not playing any song for now!',
                color=ERROR_COLOR
            )
            return

        q: Queue = self._queues[ctx.guild.id]
        current = q.current
        await utils.send_embed(
            ctx=ctx,
            title='Current song:',
            description=f'[{current[1]}]({current[0]}) | {current[2]}',
            color=BASE_COLOR
        )

    @commands.command(aliases=['n'])
    @commands.check(is_connected)
    async def next(self, ctx: commands.Context):
        ctx.voice_client.stop()

    @commands.command(aliases=['prev'])
    @commands.check(is_connected)
    async def previous(self, ctx: commands.Context):
        q: Queue = self._queues[ctx.guild.id]
        if len(q) > 0:
            q.now_playing -= 1
            if q.loop == 0 and q.now_playing < 0:
                q.now_playing = 0
                await send_embed(
                    ctx=ctx,
                    description='There are no tracks before current song',
                    color=ERROR_COLOR)
                raise exceptions.NoPreviousTracks

            ctx.guild.voice_client.stop()

            stream = self._yt.get_stream(q.current[0])
            loop = bot.loop
            await self._play(ctx, stream, loop)
        else:
            await utils.send_embed(
                ctx=ctx,
                description='The queue is empty!',
                color=ERROR_COLOR
            )
            raise exceptions.QueueEmpty

    async def _get_tracks_pagination(self, ctx: commands.Context, *tracks):
        embeds = []
        tracks = tracks[0]

        for url, title, thumbnail in tracks:
            embed = Embed(title=title, url=url)
            embed.set_thumbnail(url=thumbnail)
            embed.set_author(name=ctx.author)
            embeds.append(embed)

        current = 0
        message = await ctx.reply(
            embed=embeds[current],
            components=get_track_components(embeds, current)
        )

        while True:
            try:
                interaction = await bot.wait_for(
                    'button_click',
                    check=lambda i: i.component.id in ['back', 'front', 'preferred_track'],
                    timeout=10.0
                )
                if interaction.component.id == 'back':
                    current -= 1
                elif interaction.component.id == 'front':
                    current += 1
                elif interaction.component.id == 'preferred_track':
                    if (track := tracks[current]) is not None:
                        await message.delete()
                        return track

                if current == len(embeds):
                    current = 0
                elif current < 0:
                    current = len(embeds) - 1

                await interaction.respond(
                    type=InteractionType.UpdateMessage,
                    embed=embeds[current],
                    components=get_track_components(embeds, current)
                )
            except asyncio.TimeoutError:
                await message.delete()
                break

    async def _get_handlers_pagination(self, ctx: commands.Context, handlers):
        embeds = []

        for handler in HANDLERS_DATA:
            title = handler.get('title')
            description = handler.get('description')
            embed = Embed(title=title, description=description, color=BASE_COLOR)
            embed.add_field(name='Called by', value=ctx.author.mention)
            embeds.append(embed)

        current = 0
        message = await ctx.send(
            embed=embeds[current],
            components=get_handlers_components(embeds, current)
        )

        while True:
            try:
                interaction = await bot.wait_for(
                    'button_click',
                    check=lambda i: i.component.id in ['back', 'front', 'preferred_handler'],
                    timeout=10.0
                )
                if interaction.component.id == 'back':
                    current -= 1
                elif interaction.component.id == 'front':
                    current += 1
                elif interaction.component.id == 'preferred_handler':
                    if (handler := handlers[current]) is not None:
                        await message.delete()
                        return handler

                if current == len(embeds):
                    current = 0
                elif current < 0:
                    current = len(embeds) - 1

                await interaction.respond(
                    type=InteractionType.UpdateMessage,
                    embed=embeds[current],
                    components=get_handlers_components(embeds, current)
                )
            except asyncio.TimeoutError:
                await message.delete()
                break

    @commands.command(aliases=['p'])
    async def play(self, ctx: commands.Context, *query) -> None:
        """
        Plays the current song.
        """
        query = ' '.join(query)
        voice = ctx.voice_client
        if not voice:
            if not ctx.author.voice:
                await utils.send_embed(
                    ctx=ctx,
                    description='Connect to a voice channel first',
                    color=ERROR_COLOR
                )
                raise exceptions.UserNotConnected

            await ctx.author.voice.channel.connect()

        voice = ctx.voice_client
        q: Queue = self._queues[ctx.guild.id]
        q.play_next = True

        if query != '':
            if voice.is_playing():
                await self.queue(ctx, query)
                return

            if voice.is_paused():
                await voice.resume()
                await self.queue(ctx, query)
                return

            url, title = self._yt.get_info(query)

            q.add(url, title, ctx.author.mention)
            q.now_playing = len(q) - 1
            stream = self._yt.get_stream(url)
            loop = bot.loop
            await self._play(ctx, stream, loop)
        else:
            if voice.is_paused():
                voice.resume()
                return

            if not q.is_empty:
                res = q.get_next()
                if not res:
                    await utils.send_embed(
                        ctx=ctx,
                        description='The queue has ended',
                        color=BASE_COLOR
                    )
                    return
            else:
                await utils.send_embed(
                    ctx=ctx,
                    description='There are no songs in the queue',
                    color=ERROR_COLOR
                )
                raise exceptions.QueueEmpty

            stream = self._yt.get_stream(res[0])
            loop = bot.loop
            await self._play(ctx, stream, loop)

    def _after(self, ctx: commands.Context, loop: asyncio.AbstractEventLoop):
        q: Queue = self._queues[ctx.guild.id]
        if q.play_next:
            ctx.message.content = ''
            return asyncio.run_coroutine_threadsafe(self.play(ctx), loop)

    async def _play(self, ctx: commands.Context, stream, loop):
        voice = ctx.voice_client
        audio_source = discord.FFmpegPCMAudio(stream,
                                              before_options='-reconnect 1'
                                                             ' -reconnect_streamed 1'
                                                             ' -reconnect_delay_max 5')
        audio_source = discord.PCMVolumeTransformer(audio_source)
        voice.play(audio_source, after=lambda _: self._after(ctx, loop))
        await self.current(ctx)

    async def _get_track(self, ctx: commands.Context, query: str) -> tuple:
        if re.match(URL_REGEX, query):
            song = self._yt.get_info(query)
        else:
            tracks = list(await utils.run_blocking(self._yt.get_infos, bot, query=query))
            song = await self._choose_track(ctx, tracks)

        return song

    async def _choose_track(self, ctx: commands.Context, tracks):
        track = await self._get_tracks_pagination(ctx, tracks)

        if not track:
            return

        url, title, _ = track
        return url, title

    async def _choose_handler(self, ctx: commands.Context, handlers):
        return handler if (handler := await self._get_handlers_pagination(ctx, handlers)) is not None else None

    async def send_no_tracks_specified(self, ctx: commands.Context):
        await send_embed(description='No tracks were specified', color=BASE_COLOR, ctx=ctx)
        raise exceptions.NoTracksSpecified

    @commands.command(aliases=['q'])
    async def queue(self, ctx: commands.Context, *query) -> None:
        """
        Displays current queue.
        """
        q: Queue = self._queues[ctx.guild.id]
        query = ' '.join(query)
        if query:
            song = await self._get_track(ctx, query)
            
            if not song:
                await self.send_no_tracks_specified(ctx)

            if song is None:
                await send_embed('Canceled.', BASE_COLOR, ctx)
                return
            
            url, title = song

            q.add(url, title, ctx.author.mention)
            await utils.send_embed(
                ctx=ctx,
                description=f'Queued: [{title}]({url})',
                color=BASE_COLOR
            )
        else:
            if len(q) > 0:
                desc = ''
                for index, item in enumerate(q.queue):
                    url, title, mention = item
                    desc += f'{["", "now -> "][int(index == q.now_playing)]}' \
                            f'{index + 1}.\t[{title}]({url}) | {mention}\n'
            else:
                desc = 'There are no tracks in the queue for now!'

            await utils.send_embed(
                ctx=ctx,
                title='Current queue:',
                color=BASE_COLOR,
                description=desc
            )

    @commands.command(aliases=['clr'])
    async def clear(self, ctx: commands.Context):
        """
        Clears current queue.
        """
        q: Queue = self._queues[ctx.guild.id]
        q.clear()

        await utils.send_embed(
            ctx=ctx,
            description='Queue has been successfully cleared',
            color=BASE_COLOR
        )

    @commands.command()
    async def loop(self, cxt: commands.Context, option: str = ''):
        """
        Changes loop option to None, Queue or Track
        """
        loop_setting = ['None', 'Current queue', 'Current track']

        q: Queue = self._queues[cxt.guild.id]
        if option:
            q.loop = ['None', 'Queue', 'Track'].index(option.capitalize())
        else:
            q.loop += 1
            if q.loop > 2:
                q.loop = 0

        embed = discord.Embed(description=f'Now looping is set to: `{loop_setting[q.loop]}`',
                              color=BASE_COLOR)
        await cxt.send(embed=embed)

    @commands.command(aliases=['rm'])
    async def remove(self, ctx: commands.Context, index: int):
        """
        Removes a song from the queue by its index.
        """
        q: Queue = self._queues[ctx.guild.id]
        try:
            res = q.remove(index - 1)
        except IndexError:
            await utils.send_embed(
                ctx=ctx,
                description='No specified track in the queue.',
                color=ERROR_COLOR
            )
            return

        await utils.send_embed(
            ctx=ctx,
            description=f'Removed: [{res[1]}]({res[0]})',
            color=BASE_COLOR
        )

    @commands.command()
    async def seek(self, ctx: commands.Context, index: int):
        """
        Seeks a specified track with an index and plays it.
        """
        voice = ctx.guild.voice_client
        await self.stop()

        q: Queue = self._queues[ctx.guild.id]
        if 1 < index < len(q):
            q.now_playing = index - 1
        else:
            await send_embed(
                ctx=ctx,
                description=f'Index must be in range `1` to `len(q), not {index}`',
                color=ERROR_COLOR
            )

        while voice.is_playing():
            await asyncio.sleep(0.1)
        await self.play()

    @commands.command(aliases=['vol', 'v'])
    @commands.check(is_connected)
    async def volume(self, ctx: commands.Context, volume: float):
        """
        Adjusts the volume.
        """
        voice: discord.VoiceClient = ctx.voice_client
        if 0 > volume > 100:
            embed = discord.Embed(
                description=f'Volume must be in the range from `0` to `100`, not {volume}',
                color=ERROR_COLOR
            )
        else:
            voice.source.volume = volume / 100
            embed = discord.Embed(
                description=f'Volume has been successfully changed to `{volume}%`',
                color=BASE_COLOR
            )
        await ctx.send(embed=embed)

    @commands.command(aliases=['sch'])
    async def search(self, ctx: commands.Context, *query):
        """
        Searches for a song on YouTube and gives you 5 options to choose.
        """
        q: Queue = self._queues[ctx.guild.id]
        query = ' '.join(query)

        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()

        voice = ctx.voice_client

        tracks = list(await utils.run_blocking(self._yt.get_infos, bot, query=query))
        track = await self._choose_track(ctx, tracks)

        if not track:
            await self.send_no_tracks_specified(ctx)
        
        url, title = track

        q.add(url, title, ctx.author.mention)
        if not voice.is_playing():
            stream = self._yt.get_stream(url)
            loop = bot.loop
            await self._play(ctx, stream, loop)
        else:
            await utils.send_embed(
                ctx=ctx,
                description=f'Queued: [{title}]({url})',
                color=BASE_COLOR
            )

    @commands.command(aliases=['sh'])
    async def set_handler(self, ctx: commands.Context):
        handlers = [h.value for h in Handler]
        self.handler = await self._choose_handler(ctx, handlers)

        if self.handler == Handler.YTAPI.value:
            self._yt = YTAPIHandler(API_KEY)
        else:
            self._yt = YDLHandler({
                'simulate': True,
                'quiet': True,
                'format': 'bestaudio/best'
            })

        await ctx.send(f"The handler has been set to **{HANDLERS_DATA[self.handler].get('title')}**")
