import discord
from discord.ext import commands
import json
import os
import random
import time
from discord import app_commands

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("ERRORE: Manca DISCORD_TOKEN!")
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

# --- RUOLO: CREA 1 VOLTA SOLA, POI SOLO DATO ---
async def get_or_create_role(guild: discord.Guild, role_name: str, color: discord.Color):
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
        return role, False
    try:
        role = await guild.create_role(
            name=role_name,
            colour=color,
            permissions=discord.Permissions.none(),
            mentionable=False,
            reason=f"Creato da Paper Bot - Shop {role_name}"
        )
        return role, True
    except discord.Forbidden:
        return None, False
    except Exception as e:
        print(f"Errore creazione ruolo {role_name}: {e}")
        return None, False

# --- SHOP DEL PAPER KING! ---
SHOP = {
    # --- WARRIOR ---
    "wcrate": {"nome": "📦 Warrior Crate", "prezzo": 5000, "faction": "Warrior", "tipo": "crate", "role_name": None, "color": 0x3498db},
    "wspin": {"nome": "🎡 Paper Wheel Spin", "prezzo": 10000, "faction": "Warrior", "tipo": "spin", "role_name": None, "color": 0x3498db},
    "cavaliere": {"nome": "🛡️ Cavaliere di Cellulosa", "prezzo": 250000, "faction": "Warrior", "tipo": "role", "role_name": "Cavaliere di Cellulosa", "color": 0x3498db},
    "duca": {"nome": "🎭 Duca di Cartone", "prezzo": 435000, "faction": "Warrior", "tipo": "role", "role_name": "Duca di Cartone", "color": 0x9b59b6},
    "principe": {"nome": "👑 Principe degli Origami", "prezzo": 575000, "faction": "Warrior", "tipo": "role", "role_name": "Principe degli Origami", "color": 0xf1c40f},

    # --- INVASION ---
    "icrate": {"nome": "📦 Invasion Crate", "prezzo": 5000, "faction": "Invasion", "tipo": "crate", "role_name": None, "color": 0xe74c3c},
    "ispin": {"nome": "🎡 Paper Wheel Spin", "prezzo": 10000, "faction": "Invasion", "tipo": "spin", "role_name": None, "color": 0xe74c3c},
    "avanguardia": {"nome": "🎯 Avanguardia di Carta", "prezzo": 250000, "faction": "Invasion", "tipo": "role", "role_name": "Avanguardia di Carta", "color": 0xe74c3c},
    "paladino": {"nome": "🦅 Paladino Imperfetto", "prezzo": 435000, "faction": "Invasion", "tipo": "role", "role_name": "Paladino Imperfetto", "color": 0xe67e22},
    "titano": {"nome": "🦾 Titano di Cartapesta", "prezzo": 575000, "faction": "Invasion", "tipo": "role", "role_name": "Titano di Cartapesta", "color": 0x2ecc71},

    # --- SPECIALE ---
    "custode": {"nome": "📖 Custode della Pergamena", "prezzo": 1000000, "faction": "Any", "tipo": "role", "role_name": "Custode della Pergamena", "color": 0x1abc9c},
}

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ PAPER INVASION Online come {bot.user}")

@bot.tree.command(name="setup", description="Scegli quali ruoli possono usare i comandi mod")
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
    if quantita <= 0:
        await interaction.response.send_message("❌ Quantità non valida!", ephemeral=True); return
    u = get_user(utente.id); u["coins"] += quantita; save_user(utente.id, u)
    await interaction.response.send_message(f"✅ Aggiunti **{quantita}** a {utente.mention}. Ora ha **{u['coins']}** 💰")

@bot.tree.command(name="remove", description="Rimuove Paper Coins a qualcuno")
async def remove_coins(interaction: discord.Interaction, utente: discord.Member, quantita: int):
    if not is_mod(interaction.user):
        await interaction.response.send_message("❌ Non hai il permesso!", ephemeral=True); return
    if quantita <= 0:
        await interaction.response.send_message("❌ Quantità non valida!", ephemeral=True); return
    u = get_user(utente.id); u["coins"] = max(0, u["coins"] - quantita); save_user(utente.id, u)
    await interaction.response.send_message(f"✅ Rimossi **{quantita}** a {utente.mention}. Ora ha **{u['coins']}** 💰")

@bot.tree.command(name="ban", description="Banna un utente dal bot")
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
@app_commands.choices(scelta=[app_commands.Choice(name="🛡️ Warrior Member", value="Warrior"), app_commands.Choice(name="🎯 Invasion Member", value="Invasion")])
async def select(interaction: discord.Interaction, scelta: app_commands.Choice[str]):
    if check_banned(interaction):
        await interaction.response.send_message("🚫 Sei bannato!", ephemeral=True); return
    u = get_user(interaction.user.id)
    if u["faction"]:
        await interaction.response.send_message(f"❌ Hai già scelto: **{u['faction']}**", ephemeral=True); return
    u["faction"] = scelta.value; save_user(interaction.user.id, u)
    role_name = "Warrior Member" if scelta.value == "Warrior" else "Invasion Member"
    role, creato = await get_or_create_role(interaction.guild, role_name, discord.Color(0x95a5a6))
    if role:
        try: await interaction.user.add_roles(role)
        except: pass
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

@bot.tree.command(name="crate", description="Apri una Paper Crate")
async def crate(interaction: discord.Interaction):
    if check_banned(interaction):
        await interaction.response.send_message("🚫 Sei bannato!", ephemeral=True); return
    u = get_user(interaction.user.id)
    if u["crates"] <= 0:
        await interaction.response.send_message("❌ Non hai Crate! Comprale con /shop", ephemeral=True); return
    u["crates"] -= 1
    premio = random.choices([1000, 5000, 15000, 50000], weights=[50, 30, 15, 5])[0]
    u["coins"] += premio; save_user(interaction.user.id, u)
    await interaction.response.send_message(f"📦 Hai aperto una Crate! Hai vinto **{premio:,}** 💰\nTi restano {u['crates']} crate. Saldo: {u['coins']:,}")

@bot.tree.command(name="buycrate", description="Compra una Crate per 5000 coins")
async def buycrate(interaction: discord.Interaction):
    if check_banned(interaction):
        await interaction.response.send_message("🚫 Sei bannato!", ephemeral=True); return
    u = get_user(interaction.user.id)
    if not u["faction"]:
        await interaction.response.send_message("❌ Prima /select!", ephemeral=True); return
    if u["coins"] < 5000:
        await interaction.response.send_message("❌ Ti servono 5.000 coins!", ephemeral=True); return
    u["coins"] -= 5000; u["crates"] += 1; save_user(interaction.user.id, u)
    await interaction.response.send_message(f"✅ Hai comprato 1 Crate! Ora ne hai {u['crates']} 📦")

@bot.tree.command(name="spin", description="Gira la Ruota della Fortuna")
async def spin(interaction: discord.Interaction):
    if check_banned(interaction):
        await interaction.response.send_message("🚫 Sei bannato!", ephemeral=True); return
    u = get_user(interaction.user.id)
    if u["spins"] <= 0:
        await interaction.response.send_message("❌ Non hai Spin! Compralo con /shop", ephemeral=True); return
    u["spins"] -= 1
    premi = [("💰 5.000 Coins", 5000, "coins"), ("💰 20.000 Coins", 20000, "coins"), ("📦 1 Crate", 1, "crates"), ("🎡 1 Spin Extra", 1, "spins"), ("💔 Niente...", 0, "coins")]
    nome, valore, tipo = random.choices(premi, weights=[40, 20, 20, 10, 10])[0]
    if tipo == "coins": u["coins"] += valore
    elif tipo == "crates": u["crates"] += valore
    elif tipo == "spins": u["spins"] += valore
    save_user(interaction.user.id, u)
    await interaction.response.send_message(f"🎡 La ruota gira... **{nome}**!\nSaldo: {u['coins']:,} 💰 | Crate: {u['crates']} | Spin: {u['spins']}")

@bot.tree.command(name="addspin", description="Dai Spin a qualcuno (Mod)")
async def addspin(interaction: discord.Interaction, utente: discord.Member, quantita: int):
    if not is_mod(interaction.user):
        await interaction.response.send_message("❌ Non hai il permesso!", ephemeral=True); return
    if quantita <= 0:
        await interaction.response.send_message("❌ Quantità non valida!", ephemeral=True); return
    u = get_user(utente.id); u["spins"] += quantita; save_user(utente.id, u)
    await interaction.response.send_message(f"✅ Dati {quantita} Spin a {utente.mention}. Ora ne ha {u['spins']} 🎡")

@bot.tree.command(name="coinflip", description="Testa o Croce con puntata")
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

class BlackjackView(discord.ui.View):
    def __init__(self, interaction, puntata, mano_tu, mano_king):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.puntata = puntata
        self.mano_tu = mano_tu
        self.mano_king = mano_king
    def valore(self, mano): return sum(mano)
    def testo(self):
        return f"🃏 Tu: {self.mano_tu} = **{self.valore(self.mano_tu)}**\n👑 King: {self.mano_king[0]} + ❓"
    async def finisci(self, interaction, vinto):
        u = get_user(interaction.user.id)
        king_tot = self.valore(self.mano_king)
        while king_tot < 17:
            self.mano_king.append(random.randint(1, 11)); king_tot = self.valore(self.mano_king)
        tu_tot = self.valore(self.mano_tu)
        if tu_tot > 21: msg = f"💥 Sballato! Tu {tu_tot} vs King {king_tot} -{self.puntata}"; u["coins"] -= self.puntata
        elif king_tot > 21 or tu_tot > king_tot:
            u["coins"] += self.puntata; msg = f"🎉 HAI VINTO! Tu {tu_tot} vs King {king_tot} +{self.puntata}"
        elif tu_tot < king_tot:
            u["coins"] -= self.puntata; msg = f"👑 KING VINCE! Tu {tu_tot} vs King {king_tot} -{self.puntata}"
        else: msg = f"🤝 Pareggio! Tu {tu_tot} vs King {king_tot}"
        save_user(interaction.user.id, u)
        for child in self.children: child.disabled = True
        await interaction.response.edit_message(content=f"{msg}\nSaldo: **{u['coins']:,}**", view=self)
    @discord.ui.button(label="🃏 Carta", style=discord.ButtonStyle.primary)
    async def carta(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("❌ Non è la tua partita!", ephemeral=True); return
        self.mano_tu.append(random.randint(1, 11))
        if self.valore(self.mano_tu) > 21:
            await self.finisci(interaction, None)
        else:
            await interaction.response.edit_message(content=self.testo(), view=self)
    @discord.ui.button(label="✋ Stai", style=discord.ButtonStyle.success)
    async def stai(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("❌ Non è la tua partita!", ephemeral=True); return
        await self.finisci(interaction, None)

@bot.tree.command(name="blackjack", description="Blackjack vero con Paper King")
async def blackjack(interaction: discord.Interaction, puntata: int):
    if check_banned(interaction):
        await interaction.response.send_message("🚫 Sei bannato!", ephemeral=True); return
    u = get_user(interaction.user.id)
    if puntata <= 0 or puntata > u["coins"]:
        await interaction.response.send_message("❌ Coins insufficienti!", ephemeral=True); return
    mano_tu = [random.randint(1, 11), random.randint(1, 11)]
    mano_king = [random.randint(1, 11), random.randint(1, 11)]
    view = BlackjackView(interaction, puntata, mano_tu, mano_king)
    await interaction.response.send_message(content=view.testo(), view=view)

# --- SHOP DEL PAPER KING! ---
@bot.tree.command(name="shop", description="Apri lo shop del Paper King")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(title="👑 SHOP DEL PAPER KING!", description="Usa /buy <codice> - I ruoli si creano 1 volta sola!", color=0xf1c40f)
    embed.add_field(name="🛡️ WARRIOR MEMBER:", value="📦 Warrior Crate - 5k - `/buy wcrate`\n🎡 Paper Wheel Spin - 10k - `/buy wspin`\n🛡️ Cavaliere di Cellulosa - 250k - `/buy cavaliere`\n🎭 Duca di Cartone - 435k - `/buy duca`\n👑 Principe degli Origami - 575k - `/buy principe`", inline=False)
    embed.add_field(name="🎯 INVASION MEMBER:", value="📦 Invasion Crate - 5k - `/buy icrate`\n🎡 Paper Wheel Spin - 10k - `/buy ispin`\n🎯 Avanguardia di Carta - 250k - `/buy avanguardia`\n🦅 Paladino Imperfetto - 435k - `/buy paladino`\n🦾 Titano di Cartapesta - 575k - `/buy titano`", inline=False)
    embed.add_field(name="📖 SPECIALE PER TUTTI:", value="📖 Custode della Pergamena - 1 Mln - `/buy custode`", inline=False)
    await interaction.response.send_message(embed=embed)

# --- BUY CON RUOLI + CRATE + SPIN ---
@bot.tree.command(name="buy", description="Compra dallo shop del Paper King")
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
        await interaction.response.send_message(f"❌ Questo è per {item['faction']}! Tu sei {u['faction']}", ephemeral=True); return
    if item["tipo"] == "role" and item["role_name"] in u["roles_bought"]:
        await interaction.response.send_message("❌ Hai già questo ruolo!", ephemeral=True); return
    if u["coins"] < item["prezzo"]:
        await interaction.response.send_message(f"❌ Ti servono {item['prezzo']:,}, hai {u['coins']:,}", ephemeral=True); return

    # Scala i coins
    u["coins"] -= item["prezzo"]

    # --- SE E' CRATE ---
    if item["tipo"] == "crate":
        u["crates"] += 1; save_user(interaction.user.id, u)
        await interaction.response.send_message(f"✅ Hai comprato **{item['nome']}**!\n📦 Ora hai {u['crates']} Crate. Saldo: {u['coins']:,}")
        return

    # --- SE E' SPIN ---
    if item["tipo"] == "spin":
        u["spins"] += 1; save_user(interaction.user.id, u)
        await interaction.response.send_message(f"✅ Hai comprato **{item['nome']}**!\n🎡 Ora hai {u['spins']} Spin. Saldo: {u['coins']:,}")
        return

    # --- SE E' RUOLO ---
    u["roles_bought"].append(item["role_name"]); save_user(interaction.user.id, u)
    role, appena_creato = await get_or_create_role(interaction.guild, item["role_name"], discord.Color(item["color"]))
    if role is None:
        u = get_user(interaction.user.id); u["coins"] += item["prezzo"]; u["roles_bought"].remove(item["role_name"]); save_user(interaction.user.id, u)
        await interaction.response.send_message(f"❌ Non riesco a creare il ruolo! Dai al bot **Gestisci Ruoli** e mettilo sopra gli altri.", ephemeral=True); return
    try:
        await interaction.user.add_roles(role)
    except discord.Forbidden:
        u = get_user(interaction.user.id); u["coins"] += item["prezzo"]; u["roles_bought"].remove(item["role_name"]); save_user(interaction.user.id, u)
        await interaction.response.send_message(f"❌ Ruolo creato ma non posso dartelo! Metti il ruolo del bot più in alto.", ephemeral=True); return
    if appena_creato:
        await interaction.response.send_message(f"🎉 Hai comprato **{item['nome']}**!\n✨ Ruolo **creato per la prima volta** (0 permessi, solo estetico) e dato a te!\nSaldo: {u['coins']:,}")
    else:
        await interaction.response.send_message(f"🎉 Hai comprato **{item['nome']}**!\n♻️ Ruolo **già esistente**, te l'ho dato senza crearne un altro!\nSaldo: {u['coins']:,}")

bot.run(TOKEN)
