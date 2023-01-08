import discord

class CharacterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    options = [
        discord.SelectOption(label="Warlock", emoji="<:warlock:995298227723173898>", description="Add the warlock symbol to your name"),
        discord.SelectOption(label="Titan", emoji="<:titan:995298246509482007>", description="Add the titan symbol to your name"),
        discord.SelectOption(label="Hunter", emoji="<:hunter:995301239954882580>", description="Add the hunter symbol to your name"),
        discord.SelectOption(label="None", emoji="❌", description="Removes your character symbol"),
    ]

    @discord.ui.select(
        placeholder="Select your character",
        min_values=1,
        max_values=1,
        options=options,
        custom_id="character_select",
    )

    async def select_callback(self, select: discord.ui.Select, interaction: discord.Interaction):
        value = select.values[0]
        member = interaction.guild.get_member(interaction.user.id)
        if value == "None":
            for role in member.roles:
                if role.name in ["Warlock", "Titan", "Hunter"]:
                    await member.remove_roles(role)
            await interaction.response.send_message("Your character symbol was removed", ephemeral=True, delete_after=5)
        else:
            new_role = discord.utils.get(interaction.guild.roles, name=select.values[0])
            for role in member.roles:
                if role.name in ["Warlock", "Titan", "Hunter"]:
                    await member.remove_roles(role)
            await member.add_roles(new_role)
            await interaction.response.send_message(f"You have chosen the {select.values[0]} symbol", ephemeral=True, delete_after=5)
        await interaction.message.edit(content="", view=self)
