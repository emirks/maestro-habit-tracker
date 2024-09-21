import discord
from datetime import datetime
from declaration.declaration_handler import DeclarationHandler  # Import the handler
from tracking.tracking_handler import TrackingHandler
import logging
import random
import asyncio

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
        logger.info(f"DeclareView initialized with handler: %s", handler)

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

        else:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)

class HabitDeclarationModal(discord.ui.Modal):
    def __init__(self, declaration_handler: DeclarationHandler):
        super().__init__(title="Habit Declaration")
        self.declaration_handler = declaration_handler
        self.submission_event = asyncio.Event()
        logger.debug("HabitDeclarationModal initialized with handler: %s", declaration_handler)

        # Add the components (text inputs)
        # Add a description text input that summarizes the full declaration
        self.habit = discord.ui.TextInput(
            label="I will ``habit``",
            placeholder="e.g., Meditate for 3 minutes, Read for 1 minutes",
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
        
        self.habit_data = {
            'metadata': {
                'user_id': str(interaction.user.id),
                'timestamp': datetime.now().isoformat(),
            },
            'declaration': {
                'habit_name': self.habit.value,
                'time_location': self.time_location.value,
                'identity': self.identity.value,
            },
        }
        logger.debug("Habit data collected: %s", self.habit_data)

        await self.declaration_handler.handle_habit_submission(interaction, self.habit_data)
        self.submission_event.set()
        logger.debug("Habit submission handled for user: %s", interaction.user.name)

    async def wait_for_submission(self):
        await self.submission_event.wait()
        return self.habit_data
    

class HabitEditModal(discord.ui.Modal):
    def __init__(self, declaration_handler: DeclarationHandler, habit_data: dict, tracking_channel: discord.TextChannel):
        super().__init__(title="Edit Habit")
        self.habit_data = habit_data
        self.tracking_channel = tracking_channel
        self.declaration_handler = declaration_handler
        self.submission_event = asyncio.Event()
        logger.debug("HabitEditModal initialized with handler: %s", declaration_handler)

        # Pre-populate the text inputs with the current habit data
        self.habit = discord.ui.TextInput(
            label="Habit",
            default=self.habit_data.get('habit_name', ''),
            placeholder="e.g., Meditate for 3 minutes, Read for 1 minute",
            style=discord.TextStyle.short
        )
        self.add_item(self.habit)
        logger.debug("Added TextInput for habit with pre-filled data.")

        self.time_location = discord.ui.TextInput(
            label="Time/Location",
            default=self.habit_data.get('time_location', ''),
            placeholder="When and where will you perform this habit? (e.g., when I wake up, at home)",
            style=discord.TextStyle.short
        )
        self.add_item(self.time_location)
        logger.debug("Added TextInput for time/location with pre-filled data.")

        self.identity = discord.ui.TextInput(
            label="Identity",
            default=self.habit_data.get('identity', ''),
            placeholder="What type of person will this habit help you become? (e.g., a mindful person)",
            style=discord.TextStyle.short
        )
        self.add_item(self.identity)
        logger.debug("Added TextInput for identity with pre-filled data.")

    async def on_submit(self, interaction: discord.Interaction):
        logger.debug("HabitEditModal submitted by user: %s (ID: %s)", interaction.user.name, interaction.user.id)

        self.updated_habit_data = {
            'metadata': {
                'user_id': str(interaction.user.id),
                'timestamp': datetime.now().isoformat(),
            },
            'declaration': {
                'habit_name': self.habit.value,
                'time_location': self.time_location.value,
                'identity': self.identity.value,
            },
        }
        logger.debug("Updated habit data collected: %s", self.updated_habit_data)

        await self.declaration_handler.handle_habit_submission(interaction, self.updated_habit_data, self.habit_data.get('habit_id'), predefined_tracking_channel=self.tracking_channel)
        self.submission_event.set()
        logger.debug("Habit edit submission handled for user: %s", interaction.user.name)

    async def wait_for_submission(self):
        await self.submission_event.wait()
        return self.updated_habit_data
    

class DetailedHabitCardView(discord.ui.View):
    def __init__(self, guild, tracking_handler: TrackingHandler, declaration_handler: DeclarationHandler, user):
        super().__init__(timeout=None)
        self.guild = guild
        self.tracking_handler = tracking_handler
        self.declaration_handler = declaration_handler
        self.user = user
        self.user_id = user.id

        self.tracking_handler.db_handler.connect()
        self.habit_ids = tracking_handler.db_handler.get_user_habit_ids(self.user_id)
        self.habits = tracking_handler.db_handler.get_user_habits(self.user_id)
        self.embeds = self.create_embed_for_all_habits()

        # Create edit buttons for each habit
        self.create_edit_buttons()
        self.tracking_handler.db_handler.close()

    def create_embed_for_all_habits(self):
        embeds = []
        for habit_id in self.habit_ids:
            habit_data = self.tracking_handler.db_handler.get_habit_data(habit_id)
            current_streak = self.tracking_handler.db_handler.get_current_streak(habit_id)
            tracking_channel_id = habit_data['tracking_channel_id']
            tracking_channel = self.guild.get_channel(tracking_channel_id)
            if tracking_channel:
                tracking_channel_name = self.guild.get_channel(tracking_channel_id).name
            else:
                logger.info(f"Tracking channel with id {tracking_channel_id} does not exist. ")
                continue

            embed = self.create_embed(habit_data, current_streak, tracking_channel_name)
            embeds.append(embed)
        
        return embeds
    
    def create_embed(self, habit_data, current_streak, tracking_channel_name):
        """Create and return the embed for the Habit Data."""
        embed = discord.Embed(
            title=f"{habit_data['habit_name']}",
            description=f"Habit Data",
            color=discord.Color.random()  # Use a random color for the embed
        )
        
        # Add habit details
        embed.add_field(name="Habit", value=habit_data['habit_name'], inline=True)
        embed.add_field(name="Streak", value=f"🔥 {current_streak} weeks", inline=True)
        embed.add_field(name="Time / Location", value=habit_data['time_location'], inline=False)
        
        # Motivation and Identity Reminder
        embed.add_field(name="Don't Forget Your Purpose!", value=f"You're {habit_data['habit_name'].lower()} to become {habit_data['identity'].lower()}.", inline=False)
        embed.add_field(name="Attached tracking channel", value=f"{tracking_channel_name.lower()}", inline=False)
        
        embed.set_thumbnail(url=self.get_random_image_url())  # Random image
        return embed 

    def create_edit_buttons(self):
        """Create an edit button for each habit."""
        for habit_id in self.habit_ids:
            button = discord.ui.Button(
                label="Edit Habit",
                style=discord.ButtonStyle.secondary
            )
            button.callback = self.generate_edit_button_callback(habit_id)
            self.add_item(button)

    def generate_edit_button_callback(self, habit_id):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id == self.user_id:
                self.tracking_handler.db_handler.connect()
                logger.debug(f"'Edit Habit' button clicked by {interaction.user.name} (ID: {interaction.user.id}) for habit ID: {habit_id}")
                habit_data = self.tracking_handler.db_handler.get_habit_data(habit_id)
                tracking_channel_id = habit_data['tracking_channel_id']
                # Wait for the declaration modal to be submitted and handled
                habit_data = await self.declaration_handler.send_habit_edit_modal(interaction, habit_data, tracking_channel_id)
                logger.debug(f"Habit data after modal submission: {habit_data}")
                
                # Update the habit check message with the new data
                await self.update_habit_check_message(interaction, habit_data, habit_id)
                self.tracking_handler.db_handler.close()
            else:
                await interaction.response.send_message("This button is not for you.", ephemeral=True)
        return callback

    async def update_habit_check_message(self, interaction, habit_data, habit_id):
        logger.debug(f"Initializing the new view for updated habit with habit_id: {habit_id}")
        
        # Create a new view for the updated habit
        new_view = discord.ui.View(timeout=None)
        
        # Add the "Edit Habit" button for this habit
        edit_button = discord.ui.Button(
            label="Edit Habit",
            style=discord.ButtonStyle.secondary
        )
        edit_button.callback = self.generate_edit_button_callback(habit_id)
        new_view.add_item(edit_button)

        # Generate the new embed with updated habit data
        self.tracking_handler.db_handler.connect()
        updated_habit_data = self.tracking_handler.db_handler.get_habit_data(habit_id)
        current_streak = self.tracking_handler.db_handler.get_current_streak(habit_id)
        tracking_channel_name = self.guild.get_channel(updated_habit_data['tracking_channel_id']).name
        new_embed = self.create_embed(updated_habit_data, current_streak, tracking_channel_name)
        self.tracking_handler.db_handler.close()

        # Send a new message with the updated embed and view
        await interaction.followup.send(
            embed=new_embed,
            view=new_view,
            ephemeral=True  # Ephemeral message so only the user can see it
        )
        
        logger.debug(f"New message sent with updated habit information for habit_id: {habit_id}")
    
    def get_random_image_url(self):
        """Select a random image URL."""
        from tracking import pokemon_urls, dragon_urls
        # Adding some variety to the images used, including from dragon_urls
        return random.choice(pokemon_urls)
    


class HabitCardView(discord.ui.View):
    def __init__(self, tracking_handler: TrackingHandler, declaration_handler: DeclarationHandler, user, habit_data, tracking_channel_name):
        super().__init__(timeout=None)
        self.declaration_handler = declaration_handler
        self.tracking_handler = tracking_handler
        self.habit_data = habit_data['declaration']
        self.tracking_channel_name = tracking_channel_name
        self.user = user

        self.embed = self.create_embed()  # Create the embed during initialization
        logger.debug(f"HabitCardView initialized")

    async def disable_all_buttons(self):
        """Disable all buttons in the view."""
        for item in self.children:
            item.disabled = True

    def create_embed(self):
        """Create and return the embed for the Habit Check."""
        embed = discord.Embed(
            title=f"Declaration Overview",
            description=f"{self.user.mention}",
            color=discord.Color.random()  # Use a random color for the embed
        )
        
        embed.add_field(name="Full Form", value=f"I will {self.habit_data['habit_name'].lower()}, {self.habit_data['time_location'].lower()} so that I can become {self.habit_data['identity'].lower()}", inline=False)

        # Add habit details
        embed.add_field(name="Habit", value=self.habit_data['habit_name'], inline=True)
        embed.add_field(name="Time / Location", value=self.habit_data['time_location'], inline=False)
        
        # Motivation and Identity Reminder
        embed.add_field(name="Don't Forget Your Purpose!", value=f"You're doing {self.habit_data['habit_name'].lower()} to become {self.habit_data['identity'].lower()}.", inline=False)
        embed.add_field(name="Attached tracking channel", value=f"{self.tracking_channel_name.lower()}", inline=False)
        
        embed.set_thumbnail(url=self.get_random_image_url())  # Random image
        return embed
    
    def get_random_image_url(self):
        """Select a random image URL."""
        from tracking import pokemon_urls
        # Adding some variety to the images used, including from dragon_urls
        return random.choice(pokemon_urls)
