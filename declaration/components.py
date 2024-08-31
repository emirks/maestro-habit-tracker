import discord
from datetime import datetime
from declaration.declaration_handler import DeclarationHandler  # Import the handler
import logging
import random

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DeclarationView(discord.ui.View):
    def __init__(self, handler: DeclarationHandler, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.handler = handler

        self.instructions_embed = self.create_instructions_embed()  # Create the embed during initialization
        self.full_form_embed = self.create_full_form_embed()
        logger.debug(f"DeclareView initialized with handler: %s", handler)

    async def disable_all_buttons(self):
        """Disable all buttons in the view."""
        for item in self.children:
            item.disabled = True

    def create_instructions_embed(self):
        """Create and return the embed for the Habit Check."""
        embed = discord.Embed(
            title="Habit Declaration",
            description=(
                "Before declaring your habit, please read the following:\n\n"
                "**Preliminary Info:**\n"
                "- Your habit should be specific and measurable.\n"
                "- Declare habits that you can commit to daily.\n\n"
                "**Example Declaration:**\n"
                "``I will meditate for 5 mins, when I wake up so that I can become a mindful person.``\n\n"
                "**Declaration Steps:**\n"
                "**1- Define your habit:** An atomic habit is a regular practice that is small and easy to do, and can make a remarkable difference in your life.\n"
                "``Meditate for 5 mins``\n\n"
                "**2- Get specific:** Setting an exact time and place means not waiting around for inspiration to strike. \n"
                "``When I wake up``\n\n"
                "**3- Ground it in an identity:** The ultimate form of motivation is when a habit becomes part of who you are.\n"
                "``A mindful person``\n"
            ),
            color=discord.Color.blue()
        )

        embed.set_thumbnail(url=self.get_random_image_url())  # Random pikachu image
        return embed
    
    def create_full_form_embed(self):
        """Create and return the embed for the Habit Check."""
        embed = discord.Embed(
        title="Full Habit Declaration Format",
        description=(
                "I will ``habit``, ``time/location`` so that I can become ``type of person I want to be``\n\n"
                "Please ensure that your habit declaration follows this structure."
            ),
            color=discord.Color.green()
        )

        return embed
    
    def get_random_image_url(self):
        """Select a random image URL."""
        from tracking import pokemon_urls
        return random.choice(pokemon_urls)
    
    @discord.ui.button(label="Start Declaration", style=discord.ButtonStyle.success)
    async def declare_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_id:
            logger.debug(f"'Start Declaration' button clicked by {interaction.user.name} (ID: {interaction.user.id})")
    
            await self.handler.send_declaration_modal(interaction)

            #await self.disable_all_buttons()
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)

class HabitDeclarationModal(discord.ui.Modal):
    def __init__(self, declaration_handler: DeclarationHandler, habit_id_given=None):
        super().__init__(title="Habit Declaration")
        self.habit_id_given = habit_id_given
        self.declaration_handler = declaration_handler
        logger.debug("HabitDeclarationModal initialized with handler: %s", declaration_handler)

        # Add the components (text inputs)
        # Add a description text input that summarizes the full declaration
        self.habit = discord.ui.TextInput(
            label="Habit",
            placeholder="What specific habit will you do? (e.g., meditate for 5 minutes)",
            style=discord.TextStyle.short
        )
        self.add_item(self.habit)
        logger.debug("Added TextInput for habit.")

        self.time_location = discord.ui.TextInput(
            label="Time/Location",
            placeholder="When and where will you perform this habit? (e.g., when I wake up, at home)",
            style=discord.TextStyle.short
        )
        self.add_item(self.time_location)
        logger.debug("Added TextInput for time/location.")

        self.identity = discord.ui.TextInput(
            label="Identity",
            placeholder="What type of person will this habit help you become? (e.g., a mindful person)",
            style=discord.TextStyle.short
        )
        self.add_item(self.identity)
        logger.debug("Added TextInput for identity.")

    async def on_submit(self, interaction: discord.Interaction):
        logger.debug("HabitDeclarationModal submitted by user: %s (ID: %s)", interaction.user.name, interaction.user.id)
        
        habit_data = {
            'metadata': {
                'user_id': str(interaction.user.id),
                'timestamp': datetime.now().isoformat(),
            },
            'declaration': {
                'habit': self.habit.value,
                'time_location': self.time_location.value,
                'identity': self.identity.value,
            },
        }
        logger.debug("Habit data collected: %s", habit_data)

        await self.declaration_handler.handle_habit_submission(interaction, habit_data, self.habit_id_given)
        logger.debug("Habit submission handled for user: %s", interaction.user.name)
