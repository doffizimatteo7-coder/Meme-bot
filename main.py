import discord
from discord import app_commands
from discord.ext import commands
import os, json, random, asyncio, re
from datetime import timedelta, datetime
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- DATABASE SEMPLICE ----------
# Salva setup per server in config.json
if os.path.exists("config.json"):
    with open("config.json", "r") as f:
        CONFIG = json.load(f)
else:
    CONFIG = {}

def get_guild_config(guild_id):
    gid = str(guild_id)
    if gid not in CONFIG:
        CONFIG[gid] = {
            "banned_words": [],
            "anti_link": False,
            "log_channel": None,
            "anti_spam_seconds": 0.5, # default
            "anti_spam_enabled": True
        }
    return CONFIG[gid]

def save_config():
    with open("config.json", "w") as f:
        json.dump(CONFIG, f, indent=4)

# Per anti-spam: {user_id: [timestamp, timestamp...]}
user_messages = {}

# Per gioco bandiere
flag_game = {} # {channel_id: {"answer": "Italia", "active": True, "winner": None}}

FLAGS_EASY = {
    "🇮🇹": "Italia",
    "🇫🇷": "Francia",
    "🇪🇸": "Spagna",
    "🇩🇪": "Germania",
    "🇬🇧": "Regno Unito",
    "🇺🇸": "Stati Uniti",
    "🇧🇷": "Brasile",
    "🇯🇵": "Giappone",
}
FLAGS_MEDIUM = {
    "🇨🇦": "Canada",
    "🇦🇺": "Australia",
    "🇲🇽": "Messico",
    "🇦🇷": "Argentina",
    "🇨🇳": "Cina",
    "🇰🇷": "Corea del Sud",
    "🇪🇬": "Egitto",
    "🇳🇱": "Paesi Bassi",
}
FLAGS_HARD = {
    "🇳🇴": "Norvegia",
    "🇫🇮": "Finlandia",
    "🇵🇱": "Polonia",
    "🇹🇷": "Turchia",
    "🇹🇭": "Thailandia",
    "🇻🇳": "Vietnam",
    "🇰🇪": "Kenya",
    "🇨🇱": "Cile",
}

async def send_log(guild, embed):
    cfg = get_guild_config(guild.id)
    ch_id = cfg.get("log_channel")
    if not ch_id:
        return
    ch = guild.get_channel(ch_id)
    if ch:
        await ch.send(embed=embed)

# ---------- EVENTI ----------

@bot.event
async def on_ready():
    print(f"Bot online come {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizzati {len(synced)} comandi")
    except Exception as e:
        print(e)

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    cfg = get_guild_config(message.guild.id)
    content_lower = message.content.lower()

    # --- 1. ANTI LINK INVITO ---
    if cfg.get("anti_link"):
        # Cerca link discord.gg / discord.com/invite
        if re.search(r"(discord\.gg/|discord\.com/invite/|discordapp\.com/invite/)", content_lower):
            try:
                await message.delete()
            except: pass
            try:
                await message.author.timeout(timedelta(days=1), reason="Anti-Link: ha mandato un invito")
                embed = discord.Embed(title="🔗 Anti-Link - Timeout 1 giorno", color=discord.Color.red(), timestamp=datetime.now())
                embed.add_field(name="Utente", value=f"{message.author.mention} ({message.author})", inline=False)
                embed.add_field(name="Messaggio", value=message.content[:1000], inline=False)
                embed.add_field(name="Canale", value=message.channel.mention, inline=False)
                await send_log(message.guild, embed)
                await message.channel.send(f"{message.author.mention} ha mandato un link invito -> timeout 1 giorno!", delete_after=5)
            except Exception as e:
                print(e)
            return

    # --- 2. DIVIETO PAROLA ---
    for parola in cfg.get("banned_words", []):
        if parola.lower() in content_lower:
            try:
                await message.delete()
            except: pass
            embed = discord.Embed(title="🚫 Parola vietata eliminata", color=discord.Color.orange(), timestamp=datetime.now())
            embed.add_field(name="Utente", value=f"{message.author.mention}", inline=False)
            embed.add_field(name="Parola vietata", value=f"||{parola}||", inline=False)
            embed.add_field(name="Messaggio", value=message.content[:1000], inline=False)
            embed.add_field(name="Canale", value=message.channel.mention, inline=False)
            await send_log(message.guild, embed)
            return

    # --- 3. ANTI SPAM ---
    if cfg.get("anti_spam_enabled"):
        now = asyncio.get_event_loop().time()
        uid = message.author.id
        limit = cfg.get("anti_spam_seconds", 0.5)
        if uid not in user_messages:
            user_messages[uid] = []
        user_messages[uid].append(now)
        # Tieni solo gli ultimi 5 messaggi
        user_messages[uid] = [t for t in user_messages[uid] if now - t < 5]
        # Se manda 5 messaggi in meno di (limit * 5) secondi -> spam
        if len(user_messages[uid]) >= 5:
            # Controlla velocità media
            if user_messages[uid][-1] - user_messages[uid][0] < limit * 5:
                user_messages[uid] = []
                try:
                    await message.author.timeout(timedelta(hours=1), reason="Anti-Spam")
                    await message.channel.send(f"{message.author.mention} spam -> timeout 1 ora!", delete_after=5)
                    embed = discord.Embed(title="⏱️ Anti-Spam - Timeout 1 ora", color=discord.Color.red(), timestamp=datetime.now())
                    embed.add_field(name="Utente", value=f"{message.author.mention}", inline=False)
                    embed.add_field(name="Motivo", value=f"Troppi messaggi veloci (limite {limit}s)", inline=False)
                    await send_log(message.guild, embed)
                except: pass
                return

    # --- 4. GIOCO BANDIERE ---
    ch_id = message.channel.id
    if ch_id in flag_game and flag_game[ch_id]["active"]:
        risposta_giusta = flag_game[ch_id]["answer"].lower().strip()
        if content_lower.strip() == risposta_giusta:
            flag_game[ch_id]["active"] = False
            await message.channel.send(f"🎉 **{message.author.mention} ha indovinato!** La bandiera era **{flag_game[ch_id]['answer']}**")
            return

    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild:
        return
    embed = discord.Embed(title="🗑️ Messaggio eliminato", color=discord.Color.dark_grey(), timestamp=datetime.now())
    embed.add_field(name="Utente", value=f"{message.author.mention} ({message.author})", inline=False)
    embed.add_field(name="Canale", value=message.channel.mention, inline=False)
    embed.add_field(name="Contenuto eliminato", value=message.content[:1000] or "*Nessun testo*", inline=False)
    await send_log(message.guild, embed)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild:
        return
    if before.content == after.content:
        return
    embed = discord.Embed(title="✏️ Messaggio modificato", color=discord.Color.blue(), timestamp=datetime.now())
    embed.add_field(name="Utente", value=f"{before.author.mention}", inline=False)
    embed.add_field(name="Canale", value=before.channel.mention, inline=False)
    embed.add_field(name="Prima", value=before.content[:1000] or "*Vuoto*", inline=False)
    embed.add_field(name="Dopo", value=after.content[:1000] or "*Vuoto*", inline=False)
    embed.add_field(name="Vai al messaggio", value=f"[Clicca qui]({after.jump_url})", inline=False)
    await send_log(before.guild, embed)

@bot.event
async def on_member_ban(guild, user):
    embed = discord.Embed(title="🔨 Ban", color=discord.Color.red(), timestamp=datetime.now())
    embed.add_field(name="Utente bannato", value=f"{user.mention} ({user})", inline=False)
    await send_log(guild, embed)

@bot.event
async def on_member_update(before, after):
    # Log timeout
    if before.timed_out_until != after.timed_out_until and after.timed_out_until is not None:
        embed = discord.Embed(title="⏳ Timeout dato", color=discord.Color.gold(), timestamp=datetime.now())
        embed.add_field(name="Utente", value=f"{after.mention}", inline=False)
        embed.add_field(name="Fino a", value=str(after.timed_out_until), inline=False)
        await send_log(after.guild, embed)

# ---------- COMANDI ----------

@bot.tree.command(name="divieto", description="Aggiungi una parola vietata (solo admin)")
@app_commands.describe(parola="La parola da vietare")
async def divieto(interaction: discord.Interaction, parola: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Solo gli amministratori possono usare questo comando!", ephemeral=True)
        return
    cfg = get_guild_config(interaction.guild.id)
    parola = parola.lower().strip()
    if parola in cfg["banned_words"]:
        await interaction.response.send_message(f"La parola `{parola}` è già vietata.", ephemeral=True)
        return
    cfg["banned_words"].append(parola)
    save_config()
    await interaction.response.send_message(f"✅ Parola vietata aggiunta: `{parola}`\nChi la scrive, il messaggio verrà eliminato.")

@bot.tree.command(name="setup", description="Setup del bot (solo admin)")
@app_commands.describe(
    anti_link="Attiva o disattiva anti-link",
    canale_log="Canale dove mandare i log",
    anti_spam_secondi="Secondi tra messaggi per anti-spam, es 0.5"
)
async def setup(interaction: discord.Interaction, anti_link: bool = None, canale_log: discord.TextChannel = None, anti_spam_secondi: float = None):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Solo gli amministratori!", ephemeral=True)
        return
    cfg = get_guild_config(interaction.guild.id)
    msg = "⚙️ **Setup aggiornato:**\n"
    if anti_link is not None:
        cfg["anti_link"] = anti_link
        msg += f"- Anti-Link: {'✅ Attivato' if anti_link else '❌ Disattivato'} (timeout 1 giorno se manda invito)\n"
    if canale_log is not None:
        cfg["log_channel"] = canale_log.id
        msg += f"- Canale log: {canale_log.mention}\n"
    if anti_spam_secondi is not None:
        cfg["anti_spam_seconds"] = anti_spam_secondi
        cfg["anti_spam_enabled"] = True
        msg += f"- Anti-Spam: {anti_spam_secondi}s tra messaggi -> timeout 1 ora\n"
    save_config()
    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="flag", description="Indovina la bandiera! Solo i membri possono giocare")
@app_commands.describe(difficolta="facile, media, difficile")
@app_commands.choices(difficolta=[
    app_commands.Choice(name="facile", value="facile"),
    app_commands.Choice(name="media", value="media"),
    app_commands.Choice(name="difficile", value="difficile"),
])
async def flag(interaction: discord.Interaction, difficolta: str):
    # Solo membri, non admin obbligatorio, tutti possono giocare
    if difficolta == "facile":
        pool = FLAGS_EASY
    elif difficolta == "media":
        pool = FLAGS_MEDIUM
    else:
        pool = FLAGS_HARD
    
    emoji, answer = random.choice(list(pool.items()))
    flag_game[interaction.channel_id] = {"answer": answer, "active": True}
    await interaction.response.send_message(f"🏳️ **Indovina la bandiera! Difficoltà: {difficolta}**\n\n{emoji}\n\nScrivi il nome del paese in italiano! Il primo che indovina vince!")

bot.run(TOKEN)
