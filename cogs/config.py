import asyncio
import discord
from discord.ext import commands
import aiohttp
from ext import utils
from ext.paginator import PaginatorSession
import json


class Config(commands.Cog):
    """Customize your server with these config commands."""

    def __init__(self, bot):
        self.bot = bot
        self.bs_server_files = "https://www.github.com/I-Am-The-Great/BombSquad-Server/"

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def prefix(self, ctx, *, pre):
        """Set a custom prefix for the guild."""
        result = await self.bot.config.get_prefix(str(ctx.guild.id))
        await self.bot.config.update(str(ctx.guild.id), "prefix", str(pre))
        await ctx.send(
            f'The guild prefix has been set to `{pre}` from `{result}`.\n'
            f'Use `{pre}prefix <prefix>` to change it again.')

    @commands.group(invoke_without_command=True, aliases=["bs", "bs_server", "bs_stats"])
    async def bs_server_stats(self, ctx):
        """Use it if you want to set a BS server to get stats from or if you want to retrieve stats from current set."""
        em = discord.Embed(title="Using the server stats function.",
                           description=f"For using command to show your server's stats, you must be using the server "
                                       f"files from [This Github repository]({self.bs_server_files}).")
        em.add_field(name="Usage", value=f"`{ctx.prefix}bs_server_stats <option>`")
        em.add_field(name="Available options",
                     value=f"i) `set` to set a BombSquad game's server to retrieve stats data from.\n"
                           f"ii) `get <id>` to get the stats of the BombSquad server set for this guild by id.\n"
                           f"iii) `search <id> <search term>` to search a player by name in a party\'s stats.\n"
                           f"iv) `remove <id>` to remove an stats entry of your guild by id.\n"
                           f"v) `list` to list all entries for bs servers stats set in this server.")
        em.set_footer(text="You need to use the specific server files because this bot is made to work only with those "
                           "server file's generated stats files.")
        await ctx.send(embed=em)

    @bs_server_stats.command(aliases=["set"])
    @commands.has_permissions(manage_guild=True)
    async def add(self, ctx):
        """Use this command to set a BombSquad game's server to retrieve stats data from."""

        def msg(m):
            return m.author == ctx.author and m.channel == ctx.message.channel

        await ctx.send(
            "Ohk, now send the complete link of the .json file which stores stats of the BS server in 60 seconds."
            "The link must include auth details if there is any!")

        try:
            link = await self.bot.wait_for('message', check=msg, timeout=60.0)
        except asyncio.TimeoutError:
            return await ctx.send("You failed to give a valid message in time, think again and then restart.")

        if not (str(link.content).startswith("http") and str(link.content).__contains__("://")):
            return await ctx.send("You did not gave a link correctly, now restart.")

        await ctx.send("Ohk, now send the name of the BombSquad server.")

        try:
            name = await self.bot.wait_for('message', check=msg, timeout=60.0)
        except asyncio.TimeoutError:
            return await ctx.send("You failed to give a valid message in time, think again and then restart.")

        await ctx.send("Now send me a natural number that you want to be the id of this stats entry."
                       "(If you send an already used id it will be overridden)")

        try:
            sid = await self.bot.wait_for('message', check=msg, timeout=60.0)
        except asyncio.TimeoutError:
            return await ctx.send("You failed to give a valid message in time, think again and then restart.")

        data = {
            str(sid.content): {
                "name": str(name.content),
                "link": str(link.content)
            }
        }

        await self.bot.config.update(ctx.guild.id, "BSStats", str(json.dumps(data)))
        await ctx.send(f"This stats file entry has been successfully set, it's ID is {str(sid.content)}."
                       f"To get data from it use `{ctx.prefix}bs_stats get {str(sid.content)}")

    @bs_server_stats.command()
    async def get(self, ctx, set_id: str):
        """Use this command to get the stats of the BombSquad server set for this guild by id."""
        data = await self.bot.config.get_bstats(ctx.guild.id)
        name = data[set_id]["name"]
        link = data[set_id]["link"]
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as resp:
                json_data = json.loads(await resp.read())
        pages = []
        rank = 0
        try:
            for i in range(len(json_data)):
                rank += 1
                img_url = json_data[str(rank)]["icon_url"]
                p_name = json_data[str(rank)]["name"]
                em = discord.Embed(title=f"Player stats data for the {name} BombSquad server.")
                if rank == 1:
                    em.description = "1st ranker."
                if rank == 2:
                    em.description = "2nd ranker."
                if rank == 3:
                    em.description = "3rd ranker."
                else:
                    em.description = f"{rank}th ranker."
                em.set_author(name=f"{str(p_name)}", icon_url=img_url)
                em.set_thumbnail(url=img_url)
                for field in json_data[str(rank)]:
                    em.add_field(name=str(field), value=str(json_data[str(rank)][field]))
                pages.append(em)
        except KeyError:
            em = discord.Embed(title="The stats file has KeyError.",
                               description="The entry of the stats file is missing the `name` or the `icon_url` field.")
            em.set_author(name=self.bot.creator.name, url=self.bot.creator.url, icon_url=self.bot.creator.icon)
            em.add_field(name="Error in stats file",
                         value="Are you sure you are using the server files from [This Github repository]"
                               f"({self.bs_server_files})")
            return await ctx.send(embed=em)
        except Exception as e:
            print(e)
            em = discord.Embed(title="The stats file has error(s).",
                               description="Stats command is set to be used only by special servers (explained below).")
            em.set_author(name=self.bot.creator.name, url=self.bot.creator.url, icon_url=self.bot.creator.icon)
            em.add_field(name="Error in stats file",
                         value="Are you sure you are using the server files from [This Github repository]"
                               f"({self.bs_server_files})")
            em.set_footer(text=f"Contact <@{self.bot.creator.discord}> to resolve if you already use the server files.")
            return await ctx.send(embed=em)
        p_session = PaginatorSession(ctx,
                                     footer=f'Use the reactions of this message below to navigate between the data of'
                                            f' different rank holders.',
                                     pages=pages)
        await p_session.run()

    @bs_server_stats.command()
    async def search(self, ctx, set_id: str, *, search: str):
        """Use this command to search a player in the stats of the BombSquad server set for this guild by id."""
        data = await self.bot.config.get_bstats(ctx.guild.id)
        name = data[set_id]["name"]
        link = data[set_id]["link"]
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as resp:
                json_data = json.loads(await resp.read())
        pages = []
        rank = 0
        try:
            for i in range(len(json_data)):
                rank += 1
                img_url = json_data[str(rank)]["icon_url"]
                p_name = json_data[str(rank)]["name"]
                if str(p_name).lower().__contains__(search.lower()):
                    em = discord.Embed(title=f"Player stats data for the {name} BombSquad server .",
                                       description=f"Search results for `{search}` in the players stats.")
                    em.set_author(name=str(p_name), icon_url=str(img_url))
                    em.set_thumbnail(url=img_url)
                    pages.append(em)
        except KeyError:
            em = discord.Embed(title="The stats file has KeyError.",
                               description="The entry of the stats file is missing the `name` or the `icon_url` field.")
            em.set_author(name=self.bot.creator.name, url=self.bot.creator.url, icon_url=self.bot.creator.icon)
            em.add_field(name="Error in stats file",
                         value="Are you sure you are using the server files from [This Github repository]"
                               f"({self.bs_server_files})")
            return await ctx.send(embed=em)
        except Exception as e:
            print(e)
            em = discord.Embed(title="The stats file has error(s).",
                               description="Stats command is set to be used only by special servers (explained below).")
            em.set_author(name=self.bot.creator.name, url=self.bot.creator.url, icon_url=self.bot.creator.icon)
            em.add_field(name="Error in stats file",
                         value="Are you sure you are using the server files from [This Github repository]"
                               f"({self.bs_server_files})")
            em.set_footer(text=f"Contact <@{self.bot.creator.discord}> to resolve if you already use the server files.")
            return await ctx.send(embed=em)
        p_session = PaginatorSession(ctx,
                                     footer=f'Use the reactions of this message below to navigate between the data of'
                                            f' different rank holders.',
                                     pages=pages)
        await p_session.run()

    @bs_server_stats.command(aliases=["remove", "del"])
    @commands.has_permissions(manage_guild=True)
    async def delete(self, ctx, sid):
        """Use this command to get the stats of the BombSquad server set for this guild by id."""
        data = await self.bot.config.get_bstats(ctx.guild.id)
        if data.get(str(sid), None) is not None:
            data.pop(str(sid))
        else:
            return await ctx.send("Invalid ID no server stats set to retrieve from the given ID."
                                  f"Use `{ctx.prefix}bs_stats list` command to get a list of set bs server stats.")
        await self.bot.config.update(ctx.guild.id, "BSStats", data)
        await ctx.send(f"Ohk, successfully removed the BStats of ID {str(sid)} from this guild.")

    @bs_server_stats.command(aliases=["show", "all"])
    async def list(self, ctx, noembed: str = None):
        """Use this command to list all the BombSquad server stats set for this guild by id."""
        data = await self.bot.config.get_bstats(ctx.guild.id)
        if noembed is not None and str(noembed).endswith("noembed"):
            msg = "Following are all the BombSquad servers from which you can retrieve stats by ID:\n"
            for key in data.keys():
                name = str(data[key]["name"])
                msg += f"  - ID: {str(key)}, Name: {name} \n\n"
            for m in utils.paginate(msg):
                await ctx.send(m)
        else:
            em = discord.Embed(title="BombSquad servers list", description="All BS server from which you can get stats")
            for key in data.keys():
                name = str(data[key]["name"])
                em.add_field(name=key, value=name)
                em.set_footer(text="Use noembed attribute at the end of command to get a message without embed.")
            await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(Config(bot))
