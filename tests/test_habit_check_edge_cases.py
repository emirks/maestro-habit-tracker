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

# Test right before and after 12:00 PM on Saturday
@pytest.mark.asyncio
async def test_habit_check_boundary(mock_datetime, mock_tracking_handler):
    # Set datetime to 11:59 AM on Saturday (should not trigger)
    mock_datetime.now.return_value = datetime(2024, 10, 5, 11, 59, 0, tzinfo=utc_plus_3)
    await check_habits()
    mock_tracking_handler.send_habit_check_to_all_tracking_channels.assert_not_called()

    # Set datetime to exactly 12:00 PM on Saturday (should trigger)
    mock_datetime.now.return_value = datetime(2024, 10, 5, 12, 0, 0, tzinfo=utc_plus_3)
    await check_habits()
    mock_tracking_handler.send_habit_check_to_all_tracking_channels.assert_called_once()
    mock_tracking_handler.send_habit_check_to_all_tracking_channels.reset_mock()

    # Set datetime to 12:01 PM on Saturday (should not trigger again)
    mock_datetime.now.return_value = datetime(2024, 10, 5, 12, 1, 0, tzinfo=utc_plus_3)
    await check_habits()
    mock_tracking_handler.send_habit_check_to_all_tracking_channels.assert_not_called()

# Test right before and after 23:59 PM on Saturday
@pytest.mark.asyncio
async def test_end_habit_check_boundary(mock_datetime, mock_tracking_handler):
    # Set datetime to 11:58 PM on Saturday (should not trigger end session)
    mock_datetime.now.return_value = datetime(2024, 10, 5, 23, 58, 0, tzinfo=utc_plus_3)
    await check_habits()
    mock_tracking_handler.end_habit_check_session.assert_not_called()

    # Set datetime to exactly 23:59 PM on Saturday (should trigger end session)
    mock_datetime.now.return_value = datetime(2024, 10, 5, 23, 59, 0, tzinfo=utc_plus_3)
    await check_habits()
    mock_tracking_handler.end_habit_check_session.assert_called_once()
    mock_tracking_handler.end_habit_check_session.reset_mock()

    # Set datetime to 12:00 AM on Sunday (should not trigger end session again)
    mock_datetime.now.return_value = datetime(2024, 10, 6, 0, 0, 0, tzinfo=utc_plus_3)
    await check_habits()
    mock_tracking_handler.end_habit_check_session.assert_not_called()

# Test non-Saturday check at 12:00 PM on a different day
@pytest.mark.asyncio
async def test_non_saturday_check(mock_datetime, mock_tracking_handler):
    # Set datetime to 12:00 PM on Friday (should not trigger)
    mock_datetime.now.return_value = datetime(2024, 10, 4, 12, 0, 0, tzinfo=utc_plus_3)
    await check_habits()
    mock_tracking_handler.send_habit_check_to_all_tracking_channels.assert_not_called()

    # Set datetime to 12:00 PM on Sunday (should not trigger)
    mock_datetime.now.return_value = datetime(2024, 10, 6, 12, 0, 0, tzinfo=utc_plus_3)
    await check_habits()
    mock_tracking_handler.send_habit_check_to_all_tracking_channels.assert_not_called()

# Test daylight saving time forward (losing an hour)
@pytest.mark.asyncio
async def test_daylight_saving_forward(mock_datetime, mock_tracking_handler):
    # Assuming daylight saving time skips from 2:00 AM to 3:00 AM on a specific Sunday
    # Set datetime to 1:59 AM on Sunday
    mock_datetime.now.return_value = datetime(2024, 3, 31, 1, 59, 0, tzinfo=utc_plus_3)
    await check_habits()
    mock_tracking_handler.send_habit_check_to_all_tracking_channels.assert_not_called()

    # Set datetime to 3:00 AM on Sunday (DST skip)
    mock_datetime.now.return_value = datetime(2024, 3, 31, 3, 0, 0, tzinfo=utc_plus_3)
    await check_habits()
    mock_tracking_handler.send_habit_check_to_all_tracking_channels.assert_not_called()

# Test daylight saving time backward (gaining an hour)
@pytest.mark.asyncio
async def test_daylight_saving_backward(mock_datetime, mock_tracking_handler):
    # Assuming daylight saving time falls back from 2:00 AM to 1:00 AM on a specific Sunday
    # Set datetime to 1:59 AM on Sunday
    mock_datetime.now.return_value = datetime(2024, 10, 27, 1, 59, 0, tzinfo=utc_plus_3)
    await check_habits()
    mock_tracking_handler.send_habit_check_to_all_tracking_channels.assert_not_called()

    # Set datetime to 1:00 AM after falling back (DST backward)
    mock_datetime.now.return_value = datetime(2024, 10, 27, 1, 0, 0, tzinfo=utc_plus_3)
    await check_habits()
    mock_tracking_handler.send_habit_check_to_all_tracking_channels.assert_not_called()

# Test leap year February 29th check
@pytest.mark.asyncio
async def test_leap_year_check(mock_datetime, mock_tracking_handler):
    # Set datetime to February 29th on a leap year (should not trigger unless it's Saturday)
    mock_datetime.now.return_value = datetime(2024, 2, 29, 12, 0, 0, tzinfo=utc_plus_3)  # Leap year, Friday
    await check_habits()
    mock_tracking_handler.send_habit_check_to_all_tracking_channels.assert_not_called()

    # Now test if it's Saturday, February 29th (hypothetical future leap year)
    mock_datetime.now.return_value = datetime(2020, 2, 29, 12, 0, 0, tzinfo=utc_plus_3)  # Leap year, Saturday
    await check_habits()
    mock_tracking_handler.send_habit_check_to_all_tracking_channels.assert_called_once()

