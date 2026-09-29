# -*- coding: utf-8 -*-
# ============================================================
# 🖤 GOSSIP EL HP — DARK EDITION
# Publication automatique + réponses + logs privés
# Identification réelle des auteurs dans les logs
# Système de blocage / déblocage des confessions
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


# ============================================================
# ESTHÉTIQUE
# ============================================================

AUTHOR_NAME = "GOSSIP EL HP"

# Noir / bordeaux / argent
DARK_COLOR = 0x111111
BURGUNDY_COLOR = 0x641C2C
RED_COLOR = 0x8B2635
SILVER_COLOR = 0xC7C7C7
WHITE_COLOR = 0xF2F2F2

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

        return {
            int(user_id)
            for user_id in data
        }

    except Exception:

        log.exception(
            "Erreur pendant la lecture de la banlist"
        )

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

        log.exception(
            "Erreur pendant la sauvegarde de la banlist"
        )


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


# ============================================================
# UTILITAIRES
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


def moderator(interaction: discord.Interaction) -> bool:

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
        timestamp=dt.datetime.now(dt.timezone.utc)
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

        # ----------------------------------------------------
        # VUES PERSISTANTES
        # ----------------------------------------------------

        self.add_view(
            PanelView()
        )

        self.add_view(
            GossipActionsView()
        )

        self.add_view(
            LogActionsView()
        )

        # ----------------------------------------------------
        # COMMANDES
        # ----------------------------------------------------

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
                "Commandes synchronisées"
            )

        except Exception:

            log.exception(
                "Impossible de synchroniser les commandes"
            )


bot = ElHPBot()


# ============================================================
# CHANNELS
# ============================================================

async def get_channels():

    guild = bot.get_guild(
        GUILD_ID
    )

    if guild is None:

        guild = await bot.fetch_guild(
            GUILD_ID
        )

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

def embed_panel() -> discord.Embed:

    embed = dark_embed(
        "GOSSIP EL HP",
        "**LE MUR DES SECRETS**\n\n"
        "Une confession.\n"
        "Une rumeur.\n"
        "Un crush.\n"
        "Un secret que personne ne devrait connaître.\n\n"
        "Tout peut être raconté ici.\n\n"
        "Clique sur le bouton ci-dessous pour envoyer "
        "ton gossip.\n\n"
        "*Les publications peuvent être anonymes.*",
        BURGUNDY_COLOR
    )

    if PANEL_BANNER_URL:

        embed.set_image(
            url=PANEL_BANNER_URL
        )

    return embed


class PanelView(discord.ui.View):

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

        await interaction.response.send_modal(
            SubmitModal()
        )


# ============================================================
# MODAL GOSSIP
# ============================================================

class SubmitModal(
    discord.ui.Modal,
    title="Gossip El HP"
):

    content = discord.ui.TextInput(
        label="Ton gossip",
        placeholder="Écris ta confession...",
        style=discord.TextStyle.paragraph,
        max_length=1800,
        required=True
    )

    anonymous = discord.ui.TextInput(
        label="Publier anonymement ?",
        placeholder="oui / non",
        style=discord.TextStyle.short,
        default="oui",
        max_length=10,
        required=True
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

            # =================================================
            # PUBLIC
            # =================================================

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

            # =================================================
            # IDENTITÉ RÉELLE
            # =================================================

            # IMPORTANT :
            # Même si le gossip est anonyme publiquement,
            # les vrais renseignements restent visibles
            # dans le salon de logs.

            username = interaction.user.name

            display_name = (
                interaction.user.display_name
            )

            user_id = interaction.user.id

            mention = interaction.user.mention

            anonymity_text = (
                "Oui"
                if anonymous
                else "Non"
            )

            # =================================================
            # LOG
            # =================================================

            log_embed = dark_embed(
                "NOUVEAU GOSSIP",
                "Une nouvelle confession vient "
                "d'être publiée.",
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
                value=anonymity_text,
                inline=True
            )

            log_embed.add_field(
                name="Message",
                value=f"> {text}",
                inline=False
            )

            log_embed.add_field(
                name="Lien",
                value=(
                    f"[Voir le gossip]("
                    f"{public_message.jump_url})"
                ),
                inline=False
            )

            await log_channel.send(
                embed=log_embed,
                view=LogActionsView()
            )

            # =================================================
            # CONFIRMATION
            # =================================================

            await interaction.followup.send(
                "Ton gossip a été publié.",
                ephemeral=True
            )

            log.info(
                "Gossip publié | user=%s | username=%s | "
                "display=%s | anonymous=%s",
                user_id,
                username,
                display_name,
                anonymous
            )

        except Exception:

            log.exception(
                "Erreur lors de la publication du gossip"
            )

            try:

                await interaction.followup.send(
                    "Une erreur est survenue pendant "
                    "la publication.",
                    ephemeral=True
                )

            except Exception:

                log.exception(
                    "Impossible d'envoyer le message d'erreur"
                )


# ============================================================
# ACTIONS DES GOSSIPS
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

        await interaction.response.send_modal(
            ReplyModal(
                origin_message_id=interaction.message.id
            )
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

        await interaction.response.send_modal(
            SubmitModal()
        )


# ============================================================
# MODAL RÉPONSE
# ============================================================

class ReplyModal(
    discord.ui.Modal,
    title="Répondre au gossip"
):

    def __init__(
        self,
        origin_message_id: int
    ):

        super().__init__()

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

            # =================================================
            # PUBLICATION
            # =================================================

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

            # =================================================
            # LOG
            # =================================================

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
                value=(
                    f"[Voir la réponse]("
                    f"{thread.jump_url})"
                ),
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

            log.info(
                "Réponse publiée | user=%s | anonymous=%s",
                interaction.user.id,
                anonymous
            )

        except Exception:

            log.exception(
                "Erreur lors de l'envoi d'une réponse"
            )

            try:

                await interaction.followup.send(
                    "Impossible d'envoyer ta réponse "
                    "pour le moment.",
                    ephemeral=True
                )

            except Exception:

                log.exception(
                    "Impossible d'envoyer le message d'erreur"
                )


# ============================================================
# BOUTONS DES LOGS
# ============================================================

class LogActionsView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Bloquer des confessions",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="gossip:ban_author"
    )
    async def ban_author(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        # ----------------------------------------------------
        # SÉCURITÉ
        # ----------------------------------------------------

        if not moderator(interaction):

            await interaction.response.send_message(
                "Tu n'as pas la permission d'utiliser "
                "ce bouton.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # RÉCUPÉRATION DE L'ID
        # ----------------------------------------------------

        if not interaction.message.embeds:

            await interaction.response.send_message(
                "Impossible de retrouver l'auteur.",
                ephemeral=True
            )

            return

        embed = interaction.message.embeds[0]

        user_id = None

        # On récupère l'ID directement depuis
        # le champ "ID Discord".

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
                "Impossible de récupérer l'ID Discord "
                "de cet utilisateur.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # ÉVITE DE BANNIR LE BOT
        # ----------------------------------------------------

        if bot.user and user_id == bot.user.id:

            await interaction.response.send_message(
                "Je ne peux pas me bloquer moi-même.",
                ephemeral=True
            )

            return

        # ----------------------------------------------------
        # BAN
        # ----------------------------------------------------

        already_banned = is_banned(
            user_id
        )

        ban_user(
            user_id
        )

        if already_banned:

            message = (
                f"L'utilisateur `{user_id}` est déjà "
                f"bloqué des confessions."
            )

        else:

            message = (
                f"L'utilisateur `{user_id}` est maintenant "
                f"bloqué des confessions."
            )

        await interaction.response.send_message(
            message,
            ephemeral=True
        )

        # ----------------------------------------------------
        # LOG DE MODÉRATION
        # ----------------------------------------------------

        try:

            _, log_channel = await get_channels()

            moderator_name = (
                f"{interaction.user} "
                f"(`{interaction.user.id}`)"
            )

            moderation_embed = dark_embed(
                "UTILISATEUR BLOQUÉ",
                f"**Utilisateur :** `{user_id}`\n"
                f"**Bloqué par :** {moderator_name}\n\n"
                f"Cette personne ne peut désormais plus "
                f"envoyer de confession ni de réponse.",
                RED_COLOR
            )

            await log_channel.send(
                embed=moderation_embed
            )

        except Exception:

            log.exception(
                "Impossible d'envoyer le log de bannissement"
            )

        log.info(
            "Utilisateur bloqué des confessions | "
            "user=%s | moderator=%s",
            user_id,
            interaction.user.id
        )


# ============================================================
# COMMANDE ADMIN — DÉBLOQUER
# ============================================================

@bot.tree.command(
    name="gossip_unban",
    description="Redonne accès aux confessions à un utilisateur."
)
@app_commands.describe(
    user_id="ID Discord de l'utilisateur à débloquer"
)
async def gossip_unban(
    interaction: discord.Interaction,
    user_id: str
):

    # --------------------------------------------------------
    # PERMISSIONS
    # --------------------------------------------------------

    if not moderator(interaction):

        await interaction.response.send_message(
            "Tu n'as pas la permission d'utiliser "
            "cette commande.",
            ephemeral=True
        )

        return

    try:

        target_id = int(user_id)

    except ValueError:

        await interaction.response.send_message(
            "L'ID Discord doit être un nombre.",
            ephemeral=True
        )

        return

    if not is_banned(target_id):

        await interaction.response.send_message(
            f"`{target_id}` n'est pas actuellement "
            f"bloqué des confessions.",
            ephemeral=True
        )

        return

    unban_user(
        target_id
    )

    await interaction.response.send_message(
        f"L'utilisateur `{target_id}` peut de nouveau "
        f"envoyer des confessions.",
        ephemeral=True
    )

    log.info(
        "Utilisateur débloqué | user=%s | moderator=%s",
        target_id,
        interaction.user.id
    )

    try:

        _, log_channel = await get_channels()

        embed = dark_embed(
            "UTILISATEUR DÉBLOQUÉ",
            f"**Utilisateur :** `{target_id}`\n"
            f"**Débloqué par :** "
            f"{interaction.user} "
            f"(`{interaction.user.id}`)",
            BURGUNDY_COLOR
        )

        await log_channel.send(
            embed=embed
        )

    except Exception:

        log.exception(
            "Impossible d'envoyer le log de déblocage"
        )


# ============================================================
# COMMANDE ADMIN — VÉRIFIER UN UTILISATEUR
# ============================================================

@bot.tree.command(
    name="gossip_check",
    description="Vérifie si un utilisateur est bloqué des confessions."
)
@app_commands.describe(
    user_id="ID Discord de l'utilisateur"
)
async def gossip_check(
    interaction: discord.Interaction,
    user_id: str
):

    if not moderator(interaction):

        await interaction.response.send_message(
            "Tu n'as pas la permission d'utiliser "
            "cette commande.",
            ephemeral=True
        )

        return

    try:

        target_id = int(user_id)

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
        "Gossip El HP est opérationnelle."
    )

    # --------------------------------------------------------
    # PANNEAU
    # --------------------------------------------------------

    if not bot.panel_sent:

        try:

            gossip_channel, _ = await get_channels()

            found = False

            async for message in gossip_channel.history(
                limit=50
            ):

                if (
                    message.author.id == bot.user.id
                    and message.embeds
                    and message.embeds[0].title
                    and "GOSSIP EL HP" in (
                        message.embeds[0].title.upper()
                    )
                ):

                    found = True

                    break

            if not found:

                await gossip_channel.send(
                    embed=embed_panel(),
                    view=PanelView()
                )

                log.info(
                    "Panneau Gossip envoyé."
                )

            else:

                log.info(
                    "Panneau déjà présent."
                )

            bot.panel_sent = True

        except Exception:

            log.exception(
                "Impossible d'initialiser le panneau."
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
        "Erreur Discord dans %s",
        event_method
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    if not TOKEN:

        raise SystemExit(
            "DISCORD_TOKEN est absent des variables "
            "d'environnement Railway."
        )

    if TOKEN == "REPLACE_ME":

        raise SystemExit(
            "Remplace REPLACE_ME par ton DISCORD_TOKEN."
        )

    log.info(
        "Démarrage de Gossip El HP..."
    )

    bot.run(TOKEN)