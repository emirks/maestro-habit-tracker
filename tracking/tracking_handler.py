import discord
from tracking.channel_management import TrackingChannelManager
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TrackingHandler:
    def __init__(self, guild: discord.Guild, habit_declaration_channel: str, habit_tracking_channels_prefix: str, habit_tracking_category_name: str, declaration_data_path: str):
        self.guild = guild
        self.habit_declaration_channel = habit_declaration_channel
        self.habit_tracking_channels_prefix = habit_tracking_channels_prefix
        self.declaration_data_path = declaration_data_path
        self.tracking_channel_manager = TrackingChannelManager(guild, habit_tracking_channels_prefix, habit_tracking_category_name)
        logger.debug(f"DeclarationHandler initialized with channels: {habit_declaration_channel}, prefix: {habit_tracking_channels_prefix} and data path: {declaration_data_path}")

    async def send_habit_check_to_tracking_channel(self, tracking_channel: discord.TextChannel):
        
