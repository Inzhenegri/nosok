# The technical reference of the project

1. The database is Postgres
2. Run the project in a docker image
3. Use GH Actions

## List of all commands
All the commands start from the `!` prefix.
1. `skip`. Allows a user to skip the track.
2. `seek`. The command is used for searching a certain track in the queue.
3. `search`. This is a customized `play` command that can display the first five tracks that were found on YouTube by your query. For this purpose use the discord.py's pagination.
4. `join`. Makes the bot join a voice channel.
5. `leave`. Makes bot leave your current channel.
6. `loop`. Changes loop option to None, Queue or Track.
7. `pause`. Pauses current song. Use command `play` to resume.
8. `play`. Plays current song.
9. `queue`. Displays current queue.
10. `remove`. Removes a song from queue by index.
11. `stop`. Stops bot from playing current song.
12. `set_prefix`. Sets the prefix for the server.
13. `set_handler`. Sets the preferred handler, whether it's YTAPI or YDL.