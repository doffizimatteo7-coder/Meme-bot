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

# ---------- DATABASE ----------
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
            "anti_spam_seconds": 0.5,
            "anti_spam_enabled": True,
            "staff_roles": []  # ID dei ruoli staff
        }
    # Per vecchi config.json senza staff_roles
    if "staff_roles" not in CONFIG[gid]:
        CONFIG[gid]["staff_roles"] = []
    return CONFIG[gid]

def save_config():
    with open("config.json", "w") as f:
        json.dump(CONFIG, f, indent=4)

def is_staff(interaction: discord.Interaction):
    # Admin vero di Discord = sempre staff
    if interaction.user.guild_permissions.administrator:
        return True
    cfg = get_guild_config(interaction.guild.id)
    staff_ids = cfg.get("staff_roles", [])
    # Controlla se l'utente ha uno dei ruoli staff
    for ruolo in interaction.user.roles:
        if ruolo.id in staff_ids:
            return True
    return False

user_messages = {}
flag_game = {}

FLAGS_EASY = {
    "🇮🇹": "Italia", "🇫🇷": "Francia", "🇪🇸": "Spagna", "🇩🇪": "Germania",
    "🇬🇧": "Regno Unito", "🇺🇸": "Stati Uniti", "🇧🇷": "Brasile", "🇯🇵": "Giappone",
}
FLAGS_MEDIUM = {
    "🇨🇦": "Canada", "🇦🇺": "Australia", "🇲🇽": "Messico", "🇦🇷": "Argentina",
    "🇨🇳": "Cina", "🇰🇷": "Corea del Sud", "🇪🇬": "Egitto", "🇳🇱": "Paesi Bassi",
}
FLAGS_HARD = {
    "🇳🇴": "Norvegia", "🇫🇮": "Finlandia", "🇵🇱": "Polonia", "🇹🇷": "Turchia",
    "🇹🇭": "Thailandia", "🇻🇳": "Vietnam", "🇰🇪": "Kenya", "🇨🇱": "Cile",
}

# ---------- GIVEAWAY ----------
giveaways = {}

class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Clicca qui!", style=discord.ButtonStyle.success, emoji="🎉", custom_id="giveaway_join")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        gw = giveaways.get(interaction.message.id)
        if not gw or not gw["attivo"]:
            await interaction.response.send_message("❌ Questo giveaway è finito!", ephemeral=True)
            return
        if interaction.user.id in gw["partecipanti"]:
            await interaction.response.send_message("⚠️ Sei già entrato nel giveaway!", ephemeral=True)
            return
        gw["partecipanti"].append(interaction.user.id)
        await interaction.response.send_message(f"✅ Sei entrato nel giveaway **{gw['titolo']}**! Buona fortuna! 🍀", ephemeral=True)

async def finish_giveaway(message_id):
    gw = giveaways.get(message_id)
    if not gw or not gw["attivo"]:
        return False
    gw["attivo"] = False
    canale = bot.get_channel(gw["channel_id"])
    if not canale:
        return True
    if len(gw["partecipanti"]) == 0:
        await canale.send(f"❌ Giveaway **{gw['titolo']}** finito! Nessuno ha partecipato!")
        return True
    vincitore_id = random.choice(gw["partecipanti"])
    vincitore = canale.guild.get_member(vincitore_id)
    menzione = vincitore.mention if vincitore else f"<@{vincitore_id}>"
    await canale.send(f"🎉 {menzione} ha vinto il giveaway! 🎉\n**Premio:** {gw['titolo']}\n**Descrizione:** {gw['descrizione']} - Congratulazioni!")
    return True

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
    bot.add_view(GiveawayView())
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

    if cfg.get("anti_link"):
        if re.search(r"(discord\.gg/|discord\.com/invite/|discordapp\.com/invite/)", content_lower):
            try: await message.delete()
            except: pass
            try:
                await message.author.timeout(timedelta(days=1), reason="Anti-Link: ha mandato un invito")
                embed = discord.Embed(title="🔗 Anti-Link - Timeout 1 giorno", color=discord.Color.red(), timestamp=datetime.now())
                embed.add_field(name="Staff", value="🤖 Automatico (Bot)", inline=False)
                embed.add_field(name="Utente in timeout", value=f"{message.author.mention} ({message.author})", inline=False)
                embed.add_field(name="Motivo", value="Ha mandato un link invito", inline=False)
                embed.add_field(name="Durata", value="1 giorno", inline=False)
                embed.add_field(name="Messaggio", value=message.content[:1000], inline=False)
                embed.add_field(name="Canale", value=message.channel.mention, inline=False)
                await send_log(message.guild, embed)
                await message.channel.send(f"{message.author.mention} ha mandato un link invito -> timeout 1 giorno!", delete_after=5)
            except Exception as e:
                print(e)
            return

    for parola in cfg.get("banned_words", []):
        if parola.lower() in content_lower:
            try: await message.delete()
            except: pass
            embed = discord.Embed(title="🚫 Parola vietata eliminata", color=discord.Color.orange(), timestamp=datetime.now())
            embed.add_field(name="Utente", value=f"{message.author.mention}", inline=False)
            embed.add_field(name="Parola vietata", value=f"||{parola}||", inline=False)
            embed.add_field(name="Messaggio", value=message.content[:1000], inline=False)
            embed.add_field(name="Canale", value=message.channel.mention, inline=False)
            await send_log(message.guild, embed)
            return

    if cfg.get("anti_spam_enabled"):
        now = asyncio.get_event_loop().time()
        uid = message.author.id
        limit = cfg.get("anti_spam_seconds", 0.5)
        if uid not in user_messages:
            user_messages[uid] = []
        user_messages[uid].append(now)
        user_messages[uid] = [t for t in user_messages[uid] if now - t < 5]
        if len(user_messages[uid]) >= 5:
            if user_messages[uid][-1] - user_messages[uid][0] < limit * 5:
                user_messages[uid] = []
                try:
                    await message.author.timeout(timedelta(hours=1), reason="Anti-Spam")
                    await message.channel.send(f"{message.author.mention} spam -> timeout 1 ora!", delete_after=5)
                    embed = discord.Embed(title="⏱️ Anti-Spam - Timeout 1 ora", color=discord.Color.red(), timestamp=datetime.now())
                    embed.add_field(name="Staff", value="🤖 Automatico (Bot)", inline=False)
                    embed.add_field(name="Utente in timeout", value=f"{message.author.mention}", inline=False)
                    embed.add_field(name="Motivo", value=f"Troppi messaggi veloci (limite {limit}s)", inline=False)
                    embed.add_field(name="Durata", value="1 ora", inline=False)
                    await send_log(message.guild, embed)
                except: pass
                return

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
    if before.timed_out_until != after.timed_out_until and after.timed_out_until is not None:
        embed = discord.Embed(title="⏳ Timeout dato", color=discord.Color.gold(), timestamp=datetime.now())
        embed.add_field(name="Utente in timeout", value=f"{after.mention}", inline=False)
        embed.add_field(name="Fino a", value=str(after.timed_out_until), inline=False)
        await send_log(after.guild, embed)

# ---------- COMANDI MODERAZIONE ----------

@bot.tree.command(name="ban", description="Banna un utente (staff)")
@app_commands.describe(utente="Chi vuoi bannare", motivo="Perché lo banni?")
async def ban(interaction: discord.Interaction, utente: discord.Member, motivo: str = "Nessun motivo"):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Non sei staff!", ephemeral=True)
        return
    # Controllo permessi veri di Discord per ban
    if not interaction.user.guild_permissions.ban_members and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Il bot non può bannare perché non hai il permesso Discord 'Banna membri'. Dallo al ruolo staff su Discord se vuoi che funzioni!", ephemeral=True)
        return
    try:
        await utente.ban(reason=f"Staff: {interaction.user} | Motivo: {motivo}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Errore: {e}\nAssicurati che il BOT abbia il permesso Banna membri e il ruolo del bot sia sopra al ruolo dell'utente.", ephemeral=True)
        return
    embed = discord.Embed(title="🔨 Ban", color=discord.Color.red(), timestamp=datetime.now())
    embed.add_field(name="Staff", value=f"{interaction.user.mention} ({interaction.user})", inline=False)
    embed.add_field(name="Utente bannato", value=f"{utente.mention} ({utente})", inline=False)
    embed.add_field(name="Motivo", value=motivo, inline=False)
    embed.add_field(name="Durata", value="Permanente", inline=False)
    await send_log(interaction.guild, embed)
    await interaction.response.send_message(f"✅ {utente.mention} bannato!\nMotivo: {motivo}")

@bot.tree.command(name="kick", description="Espelli un utente (staff)")
@app_commands.describe(utente="Chi vuoi espellere", motivo="Perché lo espelli?")
async def kick(interaction: discord.Interaction, utente: discord.Member, motivo: str = "Nessun motivo"):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Non sei staff!", ephemeral=True)
        return
    if not interaction.user.guild_permissions.kick_members and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Non hai il permesso Discord 'Espelli membri' sul tuo ruolo.", ephemeral=True)
        return
    try:
        await utente.kick(reason=f"Staff: {interaction.user} | Motivo: {motivo}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Errore: {e}", ephemeral=True)
        return
    embed = discord.Embed(title="👢 Espulsione (Kick)", color=discord.Color.orange(), timestamp=datetime.now())
    embed.add_field(name="Staff", value=f"{interaction.user.mention} ({interaction.user})", inline=False)
    embed.add_field(name="Utente espulso", value=f"{utente.mention} ({utente})", inline=False)
    embed.add_field(name="Motivo", value=motivo, inline=False)
    embed.add_field(name="Durata", value="Può rientrare subito con un nuovo invito", inline=False)
    await send_log(interaction.guild, embed)
    await interaction.response.send_message(f"✅ {utente.mention} espulso!\nMotivo: {motivo}")

@bot.tree.command(name="timeout", description="Metti in timeout un utente (staff)")
@app_commands.describe(utente="Chi vuoi mutare", minuti="Quanti minuti di timeout?", motivo="Perché?")
async def timeout_cmd(interaction: discord.Interaction, utente: discord.Member, minuti: int, motivo: str = "Nessun motivo"):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Non sei staff!", ephemeral=True)
        return
    if not interaction.user.guild_permissions.moderate_members and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Non hai il permesso Discord 'Moderazione membri' sul tuo ruolo.", ephemeral=True)
        return
    try:
        await utente.timeout(timedelta(minutes=minuti), reason=f"Staff: {interaction.user} | Motivo: {motivo}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Errore: {e}", ephemeral=True)
        return
    embed = discord.Embed(title="⏳ Timeout", color=discord.Color.gold(), timestamp=datetime.now())
    embed.add_field(name="Staff", value=f"{interaction.user.mention} ({interaction.user})", inline=False)
    embed.add_field(name="Utente in timeout", value=f"{utente.mention} ({utente})", inline=False)
    embed.add_field(name="Motivo", value=motivo, inline=False)
    embed.add_field(name="Durata", value=f"{minuti} minuti", inline=False)
    await send_log(interaction.guild, embed)
    await interaction.response.send_message(f"✅ {utente.mention} in timeout per {minuti} minuti!\nMotivo: {motivo}")

@bot.tree.command(name="unban", description="Sbanna un utente (staff)")
@app_commands.describe(utente_id="ID dell'utente da sbannare")
async def unban(interaction: discord.Interaction, utente_id: str):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Non sei staff!", ephemeral=True)
        return
    try:
        user = await bot.fetch_user(int(utente_id))
        await interaction.guild.unban(user)
        embed = discord.Embed(title="✅ Unban", color=discord.Color.green(), timestamp=datetime.now())
        embed.add_field(name="Staff", value=f"{interaction.user.mention}", inline=False)
        embed.add_field(name="Utente sbannato", value=f"{user.mention} ({user})", inline=False)
        embed.add_field(name="Motivo", value="Sbannato dallo staff", inline=False)
        embed.add_field(name="Durata", value="-", inline=False)
        await send_log(interaction.guild, embed)
        await interaction.response.send_message(f"✅ {user.mention} sbannato!")
    except Exception as e:
        await interaction.response.send_message(f"❌ Errore: {e}", ephemeral=True)

# ---------- DIVIETO / SETUP ----------

@bot.tree.command(name="divieto", description="Aggiungi una parola vietata (staff)")
@app_commands.describe(parola="La parola da vietare")
async def divieto(interaction: discord.Interaction, parola: str):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Non sei staff!", ephemeral=True)
        return
    cfg = get_guild_config(interaction.guild.id)
    parola = parola.lower().strip()
    if parola in cfg["banned_words"]:
        await interaction.response.send_message(f"La parola `{parola}` è già vietata.", ephemeral=True)
        return
    cfg["banned_words"].append(parola)
    save_config()
    await interaction.response.send_message(f"✅ Parola vietata aggiunta: `{parola}`")

@bot.tree.command(name="sdivieto", description="Togli una parola vietata (staff)")
@app_commands.describe(parola="La parola da sbloccare")
async def sdivieto(interaction: discord.Interaction, parola: str):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Non sei staff!", ephemeral=True)
        return
    cfg = get_guild_config(interaction.guild.id)
    parola = parola.lower().strip()
    if parola not in cfg["banned_words"]:
        await interaction.response.send_message(f"La parola `{parola}` non era vietata.", ephemeral=True)
        return
    cfg["banned_words"].remove(parola)
    save_config()
    await interaction.response.send_message(f"✅ Parola sbloccata: `{parola}`")

@bot.tree.command(name="setup", description="Setup del bot (solo admin Discord)")
@app_commands.describe(anti_link="Attiva o disattiva anti-link", canale_log="Canale dove mandare i log", anti_spam_secondi="Secondi tra messaggi per anti-spam", ruolo_staff="Ruolo che può usare i comandi staff")
async def setup(interaction: discord.Interaction, anti_link: bool = None, canale_log: discord.TextChannel = None, anti_spam_secondi: float = None, ruolo_staff: discord.Role = None):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Solo chi ha Amministratore su Discord può fare /setup!", ephemeral=True)
        return
    cfg = get_guild_config(interaction.guild.id)
    msg = "⚙️ **Setup aggiornato:**\n"
    if anti_link is not None:
        cfg["anti_link"] = anti_link
        msg += f"- Anti-Link: {'✅ Attivato' if anti_link else '❌ Disattivato'}\n"
    if canale_log is not None:
        cfg["log_channel"] = canale_log.id
        msg += f"- Canale log: {canale_log.mention}\n"
    if anti_spam_secondi is not None:
        cfg["anti_spam_seconds"] = anti_spam_secondi
        cfg["anti_spam_enabled"] = True
        msg += f"- Anti-Spam: {anti_spam_secondi}s\n"
    if ruolo_staff is not None:
        if ruolo_staff.id not in cfg["staff_roles"]:
            cfg["staff_roles"].append(ruolo_staff.id)
        msg += f"- Ruolo staff aggiunto: {ruolo_staff.mention}\nChi ha questo ruolo ora può usare /ban /kick /timeout /giveaway ecc.\n"
    save_config()
    await interaction.response.send_message(msg, ephemeral=True)

# ---------- FLAG ----------

@bot.tree.command(name="flag", description="Indovina la bandiera!")
@app_commands.describe(difficolta="facile, media, difficile")
@app_commands.choices(difficolta=[
    app_commands.Choice(name="facile", value="facile"),
    app_commands.Choice(name="media", value="media"),
    app_commands.Choice(name="difficile", value="difficile"),
])
async def flag(interaction: discord.Interaction, difficolta: str):
    if difficolta == "facile": pool = FLAGS_EASY
    elif difficolta == "media": pool = FLAGS_MEDIUM
    else: pool = FLAGS_HARD
    emoji, answer = random.choice(list(pool.items()))
    flag_game[interaction.channel_id] = {"answer": answer, "active": True}
    await interaction.response.send_message(f"🏳️ **Indovina la bandiera! Difficoltà: {difficolta}**\n\n{emoji}\n\nScrivi il nome del paese in italiano!")

# ---------- GIVEAWAY CON DURATA ----------

@bot.tree.command(name="giveaway", description="Crea un giveaway con durata automatica (staff)")
@app_commands.describe(titolo="Titolo / premio del giveaway", descrizione="Descrizione del premio", durata="Durata in MINUTI (es. 10 = 10 minuti)")
async def giveaway(interaction: discord.Interaction, titolo: str, descrizione: str, durata: int):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Non sei staff!", ephemeral=True)
        return
    if durata <= 0:
        await interaction.response.send_message("❌ La durata deve essere più di 0 minuti!", ephemeral=True)
        return
    fine = datetime.now() + timedelta(minutes=durata)
    embed = discord.Embed(title=f"🎉 GIVEAWAY: {titolo}", description=descrizione, color=discord.Color.gold(), timestamp=datetime.now())
    embed.add_field(name="📦 Premio", value=titolo, inline=False)
    embed.add_field(name="📝 Descrizione", value=descrizione, inline=False)
    embed.add_field(name="⏰ Durata", value=f"{durata} minuti", inline=True)
    embed.add_field(name="🏁 Finisce alle", value=fine.strftime("%H:%M"), inline=True)
    embed.add_field(name="Come partecipare", value="Clicca sul pulsante **Clicca qui!** qui sotto!", inline=False)
    embed.set_footer(text=f"Creato da {interaction.user} • Si estrae in automatico alla scadenza")
    await interaction.response.send_message(embed=embed, view=GiveawayView())
    msg = await interaction.original_response()
    giveaways[msg.id] = {"titolo": titolo, "descrizione": descrizione, "durata": durata, "channel_id": interaction.channel_id, "partecipanti": [], "attivo": True}
    asyncio.create_task(auto_end_giveaway(msg.id, durata))

async def auto_end_giveaway(message_id, durata_minuti):
    await asyncio.sleep(durata_minuti * 60)
    await finish_giveaway(message_id)

# Funzione per chiudere giveaway - usata da entrambi i comandi
async def do_endgiveaway(interaction: discord.Interaction, message_id: str):
    if not is_staff(interaction):
        await interaction.response.send_message("❌ Non sei staff!", ephemeral=True)
        return
    try: mid = int(message_id)
    except:
        await interaction.response.send_message("❌ ID non valido! Fai tasto destro sul messaggio del giveaway > Copia ID messaggio", ephemeral=True)
        return
    gw = giveaways.get(mid)
    if not gw or not gw["attivo"]:
        await interaction.response.send_message("❌ Giveaway non trovato o già finito! Forse il bot è stato riavviato? Se riavvii il bot, i giveaway attivi si perdono, devi rifarlo.", ephemeral=True)
        return
    await finish_giveaway(mid)
    await interaction.response.send_message(f"✅ Giveaway finito e vincitore estratto!", ephemeral=True)

@bot.tree.command(name="endgiveaway", description="Finisci subito il giveaway e estrai (staff)")
@app_commands.describe(message_id="ID del messaggio del giveaway")
async def endgiveaway(interaction: discord.Interaction, message_id: str):
    await do_endgiveaway(interaction, message_id)

@bot.tree.command(name="endgiveway", description="Finisci subito il giveaway e estrai (staff) - versione senza a")
@app_commands.describe(message_id="ID del messaggio del giveaway")
async def endgiveway(interaction: discord.Interaction, message_id: str):
    await do_endgiveaway(interaction, message_id)

# ---------- SAY ----------

@bot.tree.command(name="say", description="Fa parlare il bot (chiunque)")
@app_commands.describe(testo="Cosa deve dire il bot")
async def say(interaction: discord.Interaction, testo: str):
    await interaction.response.send_message("✅ Messaggio inviato!", ephemeral=True)
    await interaction.channel.send(testo)

bot.run(TOKEN)
