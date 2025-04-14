from discord.ext import commands

from globals import TL_SHIFTER_CHANNEL
from locales import guild_locale, Locale
from logger import KuriLogger
from repository import *
from services import MainService

main_service = MainService()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

logger = KuriLogger()
l = Locale()


@bot.event
async def on_ready():
    await bot.wait_until_ready()
    logger.info(f'We have logged in as {bot.user}')
    for guild in bot.guilds:
        guild_locale[guild.id] = guild.preferred_locale.value.lower()
        await setup_channel(guild)


@bot.event
async def on_guild_join(guild):
    await setup_channel(guild)


async def setup_channel(guild):
    logger.info(f'Setup for guild {guild.id} - {guild.name}')
    await main_service.setup_guild_channel_message(guild=guild, tl_shifter_channel=TL_SHIFTER_CHANNEL)


@bot.event
async def on_message(message):
    # Early exit for bot messages
    if message.author == bot.user:
        return

    # Early exit for non-target channels
    if message.channel.id not in TL_SHIFTER_CHANNEL:
        await bot.process_commands(message)
        return

    content = message.content
    lines = content.split('\n', 1)  # Split only once if possible
    if not lines:
        await bot.process_commands(message)
        return

    # Process first line
    first_line, *rest = lines[0].split('\n')  # Handle potential multi-split
    first_segment = SPACE_PATTERN.split(first_line.strip(), 1)[0]
    second_str = NON_DIGIT.sub('', first_segment)

    if not second_str.isdigit():
        await bot.process_commands(message)
        return

    second = int(second_str)
    if second > 90:
        await bot.process_commands(message)
        return

    sec_reduction = 90 - second
    result_lines = [
        f"TL Shift for {second}s",
        "```powershell"
    ]

    # Process remaining lines
    for line in (lines[1].split('\n') if len(lines) > 1 else []):
        parts = SPACE_PATTERN.split(line.strip(), 1)
        if len(parts) < 2:
            continue

        time_str, desc = parts
        try:
            parsed_time = utils.time_to_seconds(time_str)
        except ValueError:
            continue

        result_time = parsed_time - sec_reduction
        if result_time <= 0:
            continue

        result_lines.append(f"{utils.format_time(result_time)}  {desc.strip()}")

    # Only send response if we have valid entries
    if len(result_lines) > 2:
        result_lines.append("```")
        await message.reply(NEW_LINE.join(result_lines))


# Slash Command or sc_
@bot.tree.command(name="install", description="This command will try to install all channel related to the bot functions")
async def sc_install(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if not interaction.user.guild_permissions.administrator:
        return await utils.send_message_medium(interaction, l.t(guild_id, "system.not_administrator", user=interaction.user.display_name))

    async def button_ok_callback(interact: discord.Interaction):
        await interact.response.defer(thinking=True, ephemeral=True)

        guild = interaction.guild
        setup = await main_service.install_bot_command(guild, TL_SHIFTER_CHANNEL)
        if not setup.is_success:
            await utils.send_followup_short(interaction=interact, content=f"{setup.error_messages}",
                                            ephemeral=True)
            return

        await utils.send_followup_short(interaction=interact, content=l.t(guild_id, "message.done_install"),
                                        ephemeral=True)

    view = utils.create_confirmation_message_view(guild_id=guild_id, yes_callback=button_ok_callback)

    await utils.send_message_medium(interaction=interaction,
                                    content=l.t(guild_id, "ui.prompts.install_confirmation"),
                                    view=view, ephemeral=True)



@bot.tree.command(name="uninstall", description="This command will try to uninstall all channel related to the bots and removing data from database")
async def sc_uninstall(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if not interaction.user.guild_permissions.administrator:
        return await utils.send_message_medium(interaction, l.t(guild_id, "system.not_administrator", user=interaction.user.display_name))

    async def button_ok_callback(interact: discord.Interaction):
        await interact.response.defer(thinking=True, ephemeral=True)
        guild = interaction.guild
        action = await main_service.uninstall_bot_command(guild, TL_SHIFTER_CHANNEL)
        if not action.is_success:
            await utils.send_followup_short(interaction=interact, content=f"{action.error_messages}", ephemeral=True)
            return

        # Delete Channel
        channels = action.result
        channels.sort(reverse=True)
        for channel_id in channels:
            channel = interact.guild.get_channel(channel_id)
            if channel:
                await channel.delete()

        await utils.send_followup_short(interaction=interact, content=l.t(guild_id, "message.done_uninstall"), ephemeral=True)

    view = utils.create_confirmation_message_view(guild_id=guild_id, yes_callback=button_ok_callback)

    await utils.send_message_medium(interaction=interaction,
                                  content=l.t(guild_id, "ui.prompts.uninstall_confirmation"),
                                  view=view, ephemeral=True)



@bot.tree.command(name="report", description="Report generator")
@app_commands.describe(year="Clan battle period year", month="Clan battle period month", day="Clan battle period day")
async def sc_report(interaction: discord.Interaction, year: int, month: int, day: int):
    guild_id = interaction.guild_id
    if not interaction.user.guild_permissions.administrator:
        return await utils.send_message_medium(interaction, l.t(guild_id, "system.not_administrator", user=interaction.user.display_name))

    await interaction.response.defer(thinking=True, ephemeral=True)

    msg_content = l.t(guild_id, "message.not_found", input="Report")
    report_result = await main_service.generate_report_text(guild_id=interaction.guild_id, year=year, month=month, day=day)
    if report_result.is_success:
        msg_content = report_result.result

    msg = await interaction.followup.send(content=msg_content, ephemeral=True)
    if msg:
        await msg.delete(delay=120)


@bot.tree.command(name="sync_user_role", description="Sync user with selected role for Clan Battle Report")
@app_commands.describe(role="Discord Role")
async def sc_sync_user_role(interaction: discord.Interaction, role: discord.Role):
    guild_id = interaction.guild_id
    if not interaction.user.guild_permissions.administrator:
        return await utils.send_message_medium(interaction, l.t(guild_id, "system.not_administrator", user=interaction.user.display_name))

    await interaction.response.defer(thinking=True, ephemeral=True)

    members = [GuildPlayer(
                            guild_id=interaction.guild_id,
                            player_id=member.id,
                            player_name=member.display_name
                         )
                for member in role.members]

    service_result = await main_service.sync_user_role(guild_id=guild_id, members=members)
    msg_content = l.t(guild_id, "message.done_sync")
    if not service_result.is_success:
            msg_content = service_result.error_messages

    await main_service.refresh_report_channel_message(interaction.guild)

    msg = await interaction.followup.send(content=msg_content, ephemeral=True)
    if msg:
        await msg.delete(delay=30)

@bot.tree.command(name="help", description="Show the help available from the topic")
@app_commands.describe(topic="Topic you want to check")
async def sc_help(interaction: discord.Interaction, topic: HelpTopic().get_keys()):
    guild_id = interaction.guild_id
    if not interaction.user.guild_permissions.administrator:
        return await utils.send_message_medium(interaction, l.t(guild_id, "system.not_administrator", user=interaction.user.display_name))

    content = HelpTopic.get_value(topic)

    await interaction.response.send_message(content=content, ephemeral=True, delete_after=60)


bot.run(config.DISCORD_TOKEN, log_handler=None)
