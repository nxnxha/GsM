import os
import json
import asyncio
from typing import Optional, List, Dict

import discord
from discord import app_commands
from discord.ext import commands

# ----------------------
# Environment variables
# ----------------------
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

# IDs: You can override via env vars or keep defaults from user's spec
GUILD_ID = int(os.getenv("GUILD_ID", "1382730341944397967"))
GOSSIP_CHANNEL_ID = int(os.getenv("GOSSIP_CHANNEL_ID", "1400520302416367796"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "1400520703874433146"))

# Optional icon for the embed author (recommended to set)
GOSSIP_AUTHOR_ICON = os.getenv("GOSSIP_AUTHOR_ICON", "https://i.imgur.com/1f7h3G9.png")  # placeholder, change if you want

# Data path to remember authorship for deletions
DATA_DIR = os.getenv("DATA_DIR", "data")
GOSSIPS_DB = os.path.join(DATA_DIR, "gossips.json")

# Color #9B6B43
BRAND_COLOR = discord.Color.from_rgb(0x9B, 0x6B, 0x43)

INTENTS = discord.Intents.default()
INTENTS.message_content = False
INTENTS.members = True
INTENTS.guilds = True

bot = commands.Bot(command_prefix="!", intents=INTENTS)

# ----------------------
# Persistent storage
# ----------------------
def load_db() -> Dict[str, dict]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(GOSSIPS_DB):
        with open(GOSSIPS_DB, "w", encoding="utf-8") as f:
            json.dump({"gossips": {}}, f, ensure_ascii=False, indent=2)
    with open(GOSSIPS_DB, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db: Dict[str, dict]) -> None:
    with open(GOSSIPS_DB, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

# gossip structure: { message_id: { "author_id": int, "content": str, "thread_id": Optional[int], "created_at": iso } }
def remember_gossip(message_id: int, author_id: int, content: str, thread_id: Optional[int]) -> None:
    db = load_db()
    db["gossips"][str(message_id)] = {
        "author_id": author_id,
        "content": content[:2000],
        "thread_id": thread_id,
    }
    save_db(db)

def user_gossips(author_id: int) -> List[tuple]:
    db = load_db()
    out = []
    for mid, payload in db.get("gossips", {}).items():
        if int(payload.get("author_id", 0)) == author_id:
            out.append((int(mid), payload))
    # newest first by message id order is fine (not guaranteed chronological). Keep as-is.
    return out[-25:]  # Discord selects max 25 options

def forget_gossip(message_id: int) -> None:
    db = load_db()
    db["gossips"].pop(str(message_id), None)
    save_db(db)

# ----------------------
# UI Components
# ----------------------
class ConfessionModal(discord.ui.Modal, title="Soumettre une confession"):
    def __init__(self):
        super().__init__(timeout=None)
        self.content = discord.ui.TextInput(
            label="Ton secret / confession",
            style=discord.TextStyle.paragraph,
            placeholder="Déverse ce que tu n’oses dire à personne...",
            required=True,
            max_length=1900,
        )
        self.add_item(self.content)

    async def on_submit(self, interaction: discord.Interaction):
        author = interaction.user
        guild = interaction.guild
        gossip_ch = guild.get_channel(GOSSIP_CHANNEL_ID) if guild else None

        if gossip_ch is None:
            await interaction.response.send_message(
                "Le salon de publication est introuvable. Vérifie GOSSIP_CHANNEL_ID.",
                ephemeral=True,
            )
            return

        # Build the public embed
        embed = discord.Embed(description=str(self.content), color=BRAND_COLOR)
        embed.set_author(name="Gossip Miri", icon_url=GOSSIP_AUTHOR_ICON)
        embed.set_footer(text="XOXO, Gossip Miri 💋")

        # Post in gossip channel
        msg = await gossip_ch.send(embed=embed, view=ConfessionPostedView())
        # Create auto-thread
        thread_name = (str(self.content)[:80] + "…") if len(self.content) > 80 else str(self.content)
        thread = await msg.create_thread(name=f"Gossip • {thread_name}")
        # First message in thread (prompt)
        await thread.send("💬 **Réponds à ce gossip ci-dessous** (anonyme possible via le bouton sous le message).")

        # Remember for deletion
        remember_gossip(msg.id, author.id, str(self.content), thread.id if thread else None)

        # Log (without mention)
        try:
            log_ch = guild.get_channel(LOG_CHANNEL_ID) if guild else None
            if log_ch:
                log_embed = discord.Embed(
                    title="Nouvelle confession",
                    description=str(self.content),
                    color=BRAND_COLOR,
                )
                log_embed.set_author(name=f"{author} (ID: {author.id})", icon_url=author.display_avatar.url)
                await log_ch.send(embed=log_embed)
        except Exception:
            pass

        await interaction.response.send_message("✅ Confession envoyée !", ephemeral=True)


class ReplyModal(discord.ui.Modal, title="Répondre au gossip"):
    def __init__(self, parent_message_id: int):
        super().__init__(timeout=None)
        self.parent_message_id = parent_message_id
        self.content = discord.ui.TextInput(
            label="Ta réponse",
            style=discord.TextStyle.paragraph,
            placeholder="Écris ta réponse ici...",
            required=True,
            max_length=1900,
        )
        self.anonymous = discord.ui.TextInput(
            label="Posté en anonyme ? (oui/non)",
            style=discord.TextStyle.short,
            required=False,
            max_length=5,
            placeholder="oui / non",
        )
        self.add_item(self.content)
        self.add_item(self.anonymous)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        try:
            parent_msg = await guild.get_channel(GOSSIP_CHANNEL_ID).fetch_message(self.parent_message_id)
        except Exception:
            await interaction.response.send_message("Ce gossip n'existe plus.", ephemeral=True)
            return

        # Get thread from DB
        db = load_db()
        payload = db.get("gossips", {}).get(str(self.parent_message_id))
        thread_id = payload.get("thread_id") if payload else None
        thread = None
        if thread_id:
            ch = guild.get_channel(int(thread_id))
            if isinstance(ch, discord.Thread):
                thread = ch

        # Build reply
        anon = (str(self.anonymous).strip().lower() == "oui")
        if anon:
            title = "Réponse d’un·e anonyme"
            author_name = "Anonyme"
            icon = GOSSIP_AUTHOR_ICON
        else:
            title = f"Réponse de {interaction.user.display_name}"
            author_name = str(interaction.user.display_name)
            icon = interaction.user.display_avatar.url

        reply_embed = discord.Embed(description=str(self.content), color=BRAND_COLOR)
        reply_embed.set_author(name=author_name, icon_url=icon)

        # Send to thread if present; otherwise as reply to parent
        if thread:
            await thread.send(embed=reply_embed)
        else:
            await parent_msg.reply(embed=reply_embed)

        await interaction.response.send_message("💌 Réponse envoyée.", ephemeral=True)


class ConfessionPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Soumettre une confession", style=discord.ButtonStyle.primary, emoji="🔐", custom_id="panel_confess")
    async def confess(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ConfessionModal())


class ConfessionPostedView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Répondre à ce gossip", style=discord.ButtonStyle.secondary, emoji="💭", custom_id="reply_gossip")
    async def reply(self, interaction: discord.Interaction, button: discord.ui.Button):
        parent_message = interaction.message
        if not parent_message or not parent_message.id:
            await interaction.response.send_message("Action impossible.", ephemeral=True)
            return
        await interaction.response.send_modal(ReplyModal(parent_message.id))

    @discord.ui.button(label="Soumettre un autre gossip", style=discord.ButtonStyle.primary, emoji="🔐", custom_id="confess_again")
    async def confess_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ConfessionModal())


# ----------------------
# Slash Commands
# ----------------------
@bot.event
async def on_ready():
    try:
        await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    except Exception as e:
        print("App command sync error:", e)
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Ready.")

@bot.tree.command(name="gossip_panel", description="Publier le panneau d'accueil des confessions.", guild=discord.Object(id=GUILD_ID))
@app_commands.checks.has_permissions(manage_guild=True)
async def gossip_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Gossip Miri",
        description=(
            "**Bienvenue dans l’Espace Gossip de Miri !**\n\n"
            "Ici, tu peux **soumettre une confession** et répondre dans le **thread dédié**.\n"
            "Les réponses peuvent être **anonymes**.\n\n"
            "⚠️ Réservé aux **18 ans et plus**.\n\n"
            "Clique ci-dessous pour commencer :"
        ),
        color=BRAND_COLOR,
    )
    embed.set_author(name="Gossip Miri", icon_url=GOSSIP_AUTHOR_ICON)
    embed.set_footer(text="XOXO, Gossip Miri 💋")

    await interaction.response.send_message(embed=embed, view=ConfessionPanelView())

@gossip_panel.error
async def gossip_panel_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("Tu n'as pas la permission d'utiliser cette commande.", ephemeral=True)
    else:
        await interaction.response.send_message("Erreur lors de la publication du panneau.", ephemeral=True)

class DeleteSelect(discord.ui.Select):
    def __init__(self, options: List[discord.SelectOption]):
        super().__init__(placeholder="Choisis le gossip à supprimer…", min_values=1, max_values=1, options=options, custom_id="delete_select")

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        message_id = int(value)
        guild = interaction.guild
        gossip_ch = guild.get_channel(GOSSIP_CHANNEL_ID) if guild else None
        if gossip_ch is None:
            await interaction.response.send_message("Salon introuvable.", ephemeral=True)
            return
        # Fetch message & verify ownership
        db = load_db()
        payload = db.get("gossips", {}).get(str(message_id))
        if not payload or int(payload.get("author_id")) != interaction.user.id:
            await interaction.response.send_message("Tu ne peux pas supprimer ce gossip.", ephemeral=True)
            return

        # Delete thread if exists
        try:
            thread_id = payload.get("thread_id")
            if thread_id:
                ch = guild.get_channel(int(thread_id))
                if isinstance(ch, discord.Thread):
                    await ch.delete()
        except Exception:
            pass

        # Delete message
        deleted = False
        try:
            msg = await gossip_ch.fetch_message(message_id)
            await msg.delete()
            deleted = True
        except Exception:
            pass

        if deleted:
            forget_gossip(message_id)
            # Log
            try:
                log = guild.get_channel(LOG_CHANNEL_ID)
                if log:
                    await log.send(f"🗑️ Gossip supprimé par {interaction.user} (ID {interaction.user.id}).")
            except Exception:
                pass
            await interaction.response.send_message("✅ Ton gossip a bien été supprimé.", ephemeral=True)
        else:
            await interaction.response.send_message("Impossible de supprimer ce gossip (déjà supprimé ?).", ephemeral=True)

class DeleteView(discord.ui.View):
    def __init__(self, options: List[discord.SelectOption]):
        super().__init__(timeout=120)
        self.add_item(DeleteSelect(options))

@bot.tree.command(name="deletegossip", description="Supprimer un de tes anciens gossips.", guild=discord.Object(id=GUILD_ID))
async def deletegossip(interaction: discord.Interaction):
    items = user_gossips(interaction.user.id)
    if not items:
        await interaction.response.send_message("Tu n'as aucun gossip enregistré.", ephemeral=True)
        return
    # Build select options
    options: List[discord.SelectOption] = []
    for mid, payload in items[-25:]:
        label = payload.get("content", "")[:80]
        if not label:
            label = f"Gossip {mid}"
        options.append(discord.SelectOption(label=label, value=str(mid)))
    await interaction.response.send_message("Sélectionne le gossip à supprimer :", view=DeleteView(options), ephemeral=True)

# ----------------------
# Run
# ----------------------
def main():
    missing = []
    if not TOKEN:
        missing.append("DISCORD_TOKEN")
    if missing:
        print("Missing environment variables:", ", ".join(missing))
        raise SystemExit(1)
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
