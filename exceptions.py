from discord.ext import commands


class AlreadyConnected(commands.CommandError):
    """
    Occurs when the bot is already connected to the channel.
    """
    pass


class UserNotConnected(commands.CommandError):
    """
    Occurs when a user isn't connected to a voice channel.
    """
    pass


class AlreadyPlaying(commands.CommandError):
    """
    Occurs when the audio is already playing.
    """
    pass


class NoMoreTracks(commands.CommandError):
    """
    Occurs when there are no more tracks in the queue.
    """
    pass


class NoTracksBefore(commands.CommandError):
    """
    Occurs when there are no previous tracks.
    """
    pass


class QueueEmpty(commands.CommandError):
    """
    Occurs when the queue is empty.
    """
    pass


class AlreadyPaused(commands.CommandError):
    """
    Occurs when the player is already paused, but the user is trying to pause it one more time.
    """
    pass


class BotNotConnected(commands.CommandError):
    """
    Occurs when the bot isn't connected to a voice channel yet.
    """
    pass


class TimeoutExceeded(commands.CommandError):
    """
    Occurs, when a user chooses one of the songs more than 1 minute.
    """
    pass


class NoTracksSpecified(commands.CommandError):
    """
    Occurs, when a user didn't specify any suggested tracks.
    """
    pass


class HandlerNotSpecified(commands.CommandError):
    """
    Occurs, when a user didn't specify one of the handlers, whether it's Spotify, YouTube DL or YouTube API.
    """
    pass
