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
                        time_location TEXT,
                        identity TEXT,
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
                        streak INTEGER DEFAULT 0,
                        FOREIGN KEY (habit_id) REFERENCES habits(id),
                        UNIQUE (habit_id, week_key)
                    )
                ''')
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")
            raise

    #########################
    ### INSERTION METHODS ###
    #########################
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


    def add_habit_with_data(self, habit_data, tracking_channel_id, habit_id=None):
        try:
            # Extract data from the habit_data dictionary
            user_id = habit_data['metadata']['user_id']
            habit_name = habit_data['declaration']['habit']
            time_location = habit_data['declaration']['time_location']
            identity = habit_data['declaration']['identity']

            # If habit id is given, update the data
            if habit_id:
                 with self.conn:
                    self.conn.execute('''
                        UPDATE habits
                        SET user_id = ?, tracking_channel_id = ?, habit_name = ?, time_location = ?, identity = ?
                        WHERE id = ?
                    ''', (user_id, tracking_channel_id, habit_name, time_location, identity, habit_id))
                
                    logging.info(f"Habit ID {habit_id} updated successfully with new data.")
                    
                    return

            # Insert the habit data into the habits table
            with self.conn:
                self.conn.execute('''
                    INSERT INTO habits (user_id, tracking_channel_id, habit_name, time_location, identity)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, tracking_channel_id, habit_name, time_location, identity))
            
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
        
    def mark_habit_completed(self, habit_id, completed, current_week=True, week_key=None):
        try:
            week_key = self._get_week_key(current_week, week_key) if week_key else week_key
            logging.debug(f"Marking habit as completed: habit_id={habit_id}, completed={completed}, week_key={week_key}")

            with self.conn:
                with closing(self.conn.cursor()) as cursor:
                    last_streak_record = self._get_last_streak_record(cursor, habit_id)

                    new_streak = self._calculate_new_streak(completed, last_streak_record, week_key)
                    self._insert_or_update_tracking(cursor, habit_id, week_key, completed, new_streak)

        except sqlite3.IntegrityError:
            logging.warning(f"Habit with ID {habit_id} already has a record for week {week_key}.")
        except sqlite3.Error as e:
            logging.error(f"Error marking habit as completed: {e}")
            raise

    def _get_week_key(self, current_week, week_key):
        if not week_key and current_week:
            week_key = datetime.now().strftime("%Y-W%U")
        return week_key

    def _get_last_streak_record(self, cursor, habit_id):
        cursor.execute('''
            SELECT week_key, streak 
            FROM tracking 
            WHERE habit_id = ? 
            ORDER BY week_key DESC 
            LIMIT 1
        ''', (habit_id,))
        last_streak_record = cursor.fetchone()
        if last_streak_record:
            logging.debug(f"Last streak record found: last_week_key={last_streak_record[0]}, last_streak={last_streak_record[1]}")
        return last_streak_record

    def _calculate_new_streak(self, completed, last_streak_record, week_key):
        if completed:
            # If habit is completed and last streak record found
            if last_streak_record:
                last_week_key, last_streak = last_streak_record
                
                # If the last streak week is not passed, streak continues unchanged
                if last_week_key == week_key:
                    logging.debug(f"Same week, streak continues unchanged: new_streak={last_streak}")
                    return last_streak  
                
                # Last week matches the expected previous week, streak continues
                elif last_week_key == self.get_previous_week_key(week_key):
                    new_streak = last_streak + 1  
                    logging.debug(f"Last week matches expected previous week, streak incremented: new_streak={new_streak}")
                    return new_streak
                
                # In any other case of completion, start a new streak as 1
                else:
                    logging.debug(f"Streak reset: new_streak=1")
                    return 1  # Streak reset
            
            # If habit is completed but last streak record is not found
            else:
                logging.debug(f"Streak reset: new_streak=1")
                return 1  # Streak reset
        
        # If habit is not completed
        else:
            logging.debug(f"Not completed, resetting streak: new_streak=0")
            return 0
        
        

    def _insert_or_update_tracking(self, cursor, habit_id, week_key, completed, new_streak):
        cursor.execute('''
            INSERT INTO tracking (habit_id, week_key, completed, streak)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(habit_id, week_key) DO UPDATE SET completed=excluded.completed, streak=excluded.streak
        ''', (habit_id, week_key, completed, new_streak))
        logging.info(f"Habit with ID {habit_id} marked as completed for week {week_key} with streak {new_streak}.")



    ###################
    ### GET METHODS ###
    ###################
    def get_habit_data(self, habit_id):
        """
        Retrieve habit data from the database based on the habit ID.
        
        :param habit_id: The ID of the habit to retrieve.
        :return: A dictionary containing the habit data or None if the habit is not found.
        """
        try:
            with closing(self.conn.cursor()) as cursor:
                cursor.execute('''
                    SELECT 
                        h.id, 
                        h.user_id, 
                        h.tracking_channel_id, 
                        h.habit_name, 
                        h.time_location, 
                        h.identity,
                        u.username
                    FROM habits h
                    JOIN users u ON h.user_id = u.user_id
                    WHERE h.id = ?
                ''', (habit_id,))
                
                habit = cursor.fetchone()
                
                if habit:
                    habit_data = {
                        'habit_id': habit[0],
                        'user_id': habit[1],
                        'tracking_channel_id': habit[2],
                        'habit_name': habit[3],
                        'time_location': habit[4],
                        'identity': habit[5],
                        'username': habit[6]
                    }
                    return habit_data
                else:
                    logging.info(f"No habit found with ID {habit_id}.")
                    return None
        except sqlite3.Error as e:
            logging.error(f"Error retrieving habit data for habit ID {habit_id}: {e}")
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
    
    def get_previous_week_key(self, current_week_key):
        """
        Get the previous week key in the format 'YYYY-Www'.
        
        :param current_week_key: The current week key.
        :return: The previous week key.
        """
        year, week = map(int, current_week_key.split('-W'))
        logging.debug(f"Calculating previous week key from: current_week_key={current_week_key}")
        
        if week > 1:
            previous_week_key = f"{year}-W{week-1:02d}"
        else:
            # Handle the case where the week is 1, and we need to go back to the last week of the previous year
            previous_year = year - 1
            previous_week = datetime.strptime(f"{previous_year}-12-28", "%Y-%m-%d").isocalendar()[1]
            previous_week_key = f"{previous_year}-W{previous_week:02d}"
        
        logging.debug(f"Previous week key calculated: previous_week_key={previous_week_key}")
        return previous_week_key

    def get_current_streak(self, habit_id):
        """
        Retrieve the current streak for the given habit ID.
        
        :param habit_id: The ID of the habit.
        :return: The current streak value.
        """
        try:
            with closing(self.conn.cursor()) as cursor:
                cursor.execute('''
                    SELECT streak 
                    FROM tracking 
                    WHERE habit_id = ? 
                    ORDER BY week_key DESC 
                    LIMIT 1
                ''', (habit_id,))
                streak_record = cursor.fetchone()
                return streak_record[0] if streak_record else 0
        except sqlite3.Error as e:
            logging.error(f"Error retrieving current streak for habit ID {habit_id}: {e}")
            raise

    ###########################
    ### MAINTAINING METHODS ###
    ###########################
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
