import sqlite3
from contextlib import closing
import logging
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
DB_NAME = os.getenv('DISCORD_BOT_DB_NAME')

class DatabaseHandler:
    def __init__(self, init=False):
        self.db_name = DB_NAME
        self.conn = None
        self.connect()
        if init:
            self._init_tables()

    def connect(self):
        """Establish a connection to the SQLite database."""
        try:
            if self.conn:
                self.conn.close()  # Ensure any existing connection is closed before reopening
            self.conn = sqlite3.connect(self.db_name)
            logging.info(f"Connected to the database: {self.db_name}")
        except sqlite3.Error as e:
            logging.error(f"Error connecting to database: {e}")
            raise

    def _init_tables(self):
        try:
            with self.conn:
                # Users table
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER NOT NULL UNIQUE,
                        username TEXT
                    )
                ''')
                
                # Habits table with tracking_channel_id
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS habits (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        tracking_channel_id INTEGER,
                        habit_name TEXT NOT NULL,
                        cue TEXT,
                        frequency TEXT,
                        intention TEXT,
                        commitment TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        FOREIGN KEY (tracking_channel_id) REFERENCES tracking_channels(channel_id)
                    )
                ''')

                # Tracking channels table with 8 user slots
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS tracking_channels (
                        channel_id INTEGER PRIMARY KEY,
                        user1_id INTEGER,
                        user2_id INTEGER,
                        user3_id INTEGER,
                        user4_id INTEGER,
                        user5_id INTEGER,
                        user6_id INTEGER,
                        user7_id INTEGER,
                        user8_id INTEGER,
                        FOREIGN KEY (user1_id) REFERENCES users(user_id),
                        FOREIGN KEY (user2_id) REFERENCES users(user_id),
                        FOREIGN KEY (user3_id) REFERENCES users(user_id),
                        FOREIGN KEY (user4_id) REFERENCES users(user_id),
                        FOREIGN KEY (user5_id) REFERENCES users(user_id),
                        FOREIGN KEY (user6_id) REFERENCES users(user_id),
                        FOREIGN KEY (user7_id) REFERENCES users(user_id),
                        FOREIGN KEY (user8_id) REFERENCES users(user_id)
                    )
                ''')

                # Tracking table
                self.conn.execute('''
                    CREATE TABLE IF NOT EXISTS tracking (
                        habit_id INTEGER NOT NULL,
                        week_key TEXT NOT NULL,
                        completed BOOLEAN NOT NULL,
                        FOREIGN KEY (habit_id) REFERENCES habits(id),
                        UNIQUE (habit_id, week_key)
                    )
                ''')
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")
            raise

    def add_user(self, user_id, username):
        if self.user_exists(user_id):
            print(f"User with ID {user_id} already exists.")
            return
        try:
            with self.conn:
                self.conn.execute('''
                    INSERT INTO users (user_id, username)
                    VALUES (?, ?)
                ''', (user_id, username))
            print(f"User {username} added successfully.")
        except sqlite3.Error as e:
            print(f"Error adding user: {e}")
            raise

    def user_exists(self, user_id):
        try:
            with closing(self.conn.cursor()) as cursor:
                cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            print(f"Error checking if user exists: {e}")
            raise


    def add_habit_with_data(self, habit_data, tracking_channel_id):
        try:
            # Extract data from the habit_data dictionary
            user_id = habit_data['metadata']['user_id']
            habit_name = habit_data['declaration']['habit']
            cue = habit_data['declaration']['cue']
            frequency = habit_data['declaration']['frequency']
            intention = habit_data['declaration']['intention']
            commitment = habit_data['declaration']['commitment']

            # Insert the habit data into the habits table
            with self.conn:
                self.conn.execute('''
                    INSERT INTO habits (user_id, tracking_channel_id, habit_name, cue, frequency, intention, commitment)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, tracking_channel_id, habit_name, cue, frequency, intention, commitment))
            
            logging.info(f"Habit '{habit_name}' added successfully for user {user_id} in channel {tracking_channel_id}.")
        except sqlite3.Error as e:
            logging.error(f"Error adding habit for user {user_id}: {e}")
            raise

    def add_user_to_tracking_channel(self, user_id, channel_id):
        try:
            with closing(self.conn.cursor()) as cursor:
                # Check if the channel exists
                cursor.execute('''
                    SELECT user1_id, user2_id, user3_id, user4_id, user5_id, user6_id, user7_id, user8_id 
                    FROM tracking_channels 
                    WHERE channel_id = ?
                ''', (channel_id,))
                
                channel = cursor.fetchone()
                
                if not channel:
                    # Channel does not exist, create it
                    logging.info(f"Channel {channel_id} does not exist. Creating new channel.")
                    with self.conn:
                        self.conn.execute('''
                            INSERT INTO tracking_channels (channel_id)
                            VALUES (?)
                        ''', (channel_id,))
                    
                    # Re-fetch the channel row after creation
                    cursor.execute('''
                        SELECT user1_id, user2_id, user3_id, user4_id, user5_id, user6_id, user7_id, user8_id 
                        FROM tracking_channels 
                        WHERE channel_id = ?
                    ''', (channel_id,))
                    channel = cursor.fetchone()

                # Find the first empty slot
                for i, user in enumerate(channel):
                    if user is None:
                        slot = i + 1
                        break
                else:
                    logging.error(f"Channel {channel_id} is already full.")
                    return False

                # Update the table with the new user in the first available slot
                column_name = f"user{slot}_id"
                with self.conn:
                    self.conn.execute(f'''
                        UPDATE tracking_channels
                        SET {column_name} = ?
                        WHERE channel_id = ?
                    ''', (user_id, channel_id))

                logging.info(f"User {user_id} added to channel {channel_id} in slot {slot}.")
                return True
        except sqlite3.Error as e:
            logging.error(f"Error adding user to channel {channel_id}: {e}")
            raise

    def get_habits_in_channel(self, channel_id):
        try:
            with closing(self.conn.cursor()) as cursor:
                # Perform a JOIN to retrieve all habits and corresponding user IDs for users in the given channel
                cursor.execute('''
                    SELECT h.user_id, h.id, h.habit_name
                    FROM habits h
                    JOIN tracking_channels tc ON h.user_id IN (
                        tc.user1_id, tc.user2_id, tc.user3_id, 
                        tc.user4_id, tc.user5_id, tc.user6_id, 
                        tc.user7_id, tc.user8_id
                    )
                    WHERE h.tracking_channel_id = tc.channel_id
                    AND tc.channel_id = ?
                ''', (channel_id,))
                
                habits = cursor.fetchall()
                
                return habits if habits else []
                    
        except sqlite3.Error as e:
            logging.error(f"Error retrieving habits for channel {channel_id}: {e}")
            raise


    def get_user_habits(self, user_id):
        try:
            with closing(self.conn.cursor()) as cursor:
                cursor.execute('''
                    SELECT * FROM habits WHERE user_id = ?
                ''', (user_id,))
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error retrieving habits for user {user_id}: {e}")
            raise

    def mark_habit_completed(self, habit_id, completed=True, current_week=True, week_key=None):
        try:
            if current_week:
                week_key = datetime.now().strftime("%Y-W%U")
            with self.conn:
                self.conn.execute('''
                    INSERT INTO tracking (habit_id, week_key, completed)
                    VALUES (?, ?, ?)
                ''', (habit_id, week_key, completed))
            logging.info(f"Habit with ID {habit_id} marked as completed for week {week_key}.")
        except sqlite3.IntegrityError:
            logging.warning(f"Habit with ID {habit_id} already has a record for week {week_key}. Update instead.")
        except sqlite3.Error as e:
            logging.error(f"Error marking habit as completed: {e}")
            raise

    def list_tables(self):
        try:
            with closing(self.conn.cursor()) as cursor:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error listing tables: {e}")
            raise

    def table_schema(self, table_name):
        try:
            with closing(self.conn.cursor()) as cursor:
                cursor.execute(f"PRAGMA table_info({table_name});")
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error retrieving schema for table {table_name}: {e}")
            raise

    def reset_db(self, second_check=False):
        if second_check:
            try:
                with closing(self.conn.cursor()) as cursor:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    for table_name in tables:
                        if table_name[0] != 'sqlite_sequence':  # Skip the special sqlite_sequence table
                            cursor.execute(f"DROP TABLE IF EXISTS {table_name[0]};")
                            logging.info(f"Dropped table {table_name[0]}")
                    self.conn.commit()
                    logging.info("Database reset completed.")
                # Optionally, reinitialize the tables after the reset
                self._init_tables()
            except sqlite3.Error as e:
                logging.error(f"Error resetting the database: {e}")
                raise


    def close(self):
        try:
            self.conn.close()
            logging.info(f"Disconnected from the database: {self.db_name}")
        except sqlite3.Error as e:
            print(f"Error closing the database connection: {e}")
            raise

# Example Usage
if __name__ == "__main__":
    db_handler = DatabaseHandler(init=True)

    db_handler.reset_db(second_check=False)
    # # Add a new user
    # db_handler.add_user("123456789", "JohnDoe")

    # # Attempt to add the same user again
    # db_handler.add_user("123456789", "JohnDoe")


    # # Get all habits for a user
    # habits = db_handler.get_user_habits("123456789")
    # print("User's Habits:", habits)

    # # Mark a habit as completed
    # week_key = datetime.now().strftime("%Y-W%U")
    # db_handler.mark_habit_completed(1, completed=True, current_week=True)

    # # List all tables
    # tables = db_handler.list_tables()
    # print("Tables in the database:", tables)

    # # Get the schema of a specific table
    # schema = db_handler.table_schema("users")
    # print("Users table schema:", schema)

    # Close the database connection
    db_handler.close()
