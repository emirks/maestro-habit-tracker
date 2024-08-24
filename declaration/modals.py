import discord
from datetime import datetime
from declaration.declaration_handler import DeclarationHandler  # Import the handler

class HabitDeclarationModal(discord.ui.Modal):
    def __init__(self, handler: DeclarationHandler):
        super().__init__(title="Habit Declaration")
        self.handler = handler

        # Add the components (text inputs)
        self.habit = discord.ui.TextInput(
            label="Habit",
            placeholder="Describe the small, specific habit you're committing to",
            style=discord.TextStyle.short
        )
        self.add_item(self.habit)

        self.cue = discord.ui.TextInput(
            label="Cue",
            placeholder="What will trigger this habit? (e.g., time, place, preceding action)",
            style=discord.TextStyle.short
        )
        self.add_item(self.cue)

        self.frequency = discord.ui.TextInput(
            label="Frequency",
            placeholder="How often will this habit occur? (e.g., Daily, Weekly)",
            style=discord.TextStyle.short
        )
        self.add_item(self.frequency)

        self.intention = discord.ui.TextInput(
            label="Implementation Intention",
            placeholder="When [cue], I will [routine].",
            style=discord.TextStyle.short
        )
        self.add_item(self.intention)

        self.commitment = discord.ui.TextInput(
            label="Commitment",
            placeholder="Why this habit matters to you and how it aligns with your goals",
            style=discord.TextStyle.long
        )
        self.add_item(self.commitment)

    async def on_submit(self, interaction: discord.Interaction):
        habit_data = {
            'metadata': {
                'user_id': str(interaction.user.id),
                'timestamp': datetime.now().isoformat(),
            },
            'declaration': {
                'habit': self.habit.value,
                'cue': self.cue.value,
                'frequency': self.frequency.value,
                'intention': self.intention.value,
                'commitment': self.commitment.value,
            },
        }
        await self.handler.handle_habit_submission(interaction, habit_data)
