import psycopg2
from psycopg2 import sql, pool
from contextlib import closing
import logging
logging.basicConfig(level=logging.INFO)
import os
from dotenv import load_dotenv
from datetime import datetime

if __name__ == '__main__':
    # Check if running in development or production mode
    os.environ.pop('NEON_DB_URL', None)
    environment = os.getenv('ENV', 'development')
    environment = 'development'
    print(environment)
    if environment == 'production':
        logging.info("Loading '.env'")
        dotenv_loaded = load_dotenv('.env')  # Load production environment variables
    else:
        logging.info("Loading '.env.dev'")
        dotenv_loaded = load_dotenv('.env.dev')  # Load development environment variables
    logging.info(f".env file loaded: {dotenv_loaded}")

# Define the connection string for PostgreSQL
DB_URL = os.getenv('NEON_DB_URL')
DB_URL = "postgresql://maestro_bot_db_user:QovYPe012aaCnmzA91Gu6hpLRclfoNUm@dpg-crgm0v2j1k6c739jcu3g-a.frankfurt-postgres.render.com/maestro_bot_db"

# Create a connection pool
connection_pool = pool.SimpleConnectionPool(
    1, 10, # Maximum number of connections in the pool
    DB_URL,
    options='-c statement_timeout=60000',
)

logger = logging.getLogger(__name__)

class DatabaseHandler:
    def __init__(self, init=False):
        if connection_pool:
            logger.info("Connection pool created successfully.")
        self.conn = None
        if init:
            self._init_tables()

    def connect(self):
        """Get a connection from the pool if not already connected."""
        if self.conn is None:
            try:
                self.conn = connection_pool.getconn()
                if self.conn:
                    logger.info("Successfully obtained connection from the pool.")
            except psycopg2.Error as e:
                logger.error(f"Error obtaining connection from pool: {e}")
                raise
        else:
            logger.info("Already connected to the database.")

    def release_connection(self):
        """Release the connection back to the pool."""
        if self.conn:
            connection_pool.putconn(self.conn)
            logger.info(f"Connection returned to the pool.")
            self.conn = None

    def _init_tables(self):
        """Initialize the required tables in the database."""
        try:
            self.connect()
            with self.conn:
                with self.conn.cursor() as cursor:
                    # Users table
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS users (
                            user_id BIGINT PRIMARY KEY,
                            username VARCHAR(255)
                        );
                    ''')

                    # Tracking channels table (must be created before 'habits' due to foreign key reference)
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS tracking_channels (
                            channel_id BIGINT PRIMARY KEY,
                            user1_id BIGINT,
                            user2_id BIGINT,
                            user3_id BIGINT,
                            user4_id BIGINT,
                            user5_id BIGINT,
                            user6_id BIGINT,
                            user7_id BIGINT,
                            user8_id BIGINT,
                            FOREIGN KEY (user1_id) REFERENCES users(user_id) ON DELETE SET NULL,
                            FOREIGN KEY (user2_id) REFERENCES users(user_id) ON DELETE SET NULL,
                            FOREIGN KEY (user3_id) REFERENCES users(user_id) ON DELETE SET NULL,
                            FOREIGN KEY (user4_id) REFERENCES users(user_id) ON DELETE SET NULL,
                            FOREIGN KEY (user5_id) REFERENCES users(user_id) ON DELETE SET NULL,
                            FOREIGN KEY (user6_id) REFERENCES users(user_id) ON DELETE SET NULL,
                            FOREIGN KEY (user7_id) REFERENCES users(user_id) ON DELETE SET NULL,
                            FOREIGN KEY (user8_id) REFERENCES users(user_id) ON DELETE SET NULL
                        );
                    ''')

                    # Habits table with tracking_channel_id and ON DELETE CASCADE for tracking
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS habits (
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT NOT NULL,
                            tracking_channel_id BIGINT,
                            habit_name VARCHAR(255) NOT NULL,
                            time_location VARCHAR(255),
                            identity VARCHAR(255),
                            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                            FOREIGN KEY (tracking_channel_id) REFERENCES tracking_channels(channel_id)
                        );
                    ''')

                    # Tracking table with ON DELETE CASCADE on habit_id
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS tracking (
                            habit_id BIGINT NOT NULL,
                            week_key VARCHAR(10) NOT NULL,
                            completed BOOLEAN NOT NULL,
                            streak INTEGER DEFAULT 0,
                            FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE,
                            UNIQUE (habit_id, week_key)
                        );
                    ''')
                self.conn.commit()
        except psycopg2.Error as e:
            logger.error(f"Error creating tables: {e}")
            raise
        finally:
            self.release_connection()


    #########################
    ### INSERTION METHODS ###
    #########################

    def add_user(self, user_id, username):
        """Add a new user to the users table."""
        if self.user_exists(user_id):
            logger.info(f"User with ID {user_id} already exists.")
            return
        try:
            self.connect()
            with self.conn:
                with self.conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO users (user_id, username)
                        VALUES (%s, %s)
                    ''', (user_id, username))
            logger.info(f"User {username} added successfully.")
        except psycopg2.Error as e:
            logger.error(f"Error adding user: {e}")
            raise
        finally:
            self.release_connection()

    def user_exists(self, user_id):
        """Check if a user already exists in the users table."""
        try:
            self.connect()
            with closing(self.conn.cursor()) as cursor:
                cursor.execute('SELECT 1 FROM users WHERE user_id = %s', (user_id,))
                return cursor.fetchone() is not None
        except psycopg2.Error as e:
            logger.error(f"Error checking if user exists: {e}")
            raise
        finally:
            self.release_connection()

    def add_habit_with_data(self, habit_data, tracking_channel_id):
        """Add a new habit to the habits table."""
        try:
            self.connect()
            # Extract data from the habit_data dictionary
            user_id = habit_data['metadata']['user_id']
            habit_name = habit_data['declaration']['habit_name']
            time_location = habit_data['declaration']['time_location']
            identity = habit_data['declaration']['identity']

            with self.conn:
                with self.conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO habits (user_id, tracking_channel_id, habit_name, time_location, identity)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (user_id, tracking_channel_id, habit_name, time_location, identity))
            logger.info(f"Habit '{habit_name}' added successfully for user {user_id}.")
        except psycopg2.Error as e:
            logger.error(f"Error adding habit for user {user_id}: {e}")
            raise
        finally:
            self.release_connection()

    def update_habit_with_data(self, habit_data, tracking_channel_id, habit_id):
        """Update an existing habit in the habits table."""
        try:
            self.connect()
            user_id = habit_data['metadata']['user_id']
            habit_name = habit_data['declaration']['habit_name']
            time_location = habit_data['declaration']['time_location']
            identity = habit_data['declaration']['identity']

            with self.conn:
                with self.conn.cursor() as cursor:
                    cursor.execute('''
                        UPDATE habits
                        SET user_id = %s, tracking_channel_id = %s, habit_name = %s, time_location = %s, identity = %s
                        WHERE id = %s
                    ''', (user_id, tracking_channel_id, habit_name, time_location, identity, habit_id))
            logger.info(f"Habit ID {habit_id} updated successfully.")
        except psycopg2.Error as e:
            logger.error(f"Error updating habit for user {user_id}: {e}")
            raise
        finally:
            self.release_connection()

    def add_user_to_tracking_channel(self, user_id, channel_id):
        """Add a user to the first available slot in the tracking channel."""
        try:
            self.connect()
            with self.conn:
                with self.conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT user1_id, user2_id, user3_id, user4_id, user5_id, user6_id, user7_id, user8_id 
                        FROM tracking_channels 
                        WHERE channel_id = %s
                    ''', (channel_id,))
                    channel = cursor.fetchone()

                    if not channel:
                        logger.info(f"Channel {channel_id} does not exist. Creating new channel.")
                        cursor.execute('''
                            INSERT INTO tracking_channels (channel_id)
                            VALUES (%s)
                        ''', (channel_id,))
                        # Re-fetch the channel data
                        cursor.execute('''
                            SELECT user1_id, user2_id, user3_id, user4_id, user5_id, user6_id, user7_id, user8_id 
                            FROM tracking_channels 
                            WHERE channel_id = %s
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

                    column_name = f"user{slot}_id"
                    cursor.execute(sql.SQL('''
                        UPDATE tracking_channels
                        SET {} = %s
                        WHERE channel_id = %s
                    ''').format(sql.Identifier(column_name)), (user_id, channel_id))
            logger.info(f"User {user_id} added to channel {channel_id} in slot {slot}.")
            return True
        except psycopg2.Error as e:
            logger.error(f"Error adding user to channel {channel_id}: {e}")
            raise
        finally:
            self.release_connection()

    def mark_habit_completed(self, habit_id, completed, current_week=True, week_key=None):
        """Mark a habit as completed for a given week."""
        try:
            self.connect()
            week_key = self._get_week_key(current_week, week_key) if week_key else week_key
            logger.debug(f"Marking habit as completed: habit_id={habit_id}, completed={completed}, week_key={week_key}")

            with self.conn:
                with self.conn.cursor() as cursor:
                    last_streak_record = self._get_last_streak_record(cursor, habit_id)
                    new_streak = self._calculate_new_streak(completed, last_streak_record, week_key)
                    self._insert_or_update_tracking(cursor, habit_id, week_key, completed, new_streak)
        except psycopg2.IntegrityError:
            logger.warning(f"Habit with ID {habit_id} already has a record for week {week_key}.")
        except psycopg2.Error as e:
            logger.error(f"Error marking habit as completed: {e}")
            raise
        finally:
            self.release_connection()

    def _get_week_key(self, current_week, week_key):
        if not week_key and current_week:
            week_key = datetime.now().strftime("%Y-W%U")
        return week_key

    def _get_last_streak_record(self, cursor, habit_id):
        cursor.execute('''
            SELECT week_key, streak 
            FROM tracking 
            WHERE habit_id = %s 
            ORDER BY week_key DESC 
            LIMIT 1
        ''', (habit_id,))
        return cursor.fetchone()

    def _calculate_new_streak(self, completed, last_streak_record, week_key):
        if completed:
            if last_streak_record:
                last_week_key, last_streak = last_streak_record
                if last_week_key == week_key:
                    return last_streak
                elif last_week_key == self.get_previous_week_key(week_key):
                    return last_streak + 1
                else:
                    return 1
            else:
                return 1
        else:
            return 0

    def _insert_or_update_tracking(self, cursor, habit_id, week_key, completed, new_streak):
        cursor.execute('''
            INSERT INTO tracking (habit_id, week_key, completed, streak)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (habit_id, week_key) DO UPDATE SET completed = excluded.completed, streak = excluded.streak
        ''', (habit_id, week_key, completed, new_streak))
        logger.info(f"Habit with ID {habit_id} marked as completed for week {week_key} with streak {new_streak}.")

    def get_previous_week_key(self, current_week_key):
        """Get the previous week key in the format 'YYYY-Www'."""
        year, week = map(int, current_week_key.split('-W'))
        if week > 1:
            previous_week_key = f"{year}-W{week-1:02d}"
        else:
            previous_year = year - 1
            previous_week = datetime.strptime(f"{previous_year}-12-28", "%Y-%m-%d").isocalendar()[1]
            previous_week_key = f"{previous_year}-W{previous_week:02d}"
        return previous_week_key
    
    def reset_habits_id_sequence(self):
        """Reset the habits ID sequence to the maximum ID in the habits table."""
        try:
            self.connect()
            with closing(self.conn.cursor()) as cursor:
                # Get the maximum id from the habits table
                cursor.execute('''SELECT MAX(id) FROM habits;''')
                max_id = cursor.fetchone()[0]

                if max_id:
                    # Reset the sequence to the max id value
                    cursor.execute('''SELECT setval('habits_id_seq', %s);''', (max_id,))
                    self.conn.commit()
                    logger.info(f"Habits ID sequence reset to {max_id}")
                else:
                    logger.warning("No entries in the habits table; sequence reset not needed")
        except psycopg2.Error as e:
            logger.error(f"Error resetting habits ID sequence: {e}")
            raise
        finally:
            self.release_connection()



    ###################
    ### GET METHODS ###
    ###################

    def get_user_habits(self, user_id):
        """Retrieve all habits associated with a given user ID."""
        try:
            self.connect()
            with closing(self.conn.cursor()) as cursor:
                cursor.execute('''
                    SELECT id, habit_name, time_location, identity, tracking_channel_id
                    FROM habits
                    WHERE user_id = %s
                ''', (user_id,))
                habits = cursor.fetchall()
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
        except psycopg2.Error as e:
            logger.error(f"Error retrieving habits for user ID {user_id}: {e}")
            raise
        finally:
            self.release_connection()

    def get_user_habit_ids(self, user_id):
        """Retrieve all habit IDs associated with a given user ID."""
        try:
            self.connect()
            with closing(self.conn.cursor()) as cursor:
                cursor.execute('''
                    SELECT id 
                    FROM habits
                    WHERE user_id = %s
                ''', (user_id,))
                habit_ids = cursor.fetchall()
                habit_id_list = [habit_id[0] for habit_id in habit_ids] if habit_ids else []
                return habit_id_list
        except psycopg2.Error as e:
            logger.error(f"Error retrieving habit IDs for user ID {user_id}: {e}")
            raise
        finally:
            self.release_connection()

    def get_habit_data(self, habit_id):
        """Retrieve habit data from the database based on the habit ID."""
        try:
            self.connect()
            with closing(self.conn.cursor()) as cursor:
                cursor.execute('''
                    SELECT h.id, h.user_id, h.tracking_channel_id, h.habit_name, h.time_location, h.identity, u.username
                    FROM habits h
                    JOIN users u ON h.user_id = u.user_id
                    WHERE h.id = %s
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
        except psycopg2.Error as e:
            logger.error(f"Error retrieving habit data for habit ID {habit_id}: {e}")
            raise
        finally:
            self.release_connection()

    def get_habits_in_channel(self, channel_id):
        """Retrieve all habits in a specific tracking channel."""
        try:
            self.connect()
            with closing(self.conn.cursor()) as cursor:
                cursor.execute('''
                    SELECT h.user_id, h.id, h.habit_name
                    FROM habits h
                    JOIN tracking_channels tc ON h.tracking_channel_id = tc.channel_id
                    WHERE tc.channel_id = %s
                ''', (channel_id,))
                habits = cursor.fetchall()
                return habits if habits else []
        except psycopg2.Error as e:
            logger.error(f"Error retrieving habits for channel {channel_id}: {e}")
            raise
        finally:
            self.release_connection()

    def get_current_streak(self, habit_id):
        """Retrieve the current streak for the given habit ID."""
        try:
            self.connect()
            with closing(self.conn.cursor()) as cursor:
                cursor.execute('''
                    SELECT streak 
                    FROM tracking 
                    WHERE habit_id = %s 
                    ORDER BY week_key DESC 
                    LIMIT 1
                ''', (habit_id,))
                streak_record = cursor.fetchone()
                return streak_record[0] if streak_record else 0
        except psycopg2.Error as e:
            logger.error(f"Error retrieving current streak for habit ID {habit_id}: {e}")
            raise
        finally:
            self.release_connection()

    ###########################
    ### MAINTAINING METHODS ###
    ###########################

    def remove_habit_by_id(self, habit_id):
        """Remove a habit and its associated tracking data from the database."""
        try:
            self.connect()  # Ensure we have a connection
            
            with closing(self.conn.cursor()) as cursor:
                # Retrieve the habit's data, specifically the user_id and tracking_channel_id
                cursor.execute('''
                    SELECT user_id, tracking_channel_id
                    FROM habits
                    WHERE id = %s
                ''', (habit_id,))
                habit_data = cursor.fetchone()

                if not habit_data:
                    logger.error(f"No habit found with ID {habit_id}.")
                    return

                user_id, tracking_channel_id = habit_data

                # Remove the tracking data related to the habit
                cursor.execute('''
                    DELETE FROM tracking
                    WHERE habit_id = %s
                ''', (habit_id,))

                # Remove the habit itself
                cursor.execute('''
                    DELETE FROM habits
                    WHERE id = %s
                ''', (habit_id,))

                # Clear the user's slot in the tracking_channels table
                if tracking_channel_id:
                    cursor.execute(f'''
                        SELECT channel_id, user1_id, user2_id, user3_id, user4_id, user5_id, user6_id, user7_id, user8_id
                        FROM tracking_channels
                        WHERE channel_id = %s
                    ''', (tracking_channel_id,))
                    channel_data = cursor.fetchone()

                    if channel_data:
                        # Find the user's slot and set it to NULL
                        for i, user in enumerate(channel_data[1:], start=1):  # Skip channel_id
                            if user == user_id:
                                column_name = f"user{i}_id"
                                cursor.execute(f'''
                                    UPDATE tracking_channels
                                    SET {column_name} = NULL
                                    WHERE channel_id = %s
                                ''', (tracking_channel_id,))
                                logger.info(f"Cleared user {user_id} from slot {i} in channel {tracking_channel_id}.")
                                break

                self.conn.commit()  # Commit the changes

                logger.info(f"Habit with ID {habit_id} and its tracking data have been successfully removed.")

        except psycopg2.Error as e:
            logger.error(f"Error removing habit with ID {habit_id}: {e}")
            raise
        finally:
            self.release_connection()  # Ensure the connection is returned to the pool


    def remove_all_dev_habits(self):
        """Remove all habits named 'dev' and their associated tracking data."""
        logger.info("Removing all the development purpose habit entries in the database")
        try:
            self.connect()  # Ensure we have a connection

            with closing(self.conn.cursor()) as cursor:
                # Fetch all habits named 'dev'
                cursor.execute('''
                    SELECT id
                    FROM habits
                    WHERE habit_name = 'dev'
                ''')
                dev_habits = cursor.fetchall()

                if not dev_habits:
                    logger.info("No habits named 'dev' found.")
                    return

                # Remove each habit by ID
                for habit in dev_habits:
                    habit_id = habit[0]
                    self.remove_habit_by_id(habit_id)  # Ensure no recursive connection

        except psycopg2.Error as e:
            logger.error(f"Error removing habits named 'dev': {e}")
            raise
        finally:
            self.release_connection()  # Ensure the connection is returned to the pool


    def reset_db(self, second_check=False):
        """Drop all tables and reset the database."""
        try:
            self.connect()
            if second_check:
                with self.conn:
                    with self.conn.cursor() as cursor:
                        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
                        tables = cursor.fetchall()
                        for table_name in tables:
                            cursor.execute(f"DROP TABLE IF EXISTS {table_name[0]} CASCADE")
                            logger.info(f"Dropped table {table_name[0]}")
                    self.conn.commit()
                self._init_tables()
                logger.info("Database reset and initialized.")
        except Exception as e:
            logger.error(f"Error resetting the database: {e}")
            raise
        finally:
            self.release_connection()
            
    def close_pool(self):
        """Close all connections in the pool."""
        connection_pool.closeall()
        logger.info("Closed all connections in the pool.")

# Example usage:
if __name__ == "__main__":
    db_handler = DatabaseHandler(init=True)

    db_handler.reset_db(second_check=False)
    # db_handler.reset_habits_id_sequence()
    # Add a new user
    # db_handler.add_user(123456789, "JohnDoe")

    # # Check if user exists
    # exists = db_handler.user_exists(123456789)
    # print(f"User exists: {exists}")

    # # Add a habit
    # habit_data = {
    #     'metadata': {'user_id': 123456789},
    #     'declaration': {
    #         'habit_name': 'Read a book',
    #         'time_location': 'Evenings',
    #         'identity': 'Reader'
    #     }
    # }
    # db_handler.add_habit_with_data(habit_data, tracking_channel_id=1)

    # # Get user's habits
    # habits = db_handler.get_user_habits(123456789)
    # print("User's Habits:", habits)

    # # Mark habit as completed
    # db_handler.mark_habit_completed(habit_id=1, completed=True)

    # # Get current streak
    # streak = db_handler.get_current_streak(habit_id=1)
    # print(f"Current streak for habit 1: {streak}")

    # # Remove a habit
    # db_handler.remove_habit_by_id(habit_id=1)

    # Reset the database (for testing)
    # db_handler.reset_db(second_check=True)

    # Close the connection pool at the end of the script
    db_handler.close_pool()
