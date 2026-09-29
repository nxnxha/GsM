# -*- coding: utf-8 -*-

# ============================================================
# 🖤 GOSSIP EL HP — DARK EDITION
# ============================================================
# - Panneau automatique
# - Mise à jour du panneau existant au redémarrage
# - Confessions anonymes
# - Réponses en thread
# - Logs avec vraie identité + ID Discord
# - Bouton de blocage depuis les logs
# - Banlist persistante
# - /gossip_unban
# - /gossip_check
# - Boutons persistants après redémarrage
# ============================================================

import os
import json
import logging
import datetime as dt
import random

import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# CONFIGURATION
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1297534530558758983

GOSSIP_CHANNEL_ID = 1553007133107298364
LOG_CHANNEL_ID = 1553294899829538836

BANLIST_FILE = "gossip_banlist.json"

AUTHOR_NAME = "GOSSIP EL HP"

DARK_COLOR = 0x111111
BURGUNDY_COLOR = 0x641C2C
RED_COLOR = 0x8B2635

PANEL_BANNER_URL = ""

AUTHOR_ICON_URL = "https://i.imgur.com/BqvDq6V.png"


# ============================================================
# LOGGING
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

        with open(
            BANLIST_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        return {int(user_id) for user_id in data}

    except Exception:
        log.exception("Erreur pendant la lecture de la banlist")
        return set()


def save_banlist(bset: set[int]):
    try:
        with open(
            BANLIST_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                sorted(list(bset)),
                f,
                indent=2
            )

    except Exception:
        log.exception("Erreur pendant la sauvegarde de la banlist")


BANNED_USERS: set[int] = load_banlist()


def is_banned(user_id: int) -> bool:
    return user_id in BANNED_USERS


def ban_user(user_id: int):
    BANNED_USERS.add(user_id)
    save_banlist(BANNED_USERS)


def unban_user(user_id: int):
    BANNED_USERS.discard(user_id)
    save_banlist(BANNED_USERS)


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()

intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True


# ============================================================
# OUTILS
# ============================================================

def sanitize(
    text: str,
    limit: int = 1800
) -> str:

    text = str(text).strip()

    if not text:
        return "*(Message vide)*"

    return text[:limit]


def is_yes(value: str) -> bool:

    return str(value).lower().strip() in (
        "oui",
        "o",
        "yes",
        "y",
        "true",
        "1"
    )


def is_moderator(
    interaction: discord.Interaction
) -> bool:

    if not interaction.guild:
        return False

    permissions = interaction.user.guild_permissions

    return (
        permissions.administrator
        or permissions.manage_guild
        or permissions.manage_messages
    )


# ============================================================
# EMBEDS
# ============================================================

def dark_embed(
    title: str,
    description: str,
    color: int = DARK_COLOR
) -> discord.Embed:

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=dt.datetime.now(
            dt.timezone.utc
        )
    )

    embed.set_author(
        name=AUTHOR_NAME,
        icon_url=AUTHOR_ICON_URL
    )

    embed.set_footer(
        text="XOXO — Gossip El HP"
    )

    return embed


# ============================================================
# EMBED DU PANNEAU
# ============================================================

def embed_panel() -> discord.Embed:

    embed = dark_embed(
        "GOSSIP EL HP",
        "**LE MUR DES SECRETS**\n\n"
        "Une confession.\n"
        "Une rumeur.\n"
        "Un crush.\n"
        "Un secret.\n\n"
        "Tout peut être raconté ici.\n\n"
        "Clique sur le bouton ci-dessous "
        "pour envoyer ton gossip.\n\n"
        "*Les publications peuvent être anonymes.*",
        BURGUNDY_COLOR
    )

    if PANEL_BANNER_URL:
        embed.set_image(
            url=PANEL_BANNER_URL
        )

    return embed


# ============================================================
# BOT
# ============================================================

class ElHPBot(commands.Bot):

    def __init__(self):

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents
        )

    async def setup_hook(self):

        # Boutons persistants
        self.add_view(
            PanelView()
        )

        self.add_view(
            GossipActionsView()
        )

        self.add_view(
            LogActionsView()
        )

        # Synchronisation des commandes
        guild = discord.Object(
            id=GUILD_ID
        )

        try:

            self.tree.copy_global_to(
                guild=guild
            )

            await self.tree.sync(
                guild=guild
            )

            log.info(
                "Commandes synchronisées."
            )

        except Exception:

            log.exception(
                "Erreur pendant la synchronisation "
                "des commandes."
            )


bot = ElHPBot()


# ============================================================
# SALONS
# ============================================================

async def get_channels():

    gossip_channel = bot.get_channel(
        GOSSIP_CHANNEL_ID
    )

    if gossip_channel is None:

        gossip_channel = await bot.fetch_channel(
            GOSSIP_CHANNEL_ID
        )

    log_channel = bot.get_channel(
        LOG_CHANNEL_ID
    )

    if log_channel is None:

        log_channel = await bot.fetch_channel(
            LOG_CHANNEL_ID
        )

    return gossip_channel, log_channel


# ============================================================
# PANNEAU PRINCIPAL
# ============================================================

class PanelView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Soumettre un gossip",
        style=discord.ButtonStyle.secondary,
        emoji="🖤",
        custom_id="gossip:open"
    )
    async def open_modal(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if is_banned(
            interaction.user.id
        ):

            await interaction.response.send_message(
                "Tu n'as plus accès aux confessions.",
                ephemeral=True
            )

            return

        try:

            await interaction.response.send_modal(
                SubmitModal()
            )

        except Exception:

            log.exception(
                "Erreur ouverture SubmitModal"
            )


# ============================================================
# MODAL GOSSIP
# ============================================================

class SubmitModal(
    discord.ui.Modal
):

    def __init__(self):

        super().__init__(
            title="Gossip El HP"
        )

        self.content = discord.ui.TextInput(
            label="Ton gossip",
            placeholder="Écris ta confession...",
            style=discord.TextStyle.paragraph,
            max_length=1800,
            required=True
        )

        self.anonymous = discord.ui.TextInput(
            label="Publier anonymement ?",
            placeholder="oui / non",
            style=discord.TextStyle.short,
            default="oui",
            max_length=10,
            required=True
        )

        self.add_item(
            self.content
        )

        self.add_item(
            self.anonymous
        )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        if is_banned(
            interaction.user.id
        ):

            await interaction.response.send_message(
                "Tu n'as plus accès aux confessions.",
                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True,
            thinking=True
        )

        try:

            gossip_channel, log_channel = (
                await get_channels()
            )

            text = sanitize(
                self.content.value
            )

            anonymous = is_yes(
                self.anonymous.value
            )

            # ------------------------------------------------
            # MESSAGE PUBLIC
            # ------------------------------------------------

            public_embed = dark_embed(
                random.choice([
                    "Quelqu'un a parlé.",
                    "Une confession vient d'arriver.",
                    "Une rumeur circule...",
                    "Quelqu'un murmure dans l'ombre.",
                    "Le mur des secrets s'agrandit."
                ]),
                f"> {text}",
                BURGUNDY_COLOR
            )

            public_message = await gossip_channel.send(
                embed=public_embed,
                view=GossipActionsView()
            )

            # ------------------------------------------------
            # IDENTITÉ RÉELLE
            # ------------------------------------------------

            user_id = interaction.user.id
            username = interaction.user.name
            display_name = interaction.user.display_name
            mention = interaction.user.mention

            # ------------------------------------------------
            # LOG
            # ------------------------------------------------

            log_embed = dark_embed(
                "NOUVEAU GOSSIP",
                "Une nouvelle confession vient d'être publiée.",
                RED_COLOR
            )

            log_embed.add_field(
                name="Auteur réel",
                value=(
                    f"{mention}\n"
                    f"**Pseudo affiché :** {display_name}\n"
                    f"**Username :** `{username}`"
                ),
                inline=False
            )

            log_embed.add_field(
                name="ID Discord",
                value=f"`{user_id}`",
                inline=False
            )

            log_embed.add_field(
                name="Publication anonyme",
                value=(
                    "Oui"
                    if anonymous
                    else "Non"
                ),
                inline=True
            )

            log_embed.add_field(
                name="Contenu",
                value=f"> {text}",
                inline=False
            )

            log_embed.add_field(
                name="Publication",
                value=(
                    f"[Voir le gossip]"
                    f"({public_message.jump_url})"
                ),
                inline=False
            )

            await log_channel.send(
                embed=log_embed,
                view=LogActionsView()
            )

            await interaction.followup.send(
                "Ton gossip a été publié.",
                ephemeral=True
            )

            log.info(
                "Gossip publié | user=%s | anonymous=%s",
                user_id,
                anonymous
            )

        except Exception as e:

            log.exception(
                "Erreur publication gossip"
            )

            try:

                await interaction.followup.send(
                    "Erreur pendant la publication.\n"
                    f"`{type(e).__name__}: {e}`",
                    ephemeral=True
                )

            except Exception:

                log.exception(
                    "Impossible d'envoyer le message d'erreur."
                )


# ============================================================
# BOUTONS DES GOSSIPS
# ============================================================

class GossipActionsView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

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

        if is_banned(
            interaction.user.id
        ):

            await interaction.response.send_message(
                "Tu n'as plus accès aux confessions.",
                ephemeral=True
            )

            return

        try:

            await interaction.response.send_modal(
                ReplyModal(
                    interaction.message.id
                )
            )

        except Exception:

            log.exception(
                "Erreur ouverture ReplyModal"
            )


    @discord.ui.button(
        label="Nouveau Gossip",
        style=discord.ButtonStyle.secondary,
        emoji="✦",
        custom_id="gossip:again"
    )
    async def again(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if is_banned(
            interaction.user.id
        ):

            await interaction.response.send_message(
                "Tu n'as plus accès aux confessions.",
                ephemeral=True
            )

            return

        try:

            await interaction.response.send_modal(
                SubmitModal()
            )

        except Exception:

            log.exception(
                "Erreur ouverture nouveau SubmitModal"
            )


# ============================================================
# MODAL RÉPONSE
# ============================================================

class ReplyModal(
    discord.ui.Modal
):

    def __init__(
        self,
        origin_message_id: int
    ):

        super().__init__(
            title="Répondre au gossip"
        )

        self.origin_message_id = (
            origin_message_id
        )

        self.reply_input = discord.ui.TextInput(
            label="Ta réponse",
            placeholder="Écris ta réponse...",
            style=discord.TextStyle.paragraph,
            max_length=1700,
            required=True
        )

        self.anonymous_input = discord.ui.TextInput(
            label="Répondre anonymement ?",
            placeholder="oui / non",
            style=discord.TextStyle.short,
            default="oui",
            max_length=10,
            required=True
        )

        self.add_item(
            self.reply_input
        )

        self.add_item(
            self.anonymous_input
        )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        if is_banned(
            interaction.user.id
        ):

            await interaction.response.send_message(
                "Tu n'as plus accès aux confessions.",
                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True,
            thinking=True
        )

        try:

            gossip_channel, log_channel = (
                await get_channels()
            )

            origin = await gossip_channel.fetch_message(
                self.origin_message_id
            )

            thread = origin.thread

            if thread is None:

                thread = await origin.create_thread(
                    name="Réponses",
                    auto_archive_duration=1440
                )

            text = sanitize(
                self.reply_input.value
            )

            anonymous = is_yes(
                self.anonymous_input.value
            )

            # ------------------------------------------------
            # PUBLIC
            # ------------------------------------------------

            if anonymous:

                await thread.send(
                    embed=dark_embed(
                        "Quelqu'un a répondu...",
                        f"> {text}",
                        DARK_COLOR
                    )
                )

            else:

                await thread.send(
                    f"**{interaction.user.display_name}**\n"
                    f"> {text}"
                )

            # ------------------------------------------------
            # LOG
            # ------------------------------------------------

            log_embed = dark_embed(
                "NOUVELLE RÉPONSE",
                "Une réponse vient d'être publiée.",
                BURGUNDY_COLOR
            )

            log_embed.add_field(
                name="Auteur réel",
                value=(
                    f"{interaction.user.mention}\n"
                    f"**Pseudo affiché :** "
                    f"{interaction.user.display_name}\n"
                    f"**Username :** "
                    f"`{interaction.user.name}`"
                ),
                inline=False
            )

            log_embed.add_field(
                name="ID Discord",
                value=f"`{interaction.user.id}`",
                inline=False
            )

            log_embed.add_field(
                name="Réponse anonyme",
                value=(
                    "Oui"
                    if anonymous
                    else "Non"
                ),
                inline=True
            )

            log_embed.add_field(
                name="Contenu",
                value=f"> {text}",
                inline=False
            )

            log_embed.add_field(
                name="Thread",
                value=f"[Voir]({thread.jump_url})",
                inline=False
            )

            await log_channel.send(
                embed=log_embed,
                view=LogActionsView()
            )

            await interaction.followup.send(
                "Réponse envoyée.",
                ephemeral=True
            )

        except Exception as e:

            log.exception(
                "Erreur réponse gossip"
            )

            try:

                await interaction.followup.send(
                    "Erreur pendant l'envoi de la réponse.\n"
                    f"`{type(e).__name__}: {e}`",
                    ephemeral=True
                )

            except Exception:
                pass


# ============================================================
# ACTIONS DANS LES LOGS
# ============================================================

class LogActionsView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Bloquer cet utilisateur",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="gossip:ban_author"
    )
    async def ban_author(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_moderator(
            interaction
        ):

            await interaction.response.send_message(
                "Tu n'as pas la permission d'utiliser "
                "ce bouton.",
                ephemeral=True
            )

            return

        if not interaction.message.embeds:

            await interaction.response.send_message(
                "Impossible de récupérer l'auteur.",
                ephemeral=True
            )

            return

        embed = interaction.message.embeds[0]

        user_id = None

        for field in embed.fields:

            if field.name == "ID Discord":

                raw_id = (
                    field.value
                    .replace("`", "")
                    .strip()
                )

                try:
                    user_id = int(raw_id)
                except ValueError:
                    user_id = None

                break

        if user_id is None:

            await interaction.response.send_message(
                "ID Discord introuvable.",
                ephemeral=True
            )

            return

        if bot.user and user_id == bot.user.id:

            await interaction.response.send_message(
                "Je ne peux pas bloquer le bot.",
                ephemeral=True
            )

            return

        already_banned = is_banned(
            user_id
        )

        ban_user(
            user_id
        )

        if already_banned:

            message = (
                f"`{user_id}` est déjà bloqué."
            )

        else:

            message = (
                f"`{user_id}` est maintenant bloqué "
                f"des confessions."
            )

        await interaction.response.send_message(
            message,
            ephemeral=True
        )

        log.info(
            "Utilisateur bloqué | user=%s | moderator=%s",
            user_id,
            interaction.user.id
        )


# ============================================================
# COMMANDE UNBAN
# ============================================================

@bot.tree.command(
    name="gossip_unban",
    description="Débloque un utilisateur des confessions."
)
@app_commands.describe(
    user_id="ID Discord de l'utilisateur"
)
async def gossip_unban(
    interaction: discord.Interaction,
    user_id: str
):

    if not is_moderator(
        interaction
    ):

        await interaction.response.send_message(
            "Tu n'as pas la permission.",
            ephemeral=True
        )

        return

    try:

        target_id = int(
            user_id
        )

    except ValueError:

        await interaction.response.send_message(
            "L'ID Discord doit être un nombre.",
            ephemeral=True
        )

        return

    if not is_banned(
        target_id
    ):

        await interaction.response.send_message(
            f"`{target_id}` n'est pas bloqué.",
            ephemeral=True
        )

        return

    unban_user(
        target_id
    )

    await interaction.response.send_message(
        f"`{target_id}` peut de nouveau "
        f"envoyer des confessions.",
        ephemeral=True
    )


# ============================================================
# COMMANDE CHECK
# ============================================================

@bot.tree.command(
    name="gossip_check",
    description="Vérifie si un utilisateur est bloqué."
)
@app_commands.describe(
    user_id="ID Discord de l'utilisateur"
)
async def gossip_check(
    interaction: discord.Interaction,
    user_id: str
):

    if not is_moderator(
        interaction
    ):

        await interaction.response.send_message(
            "Tu n'as pas la permission.",
            ephemeral=True
        )

        return

    try:

        target_id = int(
            user_id
        )

    except ValueError:

        await interaction.response.send_message(
            "L'ID Discord doit être un nombre.",
            ephemeral=True
        )

        return

    status = (
        "BLOQUÉ"
        if is_banned(target_id)
        else "AUTORISÉ"
    )

    await interaction.response.send_message(
        f"Utilisateur `{target_id}` : **{status}**",
        ephemeral=True
    )


# ============================================================
# MISE À JOUR DU PANNEAU
# ============================================================

async def update_gossip_panel():

    gossip_channel, _ = (
        await get_channels()
    )

    existing_panel = None

    try:

        async for message in gossip_channel.history(
            limit=100
        ):

            if message.author.id != bot.user.id:
                continue

            if not message.embeds:
                continue

            title = (
                message.embeds[0].title or ""
            ).strip().upper()

            # Le panneau actuel
            if title == "GOSSIP EL HP":

                existing_panel = message
                break

    except Exception:

        log.exception(
            "Impossible de parcourir l'historique "
            "du salon Gossip."
        )

        return

    # --------------------------------------------------------
    # PANNEAU TROUVÉ
    # --------------------------------------------------------

    if existing_panel:

        try:

            await existing_panel.edit(
                embed=embed_panel(),
                view=PanelView()
            )

            log.info(
                "Panneau Gossip existant mis à jour."
            )

            return

        except Exception:

            log.exception(
                "Impossible de modifier le panneau existant."
            )

    # --------------------------------------------------------
    # PAS DE PANNEAU
    # --------------------------------------------------------

    try:

        await gossip_channel.send(
            embed=embed_panel(),
            view=PanelView()
        )

        log.info(
            "Nouveau panneau Gossip créé."
        )

    except Exception:

        log.exception(
            "Impossible de créer le panneau Gossip."
        )


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    log.info(
        "Connecté comme %s (%s)",
        bot.user,
        bot.user.id
    )

    log.info(
        "Gossip El HP opérationnelle."
    )

    try:

        await update_gossip_panel()

    except Exception:

        log.exception(
            "Erreur pendant l'initialisation du panneau."
        )


# ============================================================
# ERREURS
# ============================================================

@bot.event
async def on_error(
    event_method,
    *args,
    **kwargs
):

    log.exception(
        "Erreur Discord dans %s",
        event_method
    )


# ============================================================
# DÉMARRAGE
# ============================================================

if __name__ == "__main__":

    if not TOKEN:

        raise SystemExit(
            "❌ DISCORD_TOKEN est absent des variables "
            "d'environnement Railway."
        )

    log.info(
        "🚀 Démarrage de Gossip El HP..."
    )

    bot.run(TOKEN)