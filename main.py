# -*- coding: utf-8 -*-
# Gossip Miri — Ultra Chic + Banlist (sans anti-spam, panneau auto)
# Python / discord.py v2.x — prêt pour Railway

import os, json, logging, datetime as dt
import discord
from discord import app_commands
from discord.ext import commands

# ================== CONFIG (Railway ENV) ==================
TOKEN             = os.getenv("DISCORD_TOKEN", "REPLACE_ME")
GUILD_ID          = int(os.getenv("GUILD_ID", "1382730341944397967"))
GOSSIP_CHANNEL_ID = int(os.getenv("GOSSIP_CHANNEL_ID", "1400520302416367796"))
LOG_CHANNEL_ID    = int(os.getenv("LOG_CHANNEL_ID", "1400520703874433146"))

AUTHOR_NAME       = os.getenv("AUTHOR_NAME", "Gossip Miri")
AUTHOR_ICON_URL   = os.getenv("AUTHOR_ICON_URL", "https://i.imgur.com/8Qn8M0d.png")
THEME_COLOR_HEX   = os.getenv("THEME_COLOR_HEX", "0x603A30")  # couleur moka
THEME_COLOR       = int(THEME_COLOR_HEX, 16)

PANEL_BANNER_URL  = os.getenv("PANEL_BANNER_URL", "")
PIN_MESSAGE       = os.getenv("PIN_PUBLISHED_MESSAGE", "false").lower() == "true"

BANLIST_FILE      = os.getenv("BANLIST_FILE", "gossip_banlist.json")

# ================== LOGGING ==================
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("gossip-miri")

# ================== BANLIST persistante ==================
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

# ================== BOT ==================
intents = discord.Intents.default()
intents.members = True

class MiriBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.synced = False

    async def setup_hook(self):
        self.add_view(PanelView())
        self.add_view(GossipActionsView())
        gobj = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=gobj)
        if not self.synced:
            await self.tree.sync(guild=gobj)
            self.synced = True

bot = MiriBot()

# ================== HELPERS ==================
SEPARATOR = "━━━━━━━━━━━━━━━━━━━━━━━━"

def chic_embed(title: str | None = None, description: str | None = None) -> discord.Embed:
    emb = discord.Embed(
        title=title or "Gossip Miri",
        description=description or "",
        color=THEME_COLOR,
        timestamp=dt.datetime.utcnow()
    )
    emb.set_author(name=AUTHOR_NAME, icon_url=AUTHOR_ICON_URL)
    emb.set_footer(text="XOXO, Gossip Miri 💋")
    return emb

def fancy_panel_embed() -> discord.Embed:
    desc = (
        f"**Bienvenue dans l’Espace _Gossip_ de {AUTHOR_NAME}!**\n"
        f"{SEPARATOR}\n"
        "• **Confesse** une histoire croustillante (_anonyme possible_).\n"
        "• Un **thread** s’ouvre sous chaque post pour les réponses.\n"
        "• Reste **classe** : pas de dox, pas d’insultes ciblées, pas d’infos perso.\n\n"
        "_Clique ci-dessous pour commencer._\n\n"
        "XOXO, Gossip Miri 💋"
    )
    emb = chic_embed("Gossip Miri — Salon des confidences", desc)
    if PANEL_BANNER_URL:
        emb.set_image(url=PANEL_BANNER_URL)
    return emb

async def get_channels():
    guild = bot.get_guild(GUILD_ID) or await bot.fetch_guild(GUILD_ID)
    gossip_ch = guild.get_channel(GOSSIP_CHANNEL_ID) or await bot.fetch_channel(GOSSIP_CHANNEL_ID)
    log_ch    = guild.get_channel(LOG_CHANNEL_ID)    or await bot.fetch_channel(LOG_CHANNEL_ID)
    return gossip_ch, log_ch

def sanitize(text: str, limit: int = 1800) -> str:
    return text.strip()[:limit]

def is_banned(user_id: int) -> bool:
    return user_id in BANNED_USERS

# ================== VIEWS & MODALS ==================
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Soumettre une confession",
        style=discord.ButtonStyle.primary,
        emoji="🔐",
        custom_id="gossip:open"
    )
    async def open_modal(self, interaction: discord.Interaction, _):
        if is_banned(interaction.user.id):
            await interaction.response.send_message("🚫 Tu es banni(e) des confessions.", ephemeral=True)
            return
        await interaction.response.send_modal(SubmitModal())

class GossipActionsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Répondre à ce gossip",
        style=discord.ButtonStyle.secondary,
        emoji="💭",
        custom_id="gossip:reply"
    )
    async def reply(self, interaction: discord.Interaction, _):
        if is_banned(interaction.user.id):
            await interaction.response.send_message("🚫 Tu es banni(e) des confessions.", ephemeral=True)
            return
        await interaction.response.send_modal(ReplyModal(origin_message_id=interaction.message.id))

    @discord.ui.button(
        label="Soumettre un autre gossip",
        style=discord.ButtonStyle.primary,
        emoji="🔐",
        custom_id="gossip:again"
    )
    async def again(self, interaction: discord.Interaction, _):
        if is_banned(interaction.user.id):
            await interaction.response.send_message("🚫 Tu es banni(e) des confessions.", ephemeral=True)
            return
        await interaction.response.send_modal(SubmitModal())

class SubmitModal(discord.ui.Modal, title="✨ Nouvelle confidence"):
    content = discord.ui.TextInput(
        label="Ton gossip (reste classe)",
        style=discord.TextStyle.paragraph,
        max_length=1800,
        placeholder="Un secret, une rumeur, un tea…",
        required=True
    )
    anonymous = discord.ui.TextInput(
        label="Publier en anonyme ? (oui/non)",
        style=discord.TextStyle.short,
        max_length=5,
        default="oui",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        if is_banned(interaction.user.id):
            await interaction.response.send_message("🚫 Tu es banni(e) des confessions.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            gossip_ch, log_ch = await get_channels()
            text = sanitize(str(self.content))
            anon = str(self.anonymous).lower().strip() in ("oui","o","yes","y","true","1")

            public = await gossip_ch.send(embed=chic_embed("Confidence", text), view=GossipActionsView())
            if PIN_MESSAGE:
                try: await public.pin(reason="Gossip Miri — épinglé")
                except: pass

            thread = public.thread or await public.create_thread(
                name=f"💬 Réponses — {public.id}",
                auto_archive_duration=1440
            )

            le = chic_embed(
                "🗂️ Nouveau gossip",
                f"**Auteur :** {interaction.user} (`{interaction.user.id}`)\n"
                f"**Anonyme :** {'Oui' if anon else 'Non'}\n"
                f"**Contenu :**\n{text}\n\n"
                f"[Aller au message]({public.jump_url})"
            )
            if interaction.user.display_avatar:
                le.set_thumbnail(url=interaction.user.display_avatar.url)
            await log_ch.send(embed=le)

            await interaction.followup.send("✅ **C’est publié !** Un thread a été créé pour les réponses.", ephemeral=True)
            if not anon:
                await thread.send(f"**Note :** post par {interaction.user.mention} (non anonyme).", suppress_embeds=True)

        except Exception as e:
            log.exception("Submit error: %s", e)
            await interaction.followup.send("❌ Une erreur est survenue.", ephemeral=True)

class ReplyModal(discord.ui.Modal, title="💬 Répondre à ce gossip"):
    def __init__(self, origin_message_id: int):
        super().__init__()
        self.origin_message_id = origin_message_id
        self.reply = discord.ui.TextInput(
            label="Ta réponse",
            style=discord.TextStyle.paragraph,
            max_length=1700,
            placeholder="Reste classe et pertinent·e.",
            required=True
        )
        self.anonymous = discord.ui.TextInput(
            label="Anonyme ? (oui/non)",
            style=discord.TextStyle.short,
            max_length=5,
            default="oui",
            required=True
        )
        self.add_item(self.reply)
        self.add_item(self.anonymous)

    async def on_submit(self, interaction: discord.Interaction):
        if is_banned(interaction.user.id):
            await interaction.response.send_message("🚫 Tu es banni(e) des confessions.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            gossip_ch, log_ch = await get_channels()
            origin = await gossip_ch.fetch_message(self.origin_message_id)
            thread = origin.thread or await origin.create_thread(
                name=f"💬 Réponses — {origin.id}",
                auto_archive_duration=1440
            )

            text = sanitize(str(self.reply))
            anon = str(self.anonymous).lower().strip() in ("oui","o","yes","y","true","1")

            if anon:
                await thread.send(embed=chic_embed("Réponse (anonyme)", text))
            else:
                await thread.send(f"**{interaction.user.display_name} :**\n{text}")

            le = chic_embed(
                "🗂️ Nouvelle réponse",
                f"**Auteur :** {interaction.user} (`{interaction.user.id}`)\n"
                f"**Anonyme :** {'Oui' if anon else 'Non'}\n"
                f"**Contenu :**\n{text}\n\n"
                f"[Aller au thread]({thread.jump_url})"
            )
            if interaction.user.display_avatar:
                le.set_thumbnail(url=interaction.user.display_avatar.url)
            await log_ch.send(embed=le)

            await interaction.followup.send("✅ Réponse envoyée dans le thread.", ephemeral=True)

        except Exception as e:
            log.exception("Reply error: %s", e)
            await interaction.followup.send("❌ Impossible d’envoyer la réponse.", ephemeral=True)

# ================== SLASH COMMANDS ADMIN ==================
@bot.tree.command(description="(Admin) Bannir un membre des confessions.")
@app_commands.checks.has_permissions(manage_guild=True)
async def gossip_ban(interaction: discord.Interaction, user: discord.User, reason: str = "Aucune raison donnée"):
    BANNED_USERS.add(user.id); save_banlist(BANNED_USERS)
    _, log_ch = await get_channels()
    emb = chic_embed("🚫 Gossip Ban", f"**{user}** banni des confessions.\n**Raison :** {reason}")
    if user.display_avatar: emb.set_thumbnail(url=user.display_avatar.url)
    await log_ch.send(embed=emb)
    await interaction.response.send_message(f"✅ {user.mention} banni.", ephemeral=True)

@bot.tree.command(description="(Admin) Débannir un membre des confessions.")
@app_commands.checks.has_permissions(manage_guild=True)
async def gossip_unban(interaction: discord.Interaction, user: discord.User):
    if user.id in BANNED_USERS:
        BANNED_USERS.remove(user.id); save_banlist(BANNED_USERS)
        _, log_ch = await get_channels()
        await log_ch.send(embed=chic_embed("✅ Gossip Unban", f"**{user}** débanni."))
        await interaction.response.send_message(f"✅ {user.mention} débanni.", ephemeral=True)
    else:
        await interaction.response.send_message(f"ℹ️ {user.mention} n’était pas banni.", ephemeral=True)

@bot.tree.command(description="(Admin) Voir la banlist.")
@app_commands.checks.has_permissions(manage_guild=True)
async def gossip_banlist(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not BANNED_USERS:
        await interaction.followup.send("📭 Banlist vide.", ephemeral=True); return
    lines = [f"- <@{uid}>" for uid in BANNED_USERS]
    await interaction.followup.send("🚫 **Bannis :**\n" + "\n".join(lines), ephemeral=True)

# ================== AUTO PANEL AU DÉMARRAGE ==================
@bot.event
async def on_ready():
    log.info("Connecté comme %s (%s)", bot.user, bot.user.id)
    gossip_ch, _ = await get_channels()
    await gossip_ch.send(embed=fancy_panel_embed(), view=PanelView())
    log.info("✅ Panneau publié automatiquement dans #%s", gossip_ch.name)

# ================== START ==================
if __name__ == "__main__":
    if TOKEN == "REPLACE_ME":
        raise SystemExit("⚠️ Mets DISCORD_TOKEN dans Railway → Variables.")
    bot.run(TOKEN)
