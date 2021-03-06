import discord
import os
import re
import requests
from bs4 import BeautifulSoup
from discord.ext import commands
import random
import DiscordUtils
from tinydb import TinyDB, Query
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

sched = AsyncIOScheduler()
sched.start()

description = '''A bot to handle album club command.'''

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix=['ac!', 'AC!', 'Ac!', 'aC!'], description=description, intents=intents)
db = TinyDB('db.json')

status_table = db.table('status')
theme_table = db.table('theme')
nom_table = db.table('nominations')

def date_time_str_converter(dt_str: str):
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f")

def get_user_mention(ctx):
    return ctx.author.mention.strip().replace('!','')

async def ping_channel():
    channel = bot.get_channel(552239880042971139)
    await channel.send(f"<@&808513468339716137> time to discuss this weeks album {get_current_nomination()}")
    # sched.add_job(ping_channel, 'date', run_date=(get_next_sunday_datetime().replace(hour=19, minute=30, second=0)))

def get_last_sunday_datetime(from_date = datetime.now()):
    idx = (from_date.weekday() + 1) % 7
    return from_date - timedelta(idx)

def set_theme_date(theme):
    status = Query()
    if (status_table.get(status.key == 'theme')):
        status_table.update({ 'value': theme }, status.key == 'theme')
    else:
        status_table.insert({ 'key': 'theme', 'value': theme })

def get_theme_date():
    theme = Query()
    ret = status_table.get(theme.key == 'theme_date')
    return ret['value'] if ret else None

def get_last_sunday(from_date = datetime.now()):
    return get_last_sunday_datetime().strftime("%m/%d/%Y")

def get_next_sunday_datetime(from_date = datetime.now()):
    idx = (from_date.weekday() + 1) % 7
    return from_date + timedelta(7 - idx)

@bot.event
async def on_message(message):
    enable_pepe_replies = False
    if enable_pepe_replies and bot.user.mention in message.content.split():
        pepe_url = 'https://rare-pepe.com'
        response = requests.get(pepe_url)
        if response:
            soup = BeautifulSoup(response.text, 'html.parser')
            attrs = { 'src': re.compile(r'https://rare-pepe.com/wp-content/uploads/.*png') }
            rare_pepe_src = random.choice(soup.find_all('img', attrs=attrs)).attrs['src']
            await message.channel.send(rare_pepe_src)
        else:
            await message.channel.send('no pepe for u')
    await bot.process_commands(message)

@bot.command()
async def sunday(ctx):
    await ctx.send(get_last_sunday())

def set_current_theme(theme: str):
    status = Query()
    if (status_table.get(status.key == 'theme')):
        status_table.update({ 'value': theme }, status.key == 'theme')
    else:
        status_table.insert({ 'key': 'theme', 'value': theme })

def get_current_theme():
    theme = Query()
    ret = status_table.get(theme.key == 'theme')
    return ret['value'] if ret else None

def add_theme(name: str, user: str):
    theme_table.insert({ 'name': name, 
                         'user': user, 
                         'timestamp': str(datetime.now()), 
                         'selected': False })

def remove_theme(name: str):
    remove = Query()
    theme_table.remove(remove.name == name)

def theme_exists(name: str):
    theme = Query()
    return theme_table.get(theme.name == name) is not None

def get_unselected_themes():
    theme = Query()
    return theme_table.search(theme.selected == False)

@bot.group(aliases=['t'])
async def theme(ctx):
    pass

@theme.command(name='add')
async def theme_add(ctx, *, args):
    theme = args.strip()
    if theme:
        add_theme(args.strip(), ctx.author.mention)
        await ctx.send(f"{theme} added.")

@theme.command(name='remove')
async def theme_remove(ctx, *, args):
    theme = args.strip()
    if theme:
        remove_theme(args.strip())
        await ctx.send(f"{theme} removed.")

@theme.command(name='get')
async def theme_get(ctx):
    out = ""
    count = 0
    themes = get_unselected_themes()
    for theme in themes:
        count += 1
        out += f"{count}. {theme['name']}\n"
    if count > 0:
        await ctx.send(out)
    else:
        await ctx.send("There aren't any themes.")

@theme.command(name='history')
async def theme_history(ctx):
    out = ""
    count = 0
    themes = theme_table.all()
    for theme in themes:
        count += 1
        out += f"{count}. {theme['name']}\n"
    if count > 0:
        await ctx.send(out)
    else:
        await ctx.send("There aren't any themes.")

@theme.command(name='current')
async def theme_current(ctx):
    theme = get_current_theme()
    if theme:
        await ctx.send(f"The current theme is {theme}")
    else:
        await ctx.send("A theme has not been chosen. Use the <theme pick> command.")

@theme.command(name='pick', aliases=['select'])
async def theme_pick(ctx, *, args):
    theme = args.strip()
    if theme_exists(theme):
        set_current_theme(theme)
        await ctx.send(f"{theme} is now the current theme.")
    else:
        await ctx.send("That theme has not been added. Add it first.")

def add_nomination(album: str, artist: str, user: str):
    nom_table.insert({   'album': album, 
                         'artist': artist, 
                         'user': user, 
                         'theme': get_current_theme(), 
                         'selected': False })

def remove_nomination(album: str, artist: str, user: str):
    remove = Query()
    nom_table.remove((remove.album == album) & 
                     (remove.artist == artist) & 
                     (remove.user == user) &
                     (remove.theme == get_current_theme))

def get_nominations_for_this_week():
    album = Query()
    return nom_table.search(album.week == get_last_sunday())

def get_nominations_for_this_theme():
    album = Query()
    return nom_table.search(album.theme == get_current_theme())

def mark_nomination_as_selected(nom):
    album = Query()
    nom_table.update({'selected': True},
        (album.album == nom['album']) &
        (album.artist == nom['artist']) &
        (album.user == nom['user']))

def nomination_by_user(album: str, artist: str, user: str):
    nom = Query()
    user_nom = nom_table.search((nom.album == album) & (nom.artist == artist) & (nom.user == user))
    return user_nom is not None

def user_already_has_two(user: str):
    nom = Query()
    user_noms = nom_table.search((nom.user == user) & (nom.theme == get_current_theme()))
    return user_noms is not None and len(user_noms) == 2

def user_has_nomination(album: str, artist: str, user: str):
    nom = Query()
    user_noms = nom_table.search((nom.user == user) & 
                                 (nom.theme == get_current_theme()) &
                                 (nom.album == album) &
                                 (nom.artist == artist))
    return user_noms is not None and len(user_noms) >= 1

def set_current_nomination(new_nom):
    nom = Query()
    if (status_table.get(nom.key == 'nom')):
        status_table.update({ 'value': new_nom['album'] }, nom.key == 'nom')
    else:
        status_table.insert({ 'key': 'nom', 'value': new_nom['album'] })

def get_current_nomination():
    nom = Query()
    ret = status_table.get(nom.key == 'nom')
    return ret['value'] if ret else None

@bot.group(aliases=['n', 'nom'])
async def nomination(ctx):
    pass

@nomination.command(name='add')
async def nomination_add(ctx, *, args):
    nom = args.strip()
    if '-' in nom:
        album, artist = nom.split('-')
        album = album.strip()
        artist = artist.strip()
        if user_already_has_two(get_user_mention(ctx)):
            await ctx.send('You already have two nominations. Remove one first.')
        else:
            add_nomination(album, artist, get_user_mention(ctx))
            await ctx.send(f"{album} by {artist} added")
    else:
        await ctx.send('Invalid nomination, use: ac!nomination add <album> - <artist>')

@nomination.command(name='remove', aliases=['delete'])
async def nomination_delete(ctx, *, args):
    nom = args.strip()
    if '-' in nom:
        album, artist = nom.split('-')
        album = album.strip()
        artist = artist.strip()
        user = get_user_mention(ctx)
        if user_has_nomination(album, artist, user):
            remove_nomination(album, artist, user)
            await ctx.send(f'{album} by {artist} removed')
        else:
            await ctx.send(f'Cannot not remove {album}. You did not nominate it.')
    else:
        await ctx.send('Invalid nomination, use: ac!nomination remove <album> - <artist>')

@nomination.command(name='get')
async def nomination_get(ctx):
    out = ""
    count = 0
    this_themes_choices = get_nominations_for_this_theme()
    already_selected_users = [album['user'] for album in this_themes_choices if album['selected']]
    this_themes_choices = [album for album in this_themes_choices if album['user'] not in already_selected_users]
    for nom in this_themes_choices:
        count += 1
        out += f"{count}. {nom['album']} - {nom['artist']}\n"

    if count > 0:
        await ctx.send(out)
    else:
        await ctx.send("There aren't any nominations.")

@nomination.command(name='current')
async def nomination_current(ctx):
    nomination = get_current_nomination()
    if nomination:
        await ctx.send(f"The current album is {nomination}")
    else:
        await ctx.send("An album has not been chosen. Use the <nomination select> command.")

@nomination.group(name='history')
async def nomination_history(ctx):
    embeds = []
    nom_count = 0
    nom_per_embed = 10
    album_list_str = ""
    artist_list_str = ""
    for nom in nom_table.all():
        album_list_str += f"{nom['album']}\n"
        artist_list_str += f"{nom['artist']}\n"
        nom_count += 1
        if nom_count % nom_per_embed == 0:
            new_embed = discord.Embed()
            new_embed.add_field(name="Album", value=album_list_str[:-1], inline=True)
            new_embed.add_field(name="Artist", value=artist_list_str[:-1], inline=True)
            embeds.append(new_embed)
            nom_count = 0
            album_list_str = ""
            artist_list_str = ""
    if nom_count > 0:
        new_embed = discord.Embed()
        new_embed.add_field(name="Album", value=album_list_str[:-1], inline=True)
        new_embed.add_field(name="Artist", value=artist_list_str[:-1], inline=True)
        embeds.append(new_embed)
    paginator = DiscordUtils.Pagination.AutoEmbedPaginator(ctx)
    await paginator.run(embeds)

@nomination.command(name='select', aliases=['pick'])
async def nomination_select(ctx):
    this_themes_choices = get_nominations_for_this_theme()
    already_selected_users = [album['user'] for album in this_themes_choices if album['selected']]
    this_themes_choices = [album for album in this_themes_choices if album['user'] not in already_selected_users]
    if this_themes_choices is not None and len(this_themes_choices) > 0:
        choice = random.choice(this_themes_choices)
        artist = choice['artist']
        album = choice['album']
        user = choice['user']
        mark_nomination_as_selected(choice)
        set_current_nomination(choice)
        await ctx.send(f"{album} by {artist}, nominated by {user}")
    else:
        await ctx.send("There are no more albums to select from this week.")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print('------')

def main(args=None):
    # sched.add_job(ping_channel, 'date', run_date=(get_next_sunday_datetime().replace(hour=19, minute=30, second=0)))
    bot.run(os.getenv('DISCORD_TOKEN'))

if __name__ == "__main__":
    main()