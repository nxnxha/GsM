# -*- coding: utf-8 -*-
# Gossip Miri — Version finale simplifiée & chic
# Python / discord.py 2.x — Railway env vars

import os, json, logging, datetime as dt
import discord
from discord import app_commands
from discord.ext import commands
import random

# --------- ENV (Railway) ----------
TOKEN             = os.getenv("DISCORD_TOKEN", "REPLACE_ME")
GUILD_ID          = int(os.getenv("GUILD_ID", "1382730341944397967"))
GOSSIP_CHANNEL_ID = int(os.getenv("GOSSIP_CHANNEL_ID", "1400520302416367796"))
LOG_CHANNEL_ID    = int(os.getenv("LOG_CHANNEL_ID", "1400520703874433146"))

AUTHOR_NAME       = os.getenv("AUTHOR_NAME", "Gossip Miri")
THEME_COLOR_HEX   = os.getenv("THEME_COLOR_HEX", "0x603A30")   # #603A30
THEME_COLOR       = int(THEME_COLOR_HEX, 16)

PANEL_BANNER_URL  = os.getenv("PANEL_BANNER_URL", "")
PIN_MESSAGE       = os.getenv("PIN_PUBLISHED_MESSAGE", "false").lower() == "true"
BANLIST_FILE      = os.getenv("BANLIST_FILE", "gossip_banlist.json")

# --------- LOG ----------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("gossip-miri")

# --------- Banlist persistante ----------
def load_banlist() -> set[int]:
    try:
        with open(BANLIST_FILE, "r", encoding="utf-8") as f:
            return set(int(x) for x in json.load(f))
    except FileNotFoundError:
        return set()
    except Exception as e:
        log.exception("Erreur lecture banlist: %s", e); return set()

def save_banlist(bset: set[int]):
    try:
        with open(BANLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(list(bset), f)
    except Exception as e:
        log.exception("Erreur écriture banlist: %s", e)

BANNED_USERS: set[int] = load_banlist()

# --------- Bot ----------
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

# --------- UI helpers ----------
def embed_panel() -> discord.Embed:
    emb = discord.Embed(
        title="Gossip Miri — Espace Gossip",
        description=(
            "Un secret ? Une rumeur ?\n"
            "Ici, tout se chuchote… partage le plus gros ragot.\n"
            "Clique et entre dans le jeu."
        ),
        color=THEME_COLOR,
        timestamp=dt.datetime.utcnow()
    )
    emb.set_author(name=AUTHOR_NAME)  # pas d’icône
    emb.set_footer(text="XOXO, Gossip Miri 💋")
    if PANEL_BANNER_URL:
        emb.set_image(url=PANEL_BANNER_URL)
    return emb

HOOKS = [
    "Quelqu’un a chuchoté…",
    "On m’a soufflé à l’oreille…",
    "Un murmure traverse Miri…",
    "Pssst… écoute ça 👀",
]

def embed_post(content: str, is_reply: bool = False) -> discord.Embed:
    hook = random.choice(HOOKS)
    desc = f"*{hook}*\n\n{content}"
    emb = discord.Embed(
        description=desc,
        color=THEME_COLOR,
        timestamp=dt.datetime.utcnow()
    )
    emb.set_author(name=AUTHOR_NAME)  # sans photo
    emb.set_footer(text="XOXO, Gossip Miri 💋")
    return emb

async def get_channels():
    guild = bot.get_guild(GUILD_ID) or await bot.fetch_guild(GUILD_ID)
    gossip_ch = guild.get_channel(GOSSIP_CHANNEL_ID) or await bot.fetch_channel(GOSSIP_CHANNEL_ID)
    log_ch    = guild.get_channel(LOG_CHANNEL_ID)    or await bot.fetch_channel(LOG_CHANNEL_ID)
    return gossip_ch, log_ch

def sanitize(text: str, limit: int = 1800) -> str:
    return text.strip()[:limit]

def is_banned(uid: int) -> bool:
    return uid in BANNED_USERS

# --------- Views / Modals ----------
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Soumettre un gossip",
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

class SubmitModal(discord.ui.Modal, title="✨ Nouveau gossip"):
    content = discord.ui.TextInput(
        label="Ton gossip (reste classe)",
        style=discord.TextStyle.paragraph,
        max_length=1800,
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
        gossip_ch, log_ch = await get_channels()
        text = sanitize(str(self.content))
        anon = str(self.anonymous).lower().strip() in ("oui","o","yes","y","true","1")

        public = await gossip_ch.send(embed=embed_post(text), view=GossipActionsView())
        if PIN_MESSAGE:
            try: await public.pin()
            except: pass

        thread = public.thread or await public.create_thread(
            name="💬 Réponses", auto_archive_duration=1440
        )

        log_embed = embed_post(
            f"**Auteur :** {interaction.user} (`{interaction.user.id}`)\n"
            f"**Anonyme :** {'Oui' if anon else 'Non'}\n"
            f"**Contenu :**\n{text}\n\n"
            f"[Aller au message]({public.jump_url})"
        )
        await log_ch.send(embed=log_embed)

        await interaction.followup.send("✅ Gossip publié !", ephemeral=True)
        if not anon:
            await thread.send(f"**Note :** post par {interaction.user.mention} (non anonyme).", suppress_embeds=True)

class ReplyModal(discord.ui.Modal, title="💬 Répondre à ce gossip"):
    def __init__(self, origin_message_id: int):
        super().__init__()
        self.origin_message_id = origin_message_id
        self.reply = discord.ui.TextInput(
            label="Ta réponse",
            style=discord.TextStyle.paragraph,
            max_length=1700,
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
        gossip_ch, log_ch = await get_channels()
        origin = await gossip_ch.fetch_message(self.origin_message_id)
        thread = origin.thread or await origin.create_thread(
            name="💬 Réponses", auto_archive_duration=1440
        )

        text = sanitize(str(self.reply))
        anon = str(self.anonymous).lower().strip() in ("oui","o","yes","y","true","1")

        if anon:
            await thread.send(embed=embed_post(text, is_reply=True))
        else:
            await thread.send(f"**{interaction.user.display_name} :**\n{text}")

        log_embed = embed_post(
            f"**Auteur :** {interaction.user} (`{interaction.user.id}`)\n"
            f"**Anonyme :** {'Oui' if anon else 'Non'}\n"
            f"**Contenu :**\n{text}\n\n"
            f"[Aller au thread]({thread.jump_url})",
            is_reply=True
        )
        await log_ch.send(embed=log_embed)

        await interaction.followup.send("✅ Réponse envoyée !", ephemeral=True)

# --------- SLASH ADMIN (ban/unban/list) ----------
@bot.tree.command(description="(Admin) Bannir un membre des confessions.")
@app_commands.checks.has_permissions(manage_guild=True)
async def gossip_ban(interaction: discord.Interaction, user: discord.User, reason: str = "Aucune raison donnée"):
    BANNED_USERS.add(user.id); save_banlist(BANNED_USERS)
    _, log_ch = await get_channels()
    emb = embed_post(f"**{user}** banni des confessions.\n**Raison :** {reason}")
    await log_ch.send(embed=emb)
    await interaction.response.send_message(f"✅ {user.mention} banni.", ephemeral=True)

@bot.tree.command(description="(Admin) Débannir un membre des confessions.")
@app_commands.checks.has_permissions(manage_guild=True)
async def gossip_unban(interaction: discord.Interaction, user: discord.User):
    if user.id in BANNED_USERS:
        BANNED_USERS.remove(user.id); save_banlist(BANNED_USERS)
        _, log_ch = await get_channels()
        await log_ch.send(embed=embed_post(f"**{user}** débanni."))
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

# --------- AUTO PANEL ----------
@bot.event
async def on_ready():
    log.info("Connecté comme %s (%s)", bot.user, bot.user.id)
    gossip_ch, _ = await get_channels()
    await gossip_ch.send(embed=embed_panel(), view=PanelView())
    log.info("✅ Panneau publié automatiquement dans #%s", gossip_ch.name)

# --------- START ----------
if __name__ == "__main__":
    if TOKEN == "REPLACE_ME":
        raise SystemExit("⚠️ Mets DISCORD_TOKEN dans Railway → Variables.")
    bot.run(TOKEN)
