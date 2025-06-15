import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from declaration.declaration_handler import DeclarationHandler

@pytest.fixture
def declaration_handler():
    db_handler_mock = MagicMock()
    tracking_channel_manager_mock = MagicMock()
    tracking_handler_mock = MagicMock()
    guild_mock = MagicMock()
    habit_declaration_channel = MagicMock()
    habit_declaration_channel.name = "habit-declaration"
    
    return DeclarationHandler(
        db_handler_mock,
        tracking_channel_manager_mock,
        tracking_handler_mock,
        guild_mock,
        habit_declaration_channel
    )

@pytest.mark.asyncio
async def test_handle_habit_submission_new_habit(declaration_handler):
    interaction = AsyncMock()
    interaction.user.mention = "@user"
    interaction.user.id = "123456789"
    habit_data = {
        "metadata": {"user_id": "123456789"},
        "declaration": {
            "habit_name": "Test Habit",
            "time_location": "daily",
            "identity": "healthy person"
        }
    }
    
    habit_tracking_channel = MagicMock()
    habit_tracking_channel.id = "987654321"
    habit_tracking_channel.mention = "#test-channel"
    habit_tracking_channel.name = "habit-tracking-test"
    
    declaration_handler.tracking_channel_manager.create_or_get_tracking_channel.return_value = habit_tracking_channel
    declaration_handler.tracking_channel_manager.assign_role_to_user_for_channel = AsyncMock()
    
    await declaration_handler.handle_habit_submission(interaction, habit_data)
    
    declaration_handler.db_handler.add_habit_with_data.assert_called_once_with(habit_data, "987654321")
    declaration_handler.db_handler.add_user_to_tracking_channel.assert_called_once_with("123456789", "987654321")
    interaction.response.send_message.assert_called_once()
    assert "Your habit has been declared" in interaction.response.send_message.call_args[0][0]

@pytest.mark.asyncio
async def test_handle_habit_submission_existing_habit(declaration_handler):
    interaction = AsyncMock()
    interaction.user.mention = "@user"
    interaction.user.id = "123456789"
    habit_data = {
        "metadata": {"user_id": "123456789"},
        "declaration": {
            "habit_name": "Test Habit",
            "time_location": "daily",
            "identity": "healthy person"
        }
    }
    habit_id = "existing_habit_id"
    
    predefined_tracking_channel = MagicMock()
    predefined_tracking_channel.id = "987654321"
    predefined_tracking_channel.mention = "#existing-channel"
    predefined_tracking_channel.name = "habit-tracking-existing"
    
    declaration_handler.tracking_channel_manager.assign_role_to_user_for_channel = AsyncMock()
    
    await declaration_handler.handle_habit_submission(interaction, habit_data, habit_id, predefined_tracking_channel)
    
    declaration_handler.db_handler.add_habit_with_data.assert_called_once_with(habit_data, "987654321")
    declaration_handler.db_handler.add_user_to_tracking_channel.assert_called_once_with("123456789", "987654321")
    interaction.response.send_message.assert_called_once()
    assert "Your habit has been declared" in interaction.response.send_message.call_args[0][0]

@pytest.mark.asyncio
async def test_handle_habit_submission_error(declaration_handler):
    interaction = AsyncMock()
    interaction.user.id = "123456789"
    habit_data = {
        "metadata": {"user_id": "123456789"},
        "declaration": {
            "habit_name": "Test Habit",
            "time_location": "daily",
            "identity": "healthy person"
        }
    }
    
    declaration_handler.db_handler.add_habit_with_data.side_effect = Exception("Database error")
    declaration_handler.tracking_channel_manager.create_or_get_tracking_channel.return_value = MagicMock()
    
    await declaration_handler.handle_habit_submission(interaction, habit_data)
    
    interaction.response.send_message.assert_called_once()
    assert "An error occurred" in interaction.response.send_message.call_args[0][0]