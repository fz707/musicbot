import discord
from discord.ext import commands
import wavelink
import typing as ty
import asyncio
import re
from enum import Enum

URL_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"

OPTIONS = {
    "1️⃣": 0,
    "2⃣": 1,
    "3⃣": 2,
    "4⃣": 3,
    "5⃣": 4,
    "6⃣":5,
}
class AlreadyConectedToChannel(commands.CommandError):
    pass

class NoVoiceChannel(commands.CommandError):
    pass

class QueueIsEmpty(commands.CommandError):
    pass

class NoTracksFound(commands.CommandError):
    pass
class PlayerIsAlreadyPaused(commands.CommandError):
    pass
class PlayerIsNotAlreadyPaused(commands.CommandError):
    pass
class NoMoreTracks(commands.CommandError):
    pass

class Queue:
    def __init__(self):
        self._queue=[]
        self.position=0

    @property
    def is_empty(self):
        return not self._queue

    @property
    def current_track(self):
        if not self._queue:
            raise QueueIsEmpty
        #returns a list of the queue
        if self.position<=len(self._queue)-1:
            return self._queue[self.position]
    
    @property
    def upcoming(self):
        #upcoming song
        if not self._queue:
            raise QueueIsEmpty #empty queue
        #gets all songs on track
        return self._queue[self.position+1:]
    @property
    def history(self): #returns previous queued songs
        if not self._queue:
            raise QueueIsEmpty #empty queue
        return self._queue[:self.position]
    @property
    def length(self): #how long queue is
        return len(self._queue)

    def empty(self):
        self._queue.clear()

    def add(self,*args):
        self._queue.extend(args)

    def get_first_track(self):
        if not self._queue:
            raise QueueIsEmpty

        return self._queue[0]
    
    def get_next_track(self):
        if not self._queue:
            raise QueueIsEmpty
        self.position+=1
        if self.position<0:
            return None
        if self.position > len(self._queue)-1:
            return None

        return self._queue[self.position]

class Player(wavelink.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue= Queue()

    async def connect(self,ctx,channel=None):
        if self.is_connected:
            raise AlreadyConectedToChannel
        if(channel := getattr(ctx.author.voice, "channel",channel)) is None:
            raise NoVoiceChannel
        await super().connect(channel.id)
        return channel

    async def teardown(self):
        try:
            await self.destroy()
        except KeyError:
            pass

    async def add_tracks(self,ctx,tracks):
        if not tracks:
            raise NoTracksFound

        if isinstance(tracks, wavelink.TrackPlaylist):
            self.queue.add(*tracks.tracks)
        elif len(tracks)==1:
            self.queue.add(tracks[0])
            await ctx.send(f"Added {tracks[0].title} to the queue")
        else:
            if (track := await self.choose_track(ctx,tracks)) is not None:
                self.queue.add(track)
                await ctx.send(f"{track.title} has been added to queue!")
        if not self.is_playing and not self.queue.is_empty:
            await self.start_playback()
    
    async def choose_track(self,ctx,tracks):
        def _check(r,u):
            return (
                r.emoji in OPTIONS.keys()
                and u==ctx.author
                and r.message.id==msg.id
            )
        embed=discord.Embed(
            title="Choose a song",
            description=(
                "\n".join(
                    f"**{i+1}.** {t.title} ({t.length//60000}:{str(t.length%60).zfill(2)})"
                    for i, t in enumerate(tracks[:6])
                )
            ),
            colour=ctx.author.colour
        )
        embed.set_author(name="Query Results")
        embed.set_footer(
            text=f"Invoked by {ctx.author.display_name}",
         icon_url=ctx.author.avatar_url)

        msg=await ctx.send(embed=embed)
        for emoji in list(OPTIONS.keys())[:min(len(tracks),len(OPTIONS))]:
            await msg.add_reaction(emoji)
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=75.0, check=_check)

        except asyncio.TimeoutError:
            await msg.delete()
            await ctx.message.delete()

        else:
            await msg.delete()
            return tracks[OPTIONS[reaction.emoji]]

    async def start_playback(self):
        await self.play(self.queue.current_track)

    async def advance(self):
        try:
            if(track:= self.queue.get_next_track()) is not None:
                await self.play(track)
        except QueueIsEmpty:
            pass
class Music(commands.Cog, wavelink.WavelinkMixin):
    def __init__(self, bot):
        self.bot = bot
        self.wavelink = wavelink.Client(bot=bot)
        self.bot.loop.create_task(self.start_nodes())

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not member.bot and after.channel is None:
            #await asyncio.sleep(300)
            if not [m for m in before.channel.members if not m.bot]:
                await self.get_player(member.guild).teardown()# disconnect bot

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self,node):
        print(f"Wavelink node '{node.identifier}' ready")
    
    @wavelink.WavelinkMixin.listener("on_track_stuck")

    @wavelink.WavelinkMixin.listener("on_track_end")

    @wavelink.WavelinkMixin.listener("on_track_exception")

    async def on_player_stop(self,node,payload):
        await payload.player.advance()

    async def cog_check(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("DM commands don't exist right now")
            return False
        return True

    async def start_nodes(self):
        await self.bot.wait_until_ready()

        nodes = {
            "MAIN": {
                "host": "127.0.0.1",
                "port": 2333,
                "rest_uri": "http://127.0.0.1:2333",
                "password": "youshallnotpass",
                "identifier": "MAIN",
                "region": "us_central",
            }
        }
        for node in nodes.values():
            await self.wavelink.initiate_node(**node)

    def get_player(self, obj):
        if isinstance(obj, commands.Context):
            return self.wavelink.get_player(obj.guild.id, cls=Player, context=obj)
        elif isinstance(obj, discord.Guild):
            return self.wavelink.get_player(obj.id, cls=Player)
    
    @commands.command(name="connect",aliases=["join,sum"])
    async def connect_command(self, ctx,*,channel:ty.Optional[discord.VoiceChannel]):
        player=self.get_player(ctx)
        channel=await player.connect(ctx,channel)
        await ctx.send(f"Connected to {channel.name}.")
    
    @connect_command.error
    async def connect_command_error(self,ctx,exc):
        if isinstance(exc,AlreadyConectedToChannel):
            await ctx.send("Already connected")
        elif isinstance(exc,NoVoiceChannel):
            await ctx.send("No suitable voice channel was provided.")

    @commands.command(name="disconnect")
    async def disconnect_command(self,ctx):
        player=self.get_player(ctx)
        await player.teardown()
        await ctx.send("Disconnected")
    
    @commands.command(name="play", aliases=["p"])
    async def play_command(self,ctx,*,query: ty.Optional[str]):
        player=self.get_player(ctx)

        if not player.is_connected:
            await player.connect(ctx)
        
        if query is None:
            if player.queue.is_empty:
                raise QueueIsEmpty

            if not player.is_paused:
                raise PlayerIsNotAlreadyPaused

            await player.set_pause(False)
            await ctx.send("Song resumed.")
        else:
            query=query.strip("<>")
            if not re.match(URL_REGEX,query):
                query=f"ytsearch:{query}"
            await player.add_tracks(ctx, await self.wavelink.get_tracks(query))
    @commands.command(name="skip",aliases=["next","s"])
    async def skip_command(self,ctx):
        player=self.get_player(ctx)

        if not player.queue.upcoming:
            raise NoMoreTracks
        
        await player.advance()
        await ctx.send("Play next track in queue")

    @skip_command.error
    async def skip_command_error(self,ctx,exc):
        if isinstance(exc,QueueIsEmpty):
            await ctx.send("No more songs in queue.")
        elif isinstance(exc,NoMoreTracks):
            await ctx.send("No more songs in queue.")

    @commands.command(name="pause")
    async def pause_command(self,ctx):
        player=self.get_player(ctx)
        if player.is_paused:
            raise PlayerIsAlreadyPaused

        await player.set_pause(True)
        await ctx.send("Song paused.")


    @pause_command.error
    async def pause_command_error(self,ctx,exc):
        if isinstance(exc,PlayerIsAlreadyPaused):
            await ctx.send("Song is already paused.")

    @commands.command(name="resume")
    async def resume_command(self,ctx):
        player=self.get_player(ctx)
        if not player.is_paused:
            raise PlayerIsNotAlreadyPaused

        if player.queue.is_empty:
                raise QueueIsEmpty

        await player.set_pause(False)
        await ctx.send("Song resumed.")

    @resume_command.error
    async def resume_command_error(self,ctx,exc):
        if isinstance(exc,PlayerIsNotAlreadyPaused):
            await ctx.send("Song is already resumed.")



    @commands.command(name="queue",aliases=["q"])
    async def queue_viewer(self,ctx,show:ty.Optional[int]=8):
        player=self.get_player(ctx)

        if player.queue.is_empty:
            raise QueueIsEmpty

        embed=discord.Embed(
            title="View the Queue",
            description="Showing the Queue!",
            colour=ctx.author.colour
        )
        embed.set_author(name="Query Results")
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", 
        icon_url=ctx.author.avatar_url)
        embed.add_field(name="Currently Playing",
         value=getattr(player.queue.current_track,"title", "No tracks playing"),
        inline=False)
        if upcoming := player.queue.upcoming: #if not empty list and assign with walrus 
            embed.add_field(
                name="Next up",
                value="\n".join(f.title for f in upcoming[:show])
            )
        msg=await ctx.send(embed=embed)


    @queue_viewer.error
    async def queue_viewer_error(self,ctx,exc):
        if isinstance(exc,QueueIsEmpty):
            await ctx.send("The queue has nothing in it.")

def setup(bot):
    bot.add_cog(Music(bot))
