import functools
import typing

import discord
from discord.ext import commands
from discord_components import Button, ButtonStyle

import exceptions
from base import ERROR_COLOR


async def send_embed(description: str, color: discord.Colour, ctx: commands.Context, title: str = ''):
    embed = discord.Embed(
        description=description,
        color=color
    )
    message = await ctx.send(embed=embed)
    return message


async def is_connected(ctx: commands.Context):
    if ctx.invoked_with == 'help' or ctx.voice_client:
        return True

    await send_embed(
        ctx=ctx,
        description='I am not connected to a voice channel yet!',
        color=ERROR_COLOR
    )
    raise exceptions.BotNotConnected


async def run_blocking(blocking_func: typing.Callable, bot: commands.Bot, *args, **kwargs) -> typing.Any:
    func = functools.partial(blocking_func, *args, **kwargs)
    return await bot.loop.run_in_executor(None, func)


def get_track_components(embeds, current):
    return [
        [
            Button(label='Prev', id='back', style=ButtonStyle.red),
            Button(
                label=f'Page {int(embeds.index(embeds[current])) + 1}/{len(embeds)}',
                id='cur',
                style=ButtonStyle.grey,
                disabled=True
            ),
            Button(
                label='Next',
                id='front',
                style=ButtonStyle.red
            )
        ],
        [
            Button(
                label='That one',
                id='preferred_track',
                style=ButtonStyle.green
            )
        ]
    ]


def get_handlers_components(embeds, current):
    return [
        [
            Button(label='Prev', id='back', style=ButtonStyle.red),
            Button(
                label=f'Page {int(embeds.index(embeds[current])) + 1}/{len(embeds)}',
                id='cur',
                style=ButtonStyle.grey,
                disabled=True
            ),
            Button(
                label='Next',
                id='front',
                style=ButtonStyle.red
            )
        ],
        [
            Button(
                label='I want this one',
                id='preferred_handler',
                style=ButtonStyle.green
            )
        ]
    ]
