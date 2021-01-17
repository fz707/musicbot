
from datetime import datetime, timedelta
from random import randint
from typing import Optional

from discord import Member, Embed
from discord.ext.commands import Cog
from discord.ext.commands import CheckFailure
from discord.ext.commands import command, has_permissions
from discord.ext.menus import MenuPages, ListPageSource

from .db import db


class Exp(Cog):
    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.levelup_channel = self.bot.get_channel(704457333681422497)
            self.bot.cogs_ready.ready_up("exp")

        def __init__(self, bot):
            self.bot = bot

        @Cog.listener()
        async def on_message(self, message):
            if not message.author.bot:
                await self.process_xp(message)

        async def process_xp(self, message):
            xp, lvl, xplock = db.record(
                "SELECT XP, Level, XPLock FROM exp WHERE UserID = ?", message.author.id)

            if datetime.utcnow() > datetime.fromisoformat(xplock):
                await self.add_xp(message, xp, lvl)

        async def add_xp(self, message, xp, lvl):
            xp_to_add = randint(10, 20)
            new_lvl = int(((xp+xp_to_add)//42) ** 0.55)

            db.execute("UPDATE exp SET XP = XP + ?, Level = ?, XPLock = ? WHERE UserID = ?",
                       xp_to_add, new_lvl, (datetime.utcnow()+timedelta(seconds=60)).isoformat(), message.author.id)

            if new_lvl > lvl:
                await self.levelup_channel.send(f"Congrats {message.author.mention} - you reached level {new_lvl:,}!")
                await self.check_lvl_rewards(message, new_lvl)


def setup(bot):
    bot.add_cog(Exp(bot))
