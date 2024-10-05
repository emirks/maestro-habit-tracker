import pytest
import logging
from unittest import mock  # Keep only mock import
from datetime import datetime, timedelta, timezone
from maestro_bot import check_habits, tracking_handler

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Define UTC+3 timezone (as per your bot's timezone)
utc_plus_3 = timezone(timedelta(hours=3))

@pytest.fixture
def mock_datetime():
    """Fixture to mock datetime.now()"""
    with mock.patch('maestro_bot.datetime') as mock_dt:
        yield mock_dt

@pytest.fixture
def mock_tracking_handler():
    """Fixture to mock tracking_handler with AsyncMock for async methods"""
    mock_th = mock.MagicMock()  # Use MagicMock for async methods
    mock_th.send_habit_check_to_all_tracking_channels = mock.AsyncMock()  # Use mock.AsyncMock here
    mock_th.end_habit_check_session = mock.AsyncMock()
    with mock.patch('maestro_bot.tracking_handler', mock_th):
        yield mock_th

# Test habit check triggers exactly at 12:00 on Saturday and ends at 23:59
@pytest.mark.asyncio
async def test_habit_check_every_minute_of_the_week(mock_datetime, mock_tracking_handler):
    # Simulate every minute of a week (7 days, 24 hours, 60 minutes)
    start_time = datetime(2024, 9, 29, 0, 0, 0, tzinfo=utc_plus_3)  # Start from Sunday, 00:00 UTC+3
    for day in range(7):  # 7 days
        for hour in range(24):  # 24 hours
            for minute in range(60):  # 60 minutes
                current_time = start_time + timedelta(days=day, hours=hour, minutes=minute)
                mock_datetime.now.return_value = current_time
                
                # Call the habit check function
                await check_habits()

                # Check that habit check is only triggered at 12:00 PM on Saturday
                if current_time.weekday() == 5 and current_time.hour == 12 and current_time.minute == 0:
                    mock_tracking_handler.send_habit_check_to_all_tracking_channels.assert_called_once()
                else:
                    mock_tracking_handler.send_habit_check_to_all_tracking_channels.assert_not_called()

                # Check that habit check session only ends at 23:59 on Saturday
                if current_time.weekday() == 5 and current_time.hour == 23 and current_time.minute == 59:
                    mock_tracking_handler.end_habit_check_session.assert_called_once()
                else:
                    mock_tracking_handler.end_habit_check_session.assert_not_called()

                # Reset the mocks for the next minute
                mock_tracking_handler.send_habit_check_to_all_tracking_channels.reset_mock()
                mock_tracking_handler.end_habit_check_session.reset_mock()
