# -*- coding: utf-8 -*-
# 💋 Gossip El HP — Version corrigée
# Publication automatique + réponses + logs
# by ChatGPT

import os
import json
import logging
import datetime as dt
import random

import discord
from discord.ext import commands


# ============================================================
# CONFIGURATION
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1297534530558758983
GOSSIP_CHANNEL_ID = 1553007133107298364
LOG_CHANNEL_ID = 1553294899829538836

AUTHOR_NAME = "💋 Gossip El HP"
THEME_COLOR = 0xFFB6C1

PANEL_BANNER_URL = ""

BANLIST_FILE = "gossip_banlist.json"


# ============================================================
# LOGS
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

log = logging.getLogger("gossip-elhp")


# ============================================================
# BANLIST
# ============================================================

def load_banlist() -> set[int]:
    try:
        if not os.path.exists(BANLIST_FILE):
            return set()

        with open(BANLIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return {int(x) for x in data}

    except Exception:
        log.exception("Erreur pendant la lecture de la banlist")
        return set()


def save_banlist(bset: set[int]):
    try:
        with open(BANLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(list(bset), f, indent=2)

    except Exception:
        log.exception("Erreur pendant la sauvegarde de la banlist")


BANNED_USERS: set[int] = load_banlist()


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()

intents.guilds = True
intents.members = True
intents.messages = True


# ============================================================
# BOT
# ============================================================

class ElHPBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents
        )

        self.panel_sent = False

    async def setup_hook(self):

        # Enregistrement des boutons persistants
        self.add_view(PanelView())
        self.add_view(GossipActionsView())

        guild = discord.Object(id=GUILD_ID)

        try:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

            log.info("✅ Commandes synchronisées")

        except Exception:
            log.exception("❌ Impossible de synchroniser les commandes")


bot = ElHPBot()


# ============================================================
# UTILITAIRES
# ============================================================

def sanitize(text: str, limit: int = 1800) -> str:
    text = str(text).strip()

    if not text:
        return "*(Message vide)*"

    return text[:limit]


def is_banned(user_id: int) -> bool:
    return user_id in BANNED_USERS


def is_yes(value: str) -> bool:
    return str(value).lower().strip() in (
        "oui",
        "o",
        "yes",
        "y",
        "true",
        "1"
    )


async def get_channels():

    guild = bot.get_guild(GUILD_ID)

    if guild is None:
        guild = await bot.fetch_guild(GUILD_ID)

    gossip_channel = bot.get_channel(GOSSIP_CHANNEL_ID)

    if gossip_channel is None:
        gossip_channel = await bot.fetch_channel(GOSSIP_CHANNEL_ID)

    log_channel = bot.get_channel(LOG_CHANNEL_ID)

    if log_channel is None:
        log_channel = await bot.fetch_channel(LOG_CHANNEL_ID)

    return gossip_channel, log_channel


def girly_embed(
    title: str,
    description: str,
    color: int = THEME_COLOR
) -> discord.Embed:

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=dt.datetime.now(dt.timezone.utc)
    )

    embed.set_author(
        name=AUTHOR_NAME,
        icon_url="https://i.imgur.com/BqvDq6V.png"
    )

    embed.set_footer(
        text="XOXO, Gossip El HP 💄"
    )

    return embed


# ============================================================
# PANNEAU PRINCIPAL
# ============================================================

def embed_panel() -> discord.Embed:

    embed = girly_embed(
        "💋 Gossip El HP — Le Mur des Secrets",
        "Un secret ? Une rumeur ? Un crush interdit ?\n\n"
        "Ici, tout se murmure…\n"
        "Clique ci-dessous pour te confesser 👀"
    )

    if PANEL_BANNER_URL:
        embed.set_image(url=PANEL_BANNER_URL)

    return embed


class PanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Soumettre un gossip",
        style=discord.ButtonStyle.primary,
        emoji="💖",
        custom_id="gossip:open"
    )
    async def open_modal(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if is_banned(interaction.user.id):
            await interaction.response.send_message(
                "🚫 Tu es banni(e) des confessions 💔",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            SubmitModal()
        )


# ============================================================
# MODAL GOSSIP
# ============================================================

class SubmitModal(
    discord.ui.Modal,
    title="✨ Nouveau Gossip 💄"
):

    content = discord.ui.TextInput(
        label="Ton gossip",
        placeholder="Raconte ton gossip ici...",
        style=discord.TextStyle.paragraph,
        max_length=1800,
        required=True
    )

    anonymous = discord.ui.TextInput(
        label="Publier en anonyme ? (oui/non)",
        style=discord.TextStyle.short,
        default="oui",
        max_length=10,
        required=True
    )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        if is_banned(interaction.user.id):
            await interaction.response.send_message(
                "🚫 Tu es banni(e), darling 💔",
                ephemeral=True
            )
            return

        # Discord affiche "Gossip El HP réfléchit..."
        # pendant que le bot traite la demande.
        await interaction.response.defer(
            ephemeral=True,
            thinking=True
        )

        try:

            gossip_channel, log_channel = await get_channels()

            text = sanitize(self.content.value)

            anonymous = is_yes(
                self.anonymous.value
            )

            # ------------------------------------------------
            # PUBLICATION
            # ------------------------------------------------

            public_embed = girly_embed(
                random.choice([
                    "💖 Quelqu’un a chuchoté…",
                    "💅 On m’a soufflé quelque chose d’intéressant…",
                    "👠 Les rumeurs vont bon train à El HP High…",
                    "💋 Gossip Gossip Gossip…"
                ]),
                f"> {text}"
            )

            public_message = await gossip_channel.send(
                embed=public_embed,
                view=GossipActionsView()
            )

            # ------------------------------------------------
            # LOG
            # ------------------------------------------------

            auteur = (
                "Anonyme"
                if anonymous
                else f"{interaction.user} (`{interaction.user.id}`)"
            )

            log_embed = girly_embed(
                "💖 Gossip publié automatiquement",
                f"**Auteur :** {auteur}\n"
                f"**Anonyme :** {'Oui' if anonymous else 'Non'}\n"
                f"**Lien :** [Voir le gossip]({public_message.jump_url})\n\n"
                f"**Contenu :**\n{text}",
                color=0xFF69B4
            )

            await log_channel.send(
                embed=log_embed
            )

            # ------------------------------------------------
            # CONFIRMATION
            # ------------------------------------------------

            await interaction.followup.send(
                "💋 Ton gossip vient d’être publié directement "
                "sur le mur, XOXO 💄",
                ephemeral=True
            )

            log.info(
                "Gossip publié | auteur=%s | anonyme=%s",
                interaction.user.id,
                anonymous
            )

        except Exception as error:

            log.exception(
                "❌ ERREUR lors de la publication du gossip"
            )

            try:
                await interaction.followup.send(
                    "❌ Oups, Gossip El HP a rencontré un problème "
                    "pendant la publication.\n\n"
                    "Les logs ont été enregistrés.",
                    ephemeral=True
                )

            except Exception:
                log.exception(
                    "Impossible d'envoyer le message d'erreur"
                )


# ============================================================
# BOUTONS DES GOSSIPS
# ============================================================

class GossipActionsView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Répondre",
        style=discord.ButtonStyle.secondary,
        emoji="💬",
        custom_id="gossip:reply"
    )
    async def reply(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if is_banned(interaction.user.id):
            await interaction.response.send_message(
                "🚫 Tu es banni(e) 💔",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            ReplyModal(
                origin_message_id=interaction.message.id
            )
        )

    @discord.ui.button(
        label="Nouveau Gossip",
        style=discord.ButtonStyle.primary,
        emoji="💖",
        custom_id="gossip:again"
    )
    async def again(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if is_banned(interaction.user.id):
            await interaction.response.send_message(
                "🚫 Tu es banni(e) 💔",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            SubmitModal()
        )


# ============================================================
# MODAL RÉPONSE
# ============================================================

class ReplyModal(
    discord.ui.Modal,
    title="💬 Répondre à ce gossip"
):

    def __init__(
        self,
        origin_message_id: int
    ):
        super().__init__()

        self.origin_message_id = origin_message_id

        self.reply_input = discord.ui.TextInput(
            label="Ta réponse",
            placeholder="Écris ta réponse...",
            style=discord.TextStyle.paragraph,
            max_length=1700,
            required=True
        )

        self.anonymous_input = discord.ui.TextInput(
            label="Anonyme ? (oui/non)",
            style=discord.TextStyle.short,
            default="oui",
            max_length=10,
            required=True
        )

        self.add_item(self.reply_input)
        self.add_item(self.anonymous_input)

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        if is_banned(interaction.user.id):
            await interaction.response.send_message(
                "🚫 Tu es banni(e) 💔",
                ephemeral=True
            )
            return

        # Évite que Discord considère la réponse comme timeout
        await interaction.response.defer(
            ephemeral=True,
            thinking=True
        )

        try:

            gossip_channel, log_channel = await get_channels()

            origin = await gossip_channel.fetch_message(
                self.origin_message_id
            )

            # ------------------------------------------------
            # THREAD
            # ------------------------------------------------

            thread = origin.thread

            if thread is None:

                thread = await origin.create_thread(
                    name="💬 Réponses",
                    auto_archive_duration=1440
                )

            text = sanitize(
                self.reply_input.value
            )

            anonymous = is_yes(
                self.anonymous_input.value
            )

            # ------------------------------------------------
            # PUBLICATION RÉPONSE
            # ------------------------------------------------

            if anonymous:

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

            # ------------------------------------------------
            # LOG
            # ------------------------------------------------

            log_embed = girly_embed(
                "💬 Nouvelle réponse",
                f"**Auteur :** "
                f"{interaction.user} (`{interaction.user.id}`)\n"
                f"**Anonyme :** "
                f"{'Oui' if anonymous else 'Non'}\n\n"
                f"**Contenu :**\n{text}\n\n"
                f"[Aller au thread]({thread.jump_url})"
            )

            await log_channel.send(
                embed=log_embed
            )

            # ------------------------------------------------
            # CONFIRMATION
            # ------------------------------------------------

            await interaction.followup.send(
                "💌 Réponse envoyée 💋",
                ephemeral=True
            )

            log.info(
                "Réponse publiée | auteur=%s | anonyme=%s",
                interaction.user.id,
                anonymous
            )

        except Exception:

            log.exception(
                "❌ ERREUR lors de l'envoi d'une réponse"
            )

            try:

                await interaction.followup.send(
                    "❌ Oups, impossible d’envoyer ta réponse "
                    "pour le moment.",
                    ephemeral=True
                )

            except Exception:
                log.exception(
                    "Impossible d'envoyer le message d'erreur"
                )


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    log.info(
        "✅ Connecté comme %s (%s)",
        bot.user,
        bot.user.id
    )

    log.info(
        "💋 Gossip El HP est opérationnelle"
    )

    # --------------------------------------------------------
    # PANNEAU
    # --------------------------------------------------------
    #
    # On ne renvoie PAS le panneau à chaque reconnexion.
    # Cela évite d'avoir 50 panneaux identiques dans le salon.
    #

    if not bot.panel_sent:

        try:

            gossip_channel, _ = await get_channels()

            # Cherche un panneau récent du bot
            found = False

            async for message in gossip_channel.history(
                limit=50
            ):

                if (
                    message.author.id == bot.user.id
                    and message.embeds
                    and message.embeds[0].title
                    and "Gossip El HP" in message.embeds[0].title
                ):
                    found = True
                    break

            if not found:

                await gossip_channel.send(
                    embed=embed_panel(),
                    view=PanelView()
                )

                log.info(
                    "💖 Panneau Gossip envoyé"
                )

            else:

                log.info(
                    "💖 Panneau déjà présent, aucun doublon"
                )

            bot.panel_sent = True

        except Exception:

            log.exception(
                "❌ Impossible d'initialiser le panneau"
            )


# ============================================================
# ERREURS GLOBALES
# ============================================================

@bot.event
async def on_error(
    event_method,
    *args,
    **kwargs
):

    log.exception(
        "❌ Erreur Discord dans %s",
        event_method
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    if not TOKEN:

        raise SystemExit(
            "❌ DISCORD_TOKEN est absent des variables "
            "d'environnement Railway."
        )

    if TOKEN == "REPLACE_ME":

        raise SystemExit(
            "❌ Remplace REPLACE_ME par ton DISCORD_TOKEN."
        )

    log.info(
        "🚀 Démarrage de Gossip El HP..."
    )

    bot.run(TOKEN)