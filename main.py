# -*- coding: utf-8 -*-
# 💋 Gossip El HP — Version sans validation admin
# by ChatGPT 💄

import os, json, logging, datetime as dt, random
import discord
from discord import app_commands
from discord.ext import commands

# --------- CONFIGURATION ----------
TOKEN = os.getenv("DISCORD_TOKEN", "REPLACE_ME")

# salons
GUILD_ID = 1297534530558758983
GOSSIP_CHANNEL_ID = 1553007133107298364
LOG_CHANNEL_ID = 1504250342722895963


# esthétique
AUTHOR_NAME = "💋 Gossip El HP"
THEME_COLOR = 0xFFB6C1
PANEL_BANNER_URL = ""
PIN_MESSAGE = False
BANLIST_FILE = "gossip_banlist.json"

# --------- LOG ----------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("gossip-elhp")

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

class ElHPBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents
        )
        self.synced = False

    async def setup_hook(self):
        # Views persistantes
        self.add_view(PanelView())
        self.add_view(GossipActionsView())

        gobj = discord.Object(id=GUILD_ID)

        self.tree.copy_global_to(guild=gobj)

        if not self.synced:
            await self.tree.sync(guild=gobj)
            self.synced = True

bot = ElHPBot()

# --------- UTILITAIRES ----------
def sanitize(text: str, limit: int = 1800) -> str:
    return text.strip()[:limit]

def is_banned(uid: int) -> bool:
    return uid in BANNED_USERS

async def get_channels():
    guild = bot.get_guild(GUILD_ID) or await bot.fetch_guild(GUILD_ID)

    gossip_ch = (
        guild.get_channel(GOSSIP_CHANNEL_ID)
        or await bot.fetch_channel(GOSSIP_CHANNEL_ID)
    )

    log_ch = (
        guild.get_channel(LOG_CHANNEL_ID)
        or await bot.fetch_channel(LOG_CHANNEL_ID)
    )

    return gossip_ch, log_ch

def girly_embed(
    title: str,
    desc: str,
    color=THEME_COLOR
) -> discord.Embed:

    emb = discord.Embed(
        title=title,
        description=desc,
        color=color,
        timestamp=dt.datetime.utcnow()
    )

    emb.set_author(
        name=AUTHOR_NAME,
        icon_url="https://i.imgur.com/BqvDq6V.png"
    )

    emb.set_footer(text="XOXO, Gossip El HP 💄")

    return emb

# --------- PANEL ----------
def embed_panel() -> discord.Embed:
    emb = girly_embed(
        "💋 Gossip El HP — Le Mur des Secrets",
        "Un secret ? Une rumeur ? Un crush interdit ?\n"
        "Ici, tout se murmure… Clique ci-dessous pour te confesser 👀"
    )

    if PANEL_BANNER_URL:
        emb.set_image(url=PANEL_BANNER_URL)

    return emb


class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Soumettre un gossip 💌",
        style=discord.ButtonStyle.primary,
        emoji="💖",
        custom_id="gossip:open"
    )
    async def open_modal(
        self,
        interaction: discord.Interaction,
        _
    ):

        if is_banned(interaction.user.id):
            return await interaction.response.send_message(
                "🚫 Tu es banni(e) des confessions 💔",
                ephemeral=True
            )

        await interaction.response.send_modal(SubmitModal())


# --------- SUBMISSION ----------
class SubmitModal(
    discord.ui.Modal,
    title="✨ Nouveau Gossip 💄"
):

    content = discord.ui.TextInput(
        label="Ton gossip (reste chic, gossip girl style)",
        style=discord.TextStyle.paragraph,
        max_length=1800
    )

    anonymous = discord.ui.TextInput(
        label="Publier en anonyme ? (oui/non)",
        style=discord.TextStyle.short,
        default="oui"
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        if is_banned(interaction.user.id):
            return await interaction.response.send_message(
                "🚫 Tu es banni(e), darling 💔",
                ephemeral=True
            )

        await interaction.response.defer(
            ephemeral=True,
            thinking=True
        )

        gossip_ch, log_ch = await get_channels()

        text = sanitize(str(self.content))

        anon = (
            str(self.anonymous)
            .lower()
            .strip()
            in ("oui", "o", "yes", "y", "true", "1")
        )

        # --------- PUBLICATION DIRECTE ----------
        role = gossip_ch.guild.get_role(PUBLIC_ROLE_ID)

        public_embed = girly_embed(
            random.choice([
                "💖 Quelqu’un a chuchoté…",
                "💅 On m’a soufflé quelque chose d’intéressant…",
                "👠 Les rumeurs vont bon train à El HP High…"
            ]),
            f"> {text}"
        )

        public = await gossip_ch.send(
            content=role.mention if role else None,
            embed=public_embed,
            view=GossipActionsView()
        )

        # --------- LOG ----------
        auteur = (
            "Anonyme"
            if anon
            else f"{interaction.user} (`{interaction.user.id}`)"
        )

        log_embed = girly_embed(
            "💖 Gossip publié automatiquement",
            f"**Auteur :** {auteur}\n"
            f"**Anonyme :** {'Oui' if anon else 'Non'}\n"
            f"**Lien :** [Voir le gossip]({public.jump_url})\n\n"
            f"**Contenu :**\n{text}",
            color=0xFF69B4
        )

        await log_ch.send(embed=log_embed)

        await interaction.followup.send(
            "💋 Ton gossip vient d'être publié directement sur le mur, XOXO 💄",
            ephemeral=True
        )


# --------- ACTIONS ----------
class GossipActionsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="💭 Répondre",
        style=discord.ButtonStyle.secondary,
        emoji="💬",
        custom_id="gossip:reply"
    )
    async def reply(
        self,
        interaction: discord.Interaction,
        _
    ):

        if is_banned(interaction.user.id):
            return await interaction.response.send_message(
                "🚫 Tu es banni(e) 💔",
                ephemeral=True
            )

        await interaction.response.send_modal(
            ReplyModal(
                origin_message_id=interaction.message.id
            )
        )

    @discord.ui.button(
        label="💌 Nouveau Gossip",
        style=discord.ButtonStyle.primary,
        emoji="💖",
        custom_id="gossip:again"
    )
    async def again(
        self,
        interaction: discord.Interaction,
        _
    ):

        if is_banned(interaction.user.id):
            return await interaction.response.send_message(
                "🚫 Tu es banni(e) 💔",
                ephemeral=True
            )

        await interaction.response.send_modal(
            SubmitModal()
        )


# --------- REPLY ----------
class ReplyModal(
    discord.ui.Modal,
    title="💬 Répondre à ce gossip"
):

    def __init__(self, origin_message_id: int):
        super().__init__()

        self.origin_message_id = origin_message_id

        self.reply = discord.ui.TextInput(
            label="Ta réponse",
            style=discord.TextStyle.paragraph,
            max_length=1700
        )

        self.anonymous = discord.ui.TextInput(
            label="Anonyme ? (oui/non)",
            style=discord.TextStyle.short,
            default="oui"
        )

        self.add_item(self.reply)
        self.add_item(self.anonymous)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        if is_banned(interaction.user.id):
            return await interaction.response.send_message(
                "🚫 Tu es banni(e) 💔",
                ephemeral=True
            )

        gossip_ch, log_ch = await get_channels()

        origin = await gossip_ch.fetch_message(
            self.origin_message_id
        )

        thread = (
            origin.thread
            or await origin.create_thread(
                name="💬 Réponses",
                auto_archive_duration=1440
            )
        )

        text = sanitize(str(self.reply))

        anon = (
            str(self.anonymous)
            .lower()
            .strip()
            in ("oui", "o", "yes", "y", "true", "1")
        )

        if anon:
            await thread.send(
                embed=girly_embed(
                    "💭 Quelqu’un a répondu…",
                    f"> {text}"
                )
            )
        else:
            await thread.send(
                f"**{interaction.user.display_name} :** {text}"
            )

        # --------- LOG ----------
        log_embed = girly_embed(
            "💬 Nouvelle réponse",
            f"**Auteur :** {interaction.user} (`{interaction.user.id}`)\n"
            f"**Anonyme :** {'Oui' if anon else 'Non'}\n"
            f"**Contenu :**\n{text}\n\n"
            f"[Aller au thread]({thread.jump_url})"
        )

        await log_ch.send(embed=log_embed)

        await interaction.response.send_message(
            "💌 Réponse envoyée 💋",
            ephemeral=True
        )


# --------- AUTO PANEL ----------
@bot.event
async def on_ready():

    gossip_ch, _ = await get_channels()

    await gossip_ch.send(
        embed=embed_panel(),
        view=PanelView()
    )

    log.info(
        f"✅ Connecté comme {bot.user} — "
        f"Gossip El HP est prête 💄"
    )


# --------- START ----------
if __name__ == "__main__":

    if TOKEN == "REPLACE_ME":
        raise SystemExit(
            "⚠️ Ajoute ton DISCORD_TOKEN dans Railway ou .env"
        )

    bot.run(TOKEN)
