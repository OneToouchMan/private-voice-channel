import disnake
from disnake.ext import commands
from disnake.ui import Button, View
import asyncio 

intents = disnake.Intents.all()
intents.voice_states = True
bot = commands.Bot(command_prefix='?', intents=intents)

active_channels = {} #СЛОВАРЬ ГДЕ ХРАНЯТСЯ ДАННЫЕ


async def create_private_channel(member):
    guild = member.guild
    category_id = 1098093002456580096 #СЮДА ВСТАВЬ ID КАТЕГОРИИ
    category = disnake.utils.get(guild.categories, id=category_id)
    if category is None:
        category = await guild.create_category(name='Приватные каналы')

    overwrites = {
        guild.default_role: disnake.PermissionOverwrite(view_channel=False),
        disnake.utils.get(guild.roles, id=942355066055180308): disnake.PermissionOverwrite(
            read_messages=True,
            send_messages=True,
            connect=True,
            view_channel=True
        )
    }

    new_channel = await category.create_voice_channel(
        name=f'Канал {member.display_name}', 
        bitrate=96000, #ТУТ УКАЖИ НЕОБХОДИМЫЙ БИТРЕЙТ
        user_limit=0,
        overwrites=overwrites
    )

    await member.move_to(new_channel)
    active_channels[new_channel.id] = member.id
    await update_panel(new_channel, member.id)


async def select_member_callback(interaction: disnake.Interaction):
    member_id = interaction.data["values"][0]
    member = interaction.guild.get_member(int(member_id))
    if member:
        await member.move_to(None)
        await interaction.response.send_message(f"Участник {member.display_name} исключен из комнаты.", ephemeral=True)
    else:
        await interaction.response.send_message("Участник не найден.", ephemeral=True)


async def transfer_ownership_callback(interaction: disnake.Interaction):
    channel_id = interaction.channel.id
    user_id = interaction.author.id
    owner_id = active_channels.get(channel_id)

    if owner_id == user_id:
        members = [member for member in interaction.channel.members if not member.bot]
        options = [disnake.SelectOption(label=member.display_name, value=str(member.id)) for member in members]
        select_menu = disnake.ui.Select(placeholder="Выберите нового владельца", options=options, custom_id="select_new_owner")

        select_view = disnake.ui.View(timeout=300)
        select_view.add_item(select_menu)
        select_menu.callback = select_new_owner_callback

        embed = disnake.Embed(
            title="Передать права владения",
            description="Выберите нового владельца:",
            color=disnake.Color.blurple()
        )

        select_message = await interaction.response.send_message(
            embed=embed,
            view=select_view,
            ephemeral=True
        )

    else:
        await interaction.response.send_message("Только владелец временного голосового канала может передать права.", ephemeral=True)


async def select_new_owner_callback(interaction: disnake.Interaction):
    new_owner_id = interaction.data["values"][0]
    channel = interaction.channel
    current_owner_id = active_channels.get(channel.id)

    if current_owner_id == interaction.author.id:
        active_channels[channel.id] = int(new_owner_id)
        await interaction.response.send_message(f"Права владения переданы новому участнику.", ephemeral=True)
    else:
        await interaction.response.send_message("Только текущий владелец может передать права.", ephemeral=True)


async def update_panel(channel, owner_id):
    try:
        view = View(timeout=None)
        view.add_item(Button(label="", style=disnake.ButtonStyle.grey, custom_id="close_channel", emoji="<:lockk:1130815626701709312>"))
        view.add_item(Button(label="", style=disnake.ButtonStyle.grey, custom_id="open_channel", emoji="<:unlockk:1130815623379816550>"))
        view.add_item(Button(label="", style=disnake.ButtonStyle.grey, custom_id="hide_channel", emoji="<:invize:1130815630824702063>"))
        view.add_item(Button(label="", style=disnake.ButtonStyle.grey, custom_id="show_channel", emoji="<:noinvize:1130815628245209139>"))
        view.add_item(Button(label="", style=disnake.ButtonStyle.grey, custom_id="add_limit", emoji="<:members:1130815632418553926>"))    
        view.add_item(Button(label="", style=disnake.ButtonStyle.grey, custom_id="remove_limit", emoji="<:member:1130815636285706362>"))
        view.add_item(Button(label="", style=disnake.ButtonStyle.grey, custom_id="change_name", emoji="<:change:1130815640404512778>"))
        view.add_item(Button(label="", style=disnake.ButtonStyle.red, custom_id="kick_member", emoji="<:leave:1130815642061250591>"))
        view.add_item(Button(label="", style=disnake.ButtonStyle.grey, custom_id="transfer_ownership", emoji="<:owner:1131396039946018876> "))

        current_user_limit = channel.user_limit

        panel_message = await channel.send(embed=disnake.Embed(
            title='Управление комнатой',
            description='Измените настройки комнаты с помощью панели управления. \n <:lockk:1130815626701709312> - Закрыть канал \n <:unlockk:1130815623379816550> - Открыть канал \n <:invize:1130815630824702063> - Скрыть канал \n <:noinvize:1130815628245209139> - Открыть канал \n <:members:1130815632418553926> - Добавить 1 слот \n <:member:1130815636285706362> - Убрать 1 слот \n <:change:1130815640404512778> - Изменить название канала \n <:leave:1130815642061250591> - Исключить участника',
            color=disnake.Color.blue()
        ), view=view)

        while True:
            interaction = await bot.wait_for("button_click", timeout=None)
            if interaction.message.id != panel_message.id:
                continue

            user = interaction.user
            button = interaction.component.custom_id

            if user.id != owner_id:
                continue

            if button == "change_name" and user.id == owner_id:
                await channel.send("Введите новое название канала:")
                try:
                    await interaction.response.defer()
                    response = await bot.wait_for("message", check=lambda msg: msg.author == user, timeout=30)
                    new_name = response.content
                    await channel.edit(name=new_name)
                    await panel_message.edit(embed=disnake.Embed(title=f'Название канала изменено на "{new_name}"', color=disnake.Color.blurple()), view=view)
                except asyncio.TimeoutError:
                    await channel.send("Время ожидания истекло. Название канала не изменено.")

            elif button == "close_channel" and user.id == owner_id: 
                if user.voice and user.voice.channel == channel:
                    overwrites = {
                        channel.guild.default_role: disnake.PermissionOverwrite(connect=False, view_channel=False)
                    }
                    for member in channel.members:
                        if not member.bot:
                            overwrites[member] = disnake.PermissionOverwrite(connect=True, read_messages=True, send_messages=True)
                    await channel.edit(overwrites=overwrites)
                    await panel_message.edit(embed=disnake.Embed(title='Канал закрыт', color=disnake.Color.red()), view=view)
                    await interaction.response.defer()
                
            elif button == "open_channel" and user.id == owner_id:
                if user.voice and user.voice.channel == channel:
                    overwrites[channel.guild.default_role] = disnake.PermissionOverwrite(connect=True, view_channel=True)
                    await channel.edit(overwrites=overwrites)
                    await panel_message.edit(embed=disnake.Embed(title='Канал открыт', color=disnake.Color.green()), view=view)
                    await interaction.response.defer()

            elif button == "hide_channel" and user.id == owner_id:
                if user.voice and user.voice.channel == channel:
                    overwrites[channel.guild.default_role].update(view_channel=False)
                    await channel.edit(overwrites=overwrites)
                    await panel_message.edit(embed=disnake.Embed(title='Канал скрыт', color=disnake.Color.dark_gray()), view=view)
                    await interaction.response.defer()
            
            elif button == "show_channel" and user.id == owner_id:
                if user.voice and user.voice.channel == channel:
                    overwrites[channel.guild.default_role].update(view_channel=False)
                    await channel.edit(overwrites=overwrites)
                    await panel_message.edit(embed=disnake.Embed(title='Канал виден', color=disnake.Color.blurple()), view=view)
                    await interaction.response.defer()

            elif button == "add_limit" and user.id == owner_id:
                current_user_limit += 1
                await channel.edit(user_limit=current_user_limit)
                await panel_message.edit(embed=disnake.Embed(title=f'Лимит увеличен до {current_user_limit+0}', color=disnake.Color.blurple()), view=view)
                await interaction.response.defer()

            elif button == "remove_limit" and user.id == owner_id:
                current_user_limit = max(current_user_limit-1, 0)
                await channel.edit(user_limit=current_user_limit)
                await panel_message.edit(embed=disnake.Embed(title=f'Лимит уменьшен до {current_user_limit}', color=disnake.Color.red()), view=view)
                await interaction.response.defer()

            elif button == "kick_member" and user.id == owner_id:
                members = [member for member in channel.members if not member.bot]
                options = [
                    disnake.SelectOption(label=member.display_name, value=str(member.id)) for member in members
                ]
                select_menu = disnake.ui.Select(placeholder="Выберите участника", options=options, custom_id="select_member")

                select_view = disnake.ui.View(timeout=300)
                select_view.add_item(select_menu)
                select_menu.callback = select_member_callback

                embed = disnake.Embed(
                    title="Кого кикаем с голосового канала?",
                    color=disnake.Color.blurple()
                )

                select_message = await interaction.response.send_message(
                    embed=embed,
                    view=select_view,
                    ephemeral=True
                )

    except Exception as e:
        # Обработка ошибок здесь
        raise e

@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild
    if before.channel is not None and before.channel.id in active_channels:
        if len(before.channel.members) == 0:
            await before.channel.delete()
            active_channels.pop(before.channel.id)

    if after.channel is not None and after.channel.id == 1111038051662168137: #УКАЖИ ID КАНАЛА НА КОТОРЫЙ БУДУТ НАЖИМАТЬ
        await create_private_channel(member)

    
bot.run('') #УКАЖИ ТОКЕН СВОЕГО БОТА
