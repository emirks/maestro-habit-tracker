import sqlite3
from contextlib import closing
import logging
logger = logging.getLogger(__name__)
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
DB_NAME = os.environ['DISCORD_BOT_DB_NAME']

class DatabaseHandler:
    def __init__(self, init=False, db_name=None):
        self.db_name = db_name if db_name else DB_NAME # Accept environment value if not forced
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
            logger.info(f"Connected to the database: {self.db_name}")
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database: {e}")
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


    def add_habit_with_data(self, habit_data, tracking_channel_id):
        try:
            # Extract data from the habit_data dictionary
            user_id = habit_data['metadata']['user_id']
            habit_name = habit_data['declaration']['habit_name']
            time_location = habit_data['declaration']['time_location']
            identity = habit_data['declaration']['identity']

            # Insert the habit data into the habits table
            with self.conn:
                self.conn.execute('''
                    INSERT INTO habits (user_id, tracking_channel_id, habit_name, time_location, identity)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, tracking_channel_id, habit_name, time_location, identity))
            
            logger.info(f"Habit '{habit_name}' added successfully for user {user_id} in channel {tracking_channel_id}.")
        except sqlite3.Error as e:
            logger.error(f"Error adding habit for user {user_id}: {e}")
            raise

    def update_habit_with_data(self, habit_data, tracking_channel_id, habit_id):
        try:
            # Extract data from the habit_data dictionary
            user_id = habit_data['metadata']['user_id']
            habit_name = habit_data['declaration']['habit_name']
            time_location = habit_data['declaration']['time_location']
            identity = habit_data['declaration']['identity']

            # If habit id is given, update the data
            
            with self.conn:
                self.conn.execute('''
                    UPDATE habits
                    SET user_id = ?, tracking_channel_id = ?, habit_name = ?, time_location = ?, identity = ?
                    WHERE id = ?
                ''', (user_id, tracking_channel_id, habit_name, time_location, identity, habit_id))
            
                logger.info(f"Habit ID {habit_id} updated successfully with new data.")
            
            
        except sqlite3.Error as e:
            logger.error(f"Error adding habit for user {user_id}: {e}")
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
                    logger.info(f"Channel {channel_id} does not exist. Creating new channel.")
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
                    logger.error(f"Channel {channel_id} is already full.")
                    return False

                # Update the table with the new user in the first available slot
                column_name = f"user{slot}_id"
                with self.conn:
                    self.conn.execute(f'''
                        UPDATE tracking_channels
                        SET {column_name} = ?
                        WHERE channel_id = ?
                    ''', (user_id, channel_id))

                logger.info(f"User {user_id} added to channel {channel_id} in slot {slot}.")
                return True
        except sqlite3.Error as e:
            logger.error(f"Error adding user to channel {channel_id}: {e}")
            raise
        
    def mark_habit_completed(self, habit_id, completed, current_week=True, week_key=None):
        try:
            week_key = self._get_week_key(current_week, week_key) if week_key else week_key
            logger.debug(f"Marking habit: habit_id={habit_id}, completed={completed}, week_key={week_key}")

            with self.conn:
                with closing(self.conn.cursor()) as cursor:
                    last_streak_record = self._get_last_streak_record(cursor, habit_id)

                    new_streak = self._calculate_new_streak(completed, last_streak_record, week_key)
                    self._insert_or_update_tracking(cursor, habit_id, week_key, completed, new_streak)

        except sqlite3.IntegrityError:
            logger.warning(f"Habit with ID {habit_id} already has a record for week {week_key}.")
        except sqlite3.Error as e:
            logger.error(f"Error marking habit as completed: {e}")
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
            logger.debug(f"Last streak record found: last_week_key={last_streak_record[0]}, last_streak={last_streak_record[1]}")
        return last_streak_record

    def _calculate_new_streak(self, completed, last_streak_record, week_key):
        if completed:
            # If habit is completed and last streak record found
            if last_streak_record:
                last_week_key, last_streak = last_streak_record
                
                # If the last streak week is not passed, streak continues unchanged
                if last_week_key == week_key:
                    logger.debug(f"Same week, streak continues unchanged: new_streak={last_streak}")
                    return last_streak  
                
                # Last week matches the expected previous week, streak continues
                elif last_week_key == self.get_previous_week_key(week_key):
                    new_streak = last_streak + 1  
                    logger.debug(f"Last week matches expected previous week, streak incremented: new_streak={new_streak}")
                    return new_streak
                
                # In any other case of completion, start a new streak as 1
                else:
                    logger.debug(f"Streak reset: new_streak=1")
                    return 1  # Streak reset
            
            # If habit is completed but last streak record is not found
            else:
                logger.debug(f"Streak reset: new_streak=1")
                return 1  # Streak reset
        
        # If habit is not completed
        else:
            logger.debug(f"Not completed, resetting streak: new_streak=0")
            return 0
        
        

    def _insert_or_update_tracking(self, cursor, habit_id, week_key, completed, new_streak):
        cursor.execute('''
            INSERT INTO tracking (habit_id, week_key, completed, streak)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(habit_id, week_key) DO UPDATE SET completed=excluded.completed, streak=excluded.streak
        ''', (habit_id, week_key, completed, new_streak))
        logger.info(f"Habit with ID {habit_id} marked as {completed} for week {week_key} with streak {new_streak}.")


    def remove_habit_by_id(self, habit_id):
        """
        Remove a habit and its associated tracking data from the database.
        Also, clear the user's slot in the tracking_channels table if applicable.

        :param habit_id: The ID of the habit to be removed.
        """
        try:
            with self.conn:
                # Retrieve the habit's data, specifically the user_id and tracking_channel_id
                cursor = self.conn.cursor()
                cursor.execute('''
                    SELECT user_id, tracking_channel_id
                    FROM habits
                    WHERE id = ?
                ''', (habit_id,))
                habit_data = cursor.fetchone()

                if not habit_data:
                    logger.error(f"No habit found with ID {habit_id}.")
                    return

                user_id, tracking_channel_id = habit_data

                # Remove the tracking data related to the habit
                self.conn.execute('''
                    DELETE FROM tracking
                    WHERE habit_id = ?
                ''', (habit_id,))

                # Remove the habit itself
                self.conn.execute('''
                    DELETE FROM habits
                    WHERE id = ?
                ''', (habit_id,))

                # Clear the user's slot in the tracking_channels table
                if tracking_channel_id:
                    cursor.execute(f'''
                        SELECT channel_id, user1_id, user2_id, user3_id, user4_id, user5_id, user6_id, user7_id, user8_id
                        FROM tracking_channels
                        WHERE channel_id = ?
                    ''', (tracking_channel_id,))
                    channel_data = cursor.fetchone()

                    if channel_data:
                        # Find the user's slot and set it to NULL
                        for i, user in enumerate(channel_data[1:], start=1):  # Skip channel_id
                            if user == user_id:
                                column_name = f"user{i}_id"
                                self.conn.execute(f'''
                                    UPDATE tracking_channels
                                    SET {column_name} = NULL
                                    WHERE channel_id = ?
                                ''', (tracking_channel_id,))
                                logger.info(f"Cleared user {user_id} from slot {i} in channel {tracking_channel_id}.")
                                break

                logger.info(f"Habit with ID {habit_id} and its tracking data have been successfully removed.")

        except sqlite3.Error as e:
            logger.error(f"Error removing habit with ID {habit_id}: {e}")
            raise

    def remove_all_dev_habits(self):
        """
        Remove all habits named 'dev' and their associated tracking data.
        Uses the remove_habit_by_id method to delete each habit and its related data.
        """
        logger.info(f"\nRemoving all the development purpose habit entries in the database")
        try:
            with closing(self.conn.cursor()) as cursor:
                # Fetch all habits named 'dev'
                cursor.execute('''
                    SELECT id
                    FROM habits
                    WHERE habit_name = ?
                ''', ('dev',))
                dev_habits = cursor.fetchall()

                if not dev_habits:
                    logger.info("No habits named 'dev' found.")
                    return

                # Remove each habit by ID
                for habit in dev_habits:
                    habit_id = habit[0]
                    self.remove_habit_by_id(habit_id)
                    logger.info(f"Habit with ID {habit_id} and name 'dev' has been removed.")
                logger.info('\n')
        except sqlite3.Error as e:
            logger.error(f"Error removing habits named 'dev': {e}")
            raise

    ###################
    ### GET METHODS ###
    ###################
    def get_user_habits(self, user_id):
        """
        Retrieve all habits associated with a given user ID.

        :param user_id: The ID of the user whose habits to retrieve.
        :return: A list of dictionaries, each containing the habit data.
        """
        try:
            with closing(self.conn.cursor()) as cursor:
                cursor.execute('''
                    SELECT 
                        h.id, 
                        h.habit_name, 
                        h.time_location, 
                        h.identity, 
                        h.tracking_channel_id
                    FROM habits h
                    WHERE h.user_id = ?
                ''', (user_id,))
                
                habits = cursor.fetchall()
                
                if habits:
                    habit_list = []
                    for habit in habits:
                        habit_data = {
                            'habit_id': habit[0],
                            'habit_name': habit[1],
                            'time_location': habit[2],
                            'identity': habit[3],
                            'tracking_channel_id': habit[4]
                        }
                        habit_list.append(habit_data)
                    
                    return habit_list
                else:
                    logger.info(f"No habits found for user ID {user_id}.")
                    return []
        except sqlite3.Error as e:
            logger.error(f"Error retrieving habits for user ID {user_id}: {e}")
            raise
    
    def get_user_habit_ids(self, user_id):
        """
        Retrieve all habit IDs associated with a given user ID.

        :param user_id: The ID of the user whose habit IDs to retrieve.
        :return: A list of habit IDs.
        """
        try:
            with closing(self.conn.cursor()) as cursor:
                cursor.execute('''
                    SELECT id 
                    FROM habits
                    WHERE user_id = ?
                ''', (user_id,))
                
                habit_ids = cursor.fetchall()
                
                # Extract habit IDs from the query result
                habit_id_list = [habit_id[0] for habit_id in habit_ids] if habit_ids else []
                
                if habit_id_list:
                    logger.info(f"Retrieved habit IDs for user ID {user_id}: {habit_id_list}")
                else:
                    logger.info(f"No habits found for user ID {user_id}.")
                
                return habit_id_list
        except sqlite3.Error as e:
            logger.error(f"Error retrieving habit IDs for user ID {user_id}: {e}")
            raise

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
                    logger.info(f"No habit found with ID {habit_id}.")
                    return None
        except sqlite3.Error as e:
            logger.error(f"Error retrieving habit data for habit ID {habit_id}: {e}")
            raise

    def get_habits_in_channel(self, channel_id):
        try:
            with closing(self.conn.cursor()) as cursor:
                # Perform a JOIN to retrieve all habits for users in the given channel
                cursor.execute('''
                    SELECT h.user_id, h.id, h.habit_name
                    FROM habits h
                    JOIN tracking_channels tc ON h.tracking_channel_id = tc.channel_id
                    WHERE tc.channel_id = ?
                ''', (channel_id,))
                
                habits = cursor.fetchall()
                logging.info(f"Habits fetched: {habits}")
                return habits if habits else []
                    
        except sqlite3.Error as e:
            logger.error(f"Error retrieving habits for channel {channel_id}: {e}")
            raise

    
    def get_previous_week_key(self, current_week_key):
        """
        Get the previous week key in the format 'YYYY-Www'.
        
        :param current_week_key: The current week key.
        :return: The previous week key.
        """
        year, week = map(int, current_week_key.split('-W'))
        logger.debug(f"Calculating previous week key from: current_week_key={current_week_key}")
        
        if week > 1:
            previous_week_key = f"{year}-W{week-1:02d}"
        else:
            # Handle the case where the week is 1, and we need to go back to the last week of the previous year
            previous_year = year - 1
            previous_week = datetime.strptime(f"{previous_year}-12-28", "%Y-%m-%d").isocalendar()[1]
            previous_week_key = f"{previous_year}-W{previous_week:02d}"
        
        logger.debug(f"Previous week key calculated: previous_week_key={previous_week_key}")
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
            logger.error(f"Error retrieving current streak for habit ID {habit_id}: {e}")
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
                            logger.info(f"Dropped table {table_name[0]}")
                    self.conn.commit()
                    logger.info("Database reset completed.")
                # Optionally, reinitialize the tables after the reset
                self._init_tables()
            except sqlite3.Error as e:
                logger.error(f"Error resetting the database: {e}")
                raise


    def close(self):
        try:
            self.conn.close()
            logger.info(f"Disconnected from the database: {self.db_name}")
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
