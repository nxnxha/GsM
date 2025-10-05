# -*- coding: utf-8 -*-
# Gossip Miri 💋 — Version Girly avec Validation (Fondas/Couronnes)
# Discord.py 2.x — Style Gossip Girl
# by ChatGPT 💄

import os, json, logging, datetime as dt, random
import discord
from discord import app_commands
from discord.ext import commands

# --------- CONFIGURATION ENV ----------
TOKEN = os.getenv("DISCORD_TOKEN", "REPLACE_ME")

# salons
GUILD_ID = 1382730341944397967
GOSSIP_CHANNEL_ID = 1423696445332131851
VALIDATION_CHANNEL_ID = 1424224671485661327
LOG_CHANNEL_ID = 1409227450554126396

# rôles
VALIDATION_ROLE_ID = 1400518143595778079  # ping dans le salon de validation
PUBLIC_ROLE_ID = 1423705639288574003      # ping dans le salon public

# thème
AUTHOR_NAME = "💋 Gossip Miri"
THEME_COLOR = 0xFFB6C1
PANEL_BANNER_URL = os.getenv("PANEL_BANNER_URL", "")
PIN_MESSAGE = False
BANLIST_FILE = os.getenv("BANLIST_FILE", "gossip_banlist.json")

# --------- LOG ----------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("gossip-miri")

# --------- BANLIST ----------
def load_banlist() -> set[int]:
    try:
        with open(BANLIST_FILE, "r", encoding="utf-8") as f:
            return set(int(x) for x in json.load(f))
    except FileNotFoundError:
        return set()
    except Exception as e:
        log.exception("Erreur lecture banlist: %s", e)
        return set()

def save_banlist(bset: set[int]):
    try:
        with open(BANLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(list(bset), f)
    except Exception as e:
        log.exception("Erreur écriture banlist: %s", e)

BANNED_USERS: set[int] = load_banlist()

# --------- BOT ----------
intents = discord.Intents.default()
intents.members = True

class MiriBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.synced = False

    async def setup_hook(self):
        self.add_view(PanelView())
        self.add_view(GossipActionsView())
        self.add_view(ValidationView(0, "", True))
        gobj = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=gobj)
        if not self.synced:
            await self.tree.sync(guild=gobj)
            self.synced = True

bot = MiriBot()

# --------- UTILITAIRES ----------
def sanitize(text: str, limit: int = 1800) -> str:
    return text.strip()[:limit]

def is_banned(uid: int) -> bool:
    return uid in BANNED_USERS

async def get_channels():
    guild = bot.get_guild(GUILD_ID) or await bot.fetch_guild(GUILD_ID)
    gossip_ch = guild.get_channel(GOSSIP_CHANNEL_ID) or await bot.fetch_channel(GOSSIP_CHANNEL_ID)
    log_ch = guild.get_channel(LOG_CHANNEL_ID) or await bot.fetch_channel(LOG_CHANNEL_ID)
    return gossip_ch, log_ch

def girly_embed(title: str, desc: str, color=THEME_COLOR) -> discord.Embed:
    emb = discord.Embed(title=title, description=desc, color=color, timestamp=dt.datetime.utcnow())
    emb.set_author(name=AUTHOR_NAME, icon_url="https://i.imgur.com/BqvDq6V.png")
    emb.set_footer(text="XOXO, Gossip Miri 💄")
    return emb

# --------- UI PANEL ----------
def embed_panel() -> discord.Embed:
    emb = girly_embed(
        "💋 Gossip Miri — Le Mur des Secrets",
        "Un secret ? Une rumeur ? Un crush interdit ?\n"
        "Ici, tout se murmure… Clique ci-dessous pour te confesser 👀"
    )
    if PANEL_BANNER_URL:
        emb.set_image(url=PANEL_BANNER_URL)
    return emb

class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Soumettre un gossip 💌", style=discord.ButtonStyle.primary, emoji="💖", custom_id="gossip:open")
    async def open_modal(self, interaction: discord.Interaction, _):
        if is_banned(interaction.user.id):
            return await interaction.response.send_message("🚫 Tu es banni(e) des confessions, darling 💔", ephemeral=True)
        await interaction.response.send_modal(SubmitModal())

# --------- GOSSIP SUBMISSION ----------
class SubmitModal(discord.ui.Modal, title="✨ Nouveau Gossip 💄"):
    content = discord.ui.TextInput(
        label="Ton gossip (reste chic, gossip girl style)",
        style=discord.TextStyle.paragraph,
        max_length=1800,
        required=True
    )
    anonymous = discord.ui.TextInput(
        label="Publier en anonyme ? (oui/non)",
        style=discord.TextStyle.short,
        default="oui",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        if is_banned(interaction.user.id):
            return await interaction.response.send_message("🚫 Tu es banni(e), darling 💔", ephemeral=True)

        await interaction.response.defer(ephemeral=True, thinking=True)
        validation_ch = bot.get_channel(VALIDATION_CHANNEL_ID)
        gossip_ch, log_ch = await get_channels()

        text = sanitize(str(self.content))
        anon = str(self.anonymous).lower().strip() in ("oui", "o", "yes", "y", "true", "1")

        if not validation_ch:
            return await interaction.followup.send("⚠️ Oups, le salon de validation est introuvable 😢", ephemeral=True)

        ping_role = validation_ch.guild.get_role(1400518143595778079)
        val_embed = girly_embed(
            "💋 Nouveau gossip en attente…",
            f"**Auteur :** {interaction.user.mention} (`{interaction.user.id}`)\n"
            f"**Anonyme :** {'Oui' if anon else 'Non'}\n\n"
            f"**Contenu :**\n> {text}\n\n"
            f"👑 Fondas & Couronnes : validez ou refusez ci-dessous 💅",
            color=0xFFC0CB
        )
        await validation_ch.send(content=ping_role.mention if ping_role else None, embed=val_embed,
                                 view=ValidationView(interaction.user.id, text, anon))

        log_embed = girly_embed(
            "🕓 Gossip soumis pour validation",
            f"**Auteur :** {interaction.user} (`{interaction.user.id}`)\n"
            f"**Anonyme :** {'Oui' if anon else 'Non'}\n\n"
            f"**Contenu :**\n{text}",
            color=0xFFB6C1
        )
        await log_ch.send(embed=log_embed)
        await interaction.followup.send("💅 Ton gossip a été envoyé aux fondas pour validation. Patiente, darling 💋", ephemeral=True)

# --------- VALIDATION VIEW ----------
async def has_validation_role(member: discord.Member) -> bool:
    return any(r.name.lower() in ("fonda", "couronne") for r in member.roles)

class ValidationView(discord.ui.View):
    def __init__(self, author_id: int, content: str, anonymous: bool):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.content = content
        self.anonymous = anonymous

    @discord.ui.button(label="💖 Valider", style=discord.ButtonStyle.success, emoji="💌", custom_id="gossip:approve")
    async def approve(self, interaction: discord.Interaction, _):
        if not await has_validation_role(interaction.user):
            return await interaction.response.send_message("🚫 Désolée, seuls les fondas/couronnes peuvent valider 💅", ephemeral=True)

        gossip_ch, log_ch = await get_channels()
        role = gossip_ch.guild.get_role(PUBLIC_ROLE_ID)
        public_embed = girly_embed(
            random.choice([
                "💖 Quelqu’un a chuchoté…",
                "💅 On m’a soufflé quelque chose d’intéressant…",
                "👠 Les rumeurs vont bon train à Miri High…"
            ]),
            f"> {self.content}"
        )
        public = await gossip_ch.send(content=role.mention if role else None, embed=public_embed, view=GossipActionsView())

        log_embed = girly_embed(
            "✅ Gossip validé 💋",
            f"**Auteur :** <@{self.author_id}> (`{self.author_id}`)\n"
            f"**Validé par :** {interaction.user.mention} (`{interaction.user.id}`)\n"
            f"**Anonyme :** {'Oui' if self.anonymous else 'Non'}\n"
            f"**Lien :** [Voir le gossip]({public.jump_url})\n\n"
            f"**Contenu :**\n{self.content}",
            color=0xFF69B4
        )
        await log_ch.send(embed=log_embed)
        await interaction.message.edit(content="💖 Gossip validé et publié ✨", view=None)
        await interaction.response.send_message("💋 Gossip posté avec succès, XOXO 💄", ephemeral=True)

    @discord.ui.button(label="💔 Refuser", style=discord.ButtonStyle.danger, emoji="🚫", custom_id="gossip:deny")
    async def deny(self, interaction: discord.Interaction, _):
        if not await has_validation_role(interaction.user):
            return await interaction.response.send_message("🚫 Tu n’as pas la permission de refuser, sweetie 💋", ephemeral=True)

        _, log_ch = await get_channels()
        log_embed = girly_embed(
            "💔 Gossip refusé",
            f"**Auteur :** <@{self.author_id}> (`{self.author_id}`)\n"
            f"**Refusé par :** {interaction.user.mention} (`{interaction.user.id}`)\n"
            f"**Anonyme :** {'Oui' if self.anonymous else 'Non'}\n\n"
            f"**Contenu :**\n{self.content}",
            color=0xFFC0CB
        )
        await log_ch.send(embed=log_embed)
        await interaction.message.edit(content="💔 Gossip refusé 💄", view=None)
        await interaction.response.send_message("Refus noté, darling 💅", ephemeral=True)

# --------- ACTIONS SUR POSTS ----------
class GossipActionsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💭 Répondre", style=discord.ButtonStyle.secondary, custom_id="gossip:reply")
    async def reply(self, interaction: discord.Interaction, _):
        if is_banned(interaction.user.id):
            return await interaction.response.send_message("🚫 Tu es banni(e) des confessions 💔", ephemeral=True)
        await interaction.response.send_modal(ReplyModal(origin_message_id=interaction.message.id))

    @discord.ui.button(label="🔐 Nouveau Gossip", style=discord.ButtonStyle.primary, custom_id="gossip:again")
    async def again(self, interaction: discord.Interaction, _):
        await interaction.response.send_modal(SubmitModal())

class ReplyModal(discord.ui.Modal, title="💬 Répondre à ce gossip"):
    def __init__(self, origin_message_id: int):
        super().__init__()
        self.origin_message_id = origin_message_id
        self.reply = discord.ui.TextInput(label="Ta réponse", style=discord.TextStyle.paragraph, max_length=1700)
        self.anonymous = discord.ui.TextInput(label="Anonyme ? (oui/non)", style=discord.TextStyle.short, default="oui")
        self.add_item(self.reply)
        self.add_item(self.anonymous)

    async def on_submit(self, interaction: discord.Interaction):
        gossip_ch, log_ch = await get_channels()
        origin = await gossip_ch.fetch_message(self.origin_message_id)
        thread = origin.thread or await origin.create_thread(name="💬 Réponses", auto_archive_duration=1440)
        text = sanitize(str(self.reply))
        anon = str(self.anonymous).lower().strip() in ("oui","o","yes","y","true","1")
        if anon:
            await thread.send(embed=girly_embed("💭 Quelqu’un a répondu…", f"> {text}"))
        else:
            await thread.send(f"**{interaction.user.display_name} :** {text}")

        log_embed = girly_embed(
            "💬 Nouvelle réponse",
            f"**Auteur :** {interaction.user} (`{interaction.user.id}`)\n"
            f"**Anonyme :** {'Oui' if anon else 'Non'}\n"
            f"**Contenu :**\n{text}\n\n"
            f"[Aller au thread]({thread.jump_url})"
        )
        await log_ch.send(embed=log_embed)
        await interaction.response.send_message("💌 Réponse envoyée avec succès 💋", ephemeral=True)

# --------- AUTO PANEL ----------
@bot.event
async def on_ready():
    gossip_ch, _ = await get_channels()
    await gossip_ch.send(embed=embed_panel(), view=PanelView())
    log.info(f"✅ Connecté comme {bot.user} — Gossip Miri est prête 💄")

# --------- START ----------
if __name__ == "__main__":
    if TOKEN == "REPLACE_ME":
        raise SystemExit("⚠️ Mets DISCORD_TOKEN dans Railway → Variables.")
    bot.run(TOKEN)

