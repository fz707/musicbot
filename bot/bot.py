# Code it all

from pathlib import Path

import discord
from discord.ext import commands


class MusicBot(commands.Bot):
    def __init__(self):
        # import the cogs from cogs file and path lib to get the cogs
        self._cogs = [p.stem for p in Path(".").glob("./bot/cogs/*.py")]
        super().__init__(command_prefix=self.prefix, 
        case_insensitive=True, 
        intents= discord.Intents.all())
        # makes it case insensitive
        

    def setup(self):
        print("running setup")
        for cog in self._cogs:
            # loads them in
            self.load_extension(f"bot.cogs.{cog}")
            print(f"loaded '{cog}' cog.")
        print("Setup complete")

    def run(self):
        self.setup()

        with open("data/token.0", "r", encoding="utf-8") as f:
            Token = f.read()
        print("running bot")
        # if bot disconencts reconet happens
        super().run(Token, reconnect=True)

    async def shutdown(self):
        print("Closing connection to discord..")
        await self.logout()

    async def close(self):
        print("closing on keyboard interrupt")
        await self.shutdown()

    async def on_connect(self):
        print("connected to discord")

    async def on_disconenct(self):
        print("disconnected to discord")
    
    async def on_error(self,err,*args,**kwargs):
        raise
    
    async def on_command_error(self,ctx,exc):
        raise getattr(exc,"original",exc)
        
    async def on_ready(self):
        self.client_id=(await self.application_info()).id
        print("bot ready")

    async def prefix(self,bot,msg):
        return commands.when_mentioned_or("%")(bot,msg)

    async def process_commands(self,msg):
        ctx= await self.get_context(msg, cls=commands.Context)

        if ctx.command is not None:
            await self.invoke(ctx)

    async def on_message(self,msg):
        if not msg.author.bot:
            await self.process_commands(msg)

