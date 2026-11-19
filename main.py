import discord
from discord.ext import commands
import json
import os
import random
import time
from discord import app_commands

# PRENDE IL TOKEN DALLE VARIABILI D'AMBIENTE - SICURO
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("ERRORE: Manca DISCORD_TOKEN nelle variabili d'ambiente!")
    exit()

DATA_FILE = "paper_data.json"
CONFIG_FILE = "paper_config.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

def load_json(path, default):
    if not os.path.exists(path):
        save_json(path, default)
        return default
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def get_user(uid):
    data = load_json(DATA_FILE, {})
    uid = str(uid)
    if uid not in data:
        data[uid] = {"coins": 0, "crates": 0, "spins": 0, "faction": None, "banned": False, "roles_bought": [], "last_daily": 0}
        save_json(DATA_FILE, data)
    return data[uid]

def save_user(uid, user_data):
    data = load_json(DATA_FILE, {})
    data[str(uid)] = user_data
    save_json(DATA_FILE, data)

def is_mod(member: discord.Member):
    cfg = load_json(CONFIG_FILE, {"mod_roles": []})
    if member.guild.owner_id == member.id:
        return True
    for r in member.roles:
        if r.id in cfg["mod_roles"]:
            return True
    return False

def check_banned(interaction):
    return get_user(interaction.user.id)["banned"]

SHOP = {
    "cavaliere": {"nome": "🛡️ Cavaliere di Cellulosa", "prezzo": 250000, "faction": "Warrior", "role_name": "Cavaliere di Cellulosa"},
    "duca": {"nome": "🎭 Duca di Cartone", "prezzo": 435000, "faction": "Warrior", "role_name": "Duca di Cartone"},
    "principe": {"nome": "👑 Principe degli Origami", "prezzo": 575000, "faction": "Warrior", "role_name": "Principe degli Origami"},
    "avanguardia": {"nome": "🎯 Avanguardia di Carta", "prezzo": 250000, "faction": "Invasion", "role_name": "Avanguardia di Carta"},
    "paladino": {"nome": "🦅 Paladino Imperfetto", "prezzo": 435000, "faction": "Invasion", "role_name": "Paladino Imperfetto"},
    "titano": {"nome": "🦾 Titano di Cartapesta", "prezzo": 575000, "faction": "Invasion", "role_name": "Titano di Cartapesta"},
    "custode": {"nome": "📖 Custode della Pergamena", "prezzo": 1000000, "faction": "Any", "role_name": "Custode della Pergamena"},
}

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ PAPER INVASION Online come {bot.user}")

@bot.tree.command(name="setup", description="Scegli quali ruoli possono usare i comandi mod")
@app_commands.describe(ruolo="Ruolo che potrà usare /add /remove /ban")
async def setup(interaction: discord.Interaction, ruolo: discord.Role):
    if interaction.guild.owner_id != interaction.user.id:
        await interaction.response.send_message("❌ Solo l'Owner può usare /setup", ephemeral=True); return
    cfg = load_json(CONFIG_FILE, {"mod_roles": []})
    if ruolo.id not in cfg["mod_roles"]:
        cfg["mod_roles"].append(ruolo.id)
    save_json(CONFIG_FILE, cfg)
    await interaction.response.send_message(f"✅ Ora il ruolo {ruolo.mention} può usare i comandi Moderator!", ephemeral=True)

@bot.tree.command(name="add", description="Aggiunge Paper Coins a qualcuno")
async def add_coins(interaction: discord.Interaction, utente: discord.Member, quantita: int):
    if not is_mod(interaction.user):
        await interaction.response.send_message("❌ Non hai il permesso!", ephemeral=True); return
    u = get_user(utente.id); u["coins"] += quantita; save_user(utente.id, u)
    await interaction.response.send_message(f"✅ Aggiunti **{quantita}** a {utente.mention}. Ora ha **{u['coins']}** 💰")

@bot.tree.command(name="remove", description="Rimuove Paper Coins a qualcuno")
async def remove_coins(interaction: discord.Interaction, utente: discord.Member, quantita: int):
    if not is_mod(interaction.user):
        await interaction.response.send_message("❌ Non hai il permesso!", ephemeral=True); return
    u = get_user(utente.id); u["coins"] = max(0, u["coins"] - quantita); save_user(utente.id, u)
    await interaction.response.send_message(f"✅ Rimossi **{quantita}** a {utente.mention}. Ora ha **{u['coins']}** 💰")

@bot.tree.command(name="ban", description="Banna un utente dall'uso del bot (NON dal server)")
async def ban_bot(interaction: discord.Interaction, utente: discord.Member):
    if not is_mod(interaction.user):
        await interaction.response.send_message("❌ Non hai il permesso!", ephemeral=True); return
    u = get_user(utente.id); u["banned"] = True; save_user(utente.id, u)
    await interaction.response.send_message(f"🚫 {utente.mention} bannato dal bot!")

@bot.tree.command(name="sban", description="Sbanna un utente dal bot")
async def sban_bot(interaction: discord.Interaction, utente: discord.Member):
    if not is_mod(interaction.user):
        await interaction.response.send_message("❌ Non hai il permesso!", ephemeral=True); return
    u = get_user(utente.id); u["banned"] = False; save_user(utente.id, u)
    await interaction.response.send_message(f"✅ {utente.mention} sbannato!")

@bot.tree.command(name="select", description="Scegli la tua fazione! NON SI PUO' CAMBIARE")
@app_commands.describe(scelta="Warrior o Invasion?")
@app_commands.choices(scelta=[app_commands.Choice(name="🛡️ Warrior Member", value="Warrior"), app_commands.Choice(name="🎯 Invasion Member", value="Invasion")])
async def select(interaction: discord.Interaction, scelta: app_commands.Choice[str]):
    if check_banned(interaction):
        await interaction.response.send_message("🚫 Sei bannato!", ephemeral=True); return
    u = get_user(interaction.user.id)
    if u["faction"]:
        await interaction.response.send_message(f"❌ Hai già scelto: **{u['faction']}**", ephemeral=True); return
    u["faction"] = scelta.value; save_user(interaction.user.id, u)
    role_name = "Warrior Member" if scelta.value == "Warrior" else "Invasion Member"
    role = discord.utils.get(interaction.guild.roles, name=role_name)
    if role: await interaction.user.add_roles(role)
    await interaction.response.send_message(f"🎉 Sei diventato **{role_name}**! 📄")

@bot.tree.command(name="balance", description="Vedi i tuoi Coins, Crate, Spin e Ruoli")
async def balance(interaction: discord.Interaction):
    if check_banned(interaction):
        await interaction.response.send_message("🚫 Sei bannato!", ephemeral=True); return
    u = get_user(interaction.user.id)
    embed = discord.Embed(title=f"📄 Profilo di {interaction.user.display_name}", color=0xf1c40f)
    embed.add_field(name="💰 Paper Coins", value=f"{u['coins']:,}", inline=False)
    embed.add_field(name="📦 Crate", value=str(u['crates']), inline=True)
    embed.add_field(name="🎡 Spin Ruota", value=str(u['spins']), inline=True)
    embed.add_field(name="⚔️ Fazione", value=u['faction'] or "Non scelta - usa /select", inline=False)
    embed.add_field(name="🎭 Ruoli comprati", value=", ".join(u['roles_bought']) or "Nessuno", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="daily", description="Ricompensa giornaliera 1000-5000 coins")
async def daily(interaction: discord.Interaction):
    if check_banned(interaction):
        await interaction.response.send_message("🚫 Sei bannato!", ephemeral=True); return
    u = get_user(interaction.user.id)
    now = time.time()
    if now - u["last_daily"] < 86400:
        ore = int((86400 - (now - u["last_daily"])) // 3600)
        await interaction.response.send_message(f"⏰ Hai già riscosso! Torna tra {ore} ore.", ephemeral=True); return
    premio = random.randint(1000, 5000)
    u["coins"] += premio; u["last_daily"] = now; save_user(interaction.user.id, u)
    await interaction.response.send_message(f"🎁 Daily! Hai ricevuto **{premio}** Paper Coins! Ora hai {u['coins']:,} 💰")

@bot.tree.command(name="coinflip", description="Testa o Croce con puntata")
@app_commands.describe(puntata="Quanti coins punti", scelta="testa o croce")
@app_commands.choices(scelta=[app_commands.Choice(name="Testa", value="testa"), app_commands.Choice(name="Croce", value="croce")])
async def coinflip(interaction: discord.Interaction, puntata: int, scelta: app_commands.Choice[str]):
    if check_banned(interaction):
        await interaction.response.send_message("🚫 Sei bannato!", ephemeral=True); return
    u = get_user(interaction.user.id)
    if puntata <= 0 or puntata > u["coins"]:
        await interaction.response.send_message("❌ Puntata non valida!", ephemeral=True); return
    risultato = random.choice(["testa", "croce"])
    if risultato == scelta.value:
        u["coins"] += puntata; msg = f"🪙 È uscito **{risultato}**! HAI VINTO +{puntata} 💰"
    else:
        u["coins"] -= puntata; msg = f"🪙 È uscito **{risultato}**! HAI PERSO -{puntata} 💔"
    save_user(interaction.user.id, u)
    await interaction.response.send_message(f"{msg}\nSaldo: **{u['coins']:,}**")

@bot.tree.command(name="rockpaperscissors", description="Carta Forbice Sasso contro il bot")
@app_commands.describe(puntata="Puntata", scelta="La tua scelta")
@app_commands.choices(scelta=[app_commands.Choice(name="🪨 Sasso", value="sasso"), app_commands.Choice(name="📄 Carta", value="carta"), app_commands.Choice(name="✂️ Forbice", value="forbice")])
async def rps(interaction: discord.Interaction, puntata: int, scelta: app_commands.Choice[str]):
    if check_banned(interaction):
        await interaction.response.send_message("🚫 Sei bannato!", ephemeral=True); return
    u = get_user(interaction.user.id)
    if puntata <= 0 or puntata > u["coins"]:
        await interaction.response.send_message("❌ Coins insufficienti!", ephemeral=True); return
    bot_choice = random.choice(["sasso", "carta", "forbice"])
    vince = {"sasso":"forbice", "carta":"sasso", "forbice":"carta"}
    if bot_choice == scelta.value: msg = f"🤝 Pareggio! Bot: {bot_choice}"
    elif vince[scelta.value] == bot_choice:
        u["coins"] += puntata; msg = f"🎉 Hai vinto! Tu: {scelta.value} vs Bot: {bot_choice} +{puntata}"
    else:
        u["coins"] -= puntata; msg = f"😭 Hai perso! Tu: {scelta.value} vs Bot: {bot_choice} -{puntata}"
    save_user(interaction.user.id, u)
    await interaction.response.send_message(f"{msg}\nSaldo: **{u['coins']:,}**")

@bot.tree.command(name="blackjack", description="Blackjack con Paper King")
async def blackjack(interaction: discord.Interaction, puntata: int):
    if check_banned(interaction):
        await interaction.response.send_message("🚫 Sei bannato!", ephemeral=True); return
    u = get_user(interaction.user.id)
    if puntata <= 0 or puntata > u["coins"]:
        await interaction.response.send_message("❌ Coins insufficienti!", ephemeral=True); return
    def carta(): return random.randint(1, 11)
    tu = carta() + carta(); king = carta() + carta()
    if tu > king: u["coins"] += puntata; msg = f"👑 HAI BATTUTO PAPER KING! Tu {tu} vs King {king} +{puntata}"
    elif tu < king: u["coins"] -= puntata; msg = f"👑 PAPER KING VINCE! Tu {tu} vs King {king} -{puntata}"
    else: msg = f"🤝 Pareggio! Tu {tu} vs King {king}"
    save_user(interaction.user.id, u)
    await interaction.response.send_message(f"{msg}\nSaldo: **{u['coins']:,}**")

@bot.tree.command(name="shop", description="Apri lo shop dei ruoli")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(title="🛒 PAPER SHOP", description="Usa /buy <codice>", color=0x3498db)
    embed.add_field(name="🛡️ WARRIOR", value="🛡️ Cavaliere - 250k - `/buy cavaliere`\n🎭 Duca - 435k - `/buy duca`\n👑 Principe - 575k - `/buy principe`", inline=False)
    embed.add_field(name="🎯 INVASION", value="🎯 Avanguardia - 250k - `/buy avanguardia`\n🦅 Paladino - 435k - `/buy paladino`\n🦾 Titano - 575k - `/buy titano`", inline=False)
    embed.add_field(name="📖 SPECIALE", value="📖 Custode - 1.000.000 - `/buy custode`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="buy", description="Compra un ruolo dallo shop")
async def buy(interaction: discord.Interaction, codice: str):
    if check_banned(interaction):
        await interaction.response.send_message("🚫 Sei bannato!", ephemeral=True); return
    codice = codice.lower()
    if codice not in SHOP:
        await interaction.response.send_message("❌ Codice non valido! Usa /shop", ephemeral=True); return
    item = SHOP[codice]; u = get_user(interaction.user.id)
    if not u["faction"] and item["faction"] != "Any":
        await interaction.response.send_message("❌ Prima /select!", ephemeral=True); return
    if item["faction"] != "Any" and u["faction"] != item["faction"]:
        await interaction.response.send_message(f"❌ Questo ruolo è per {item['faction']}!", ephemeral=True); return
    if item["role_name"] in u["roles_bought"]:
        await interaction.response.send_message("❌ Hai già questo ruolo!", ephemeral=True); return
    if u["coins"] < item["prezzo"]:
        await interaction.response.send_message(f"❌ Ti servono {item['prezzo']:,}, hai {u['coins']:,}", ephemeral=True); return
    u["coins"] -= item["prezzo"]; u["roles_bought"].append(item["role_name"]); save_user(interaction.user.id, u)
    role = discord.utils.get(interaction.guild.roles, name=item["role_name"])
    if role: await interaction.user.add_roles(role)
    await interaction.response.send_message(f"🎉 Hai comprato **{item['nome']}**! Saldo: {u['coins']:,}")

bot.run(TOKEN)
