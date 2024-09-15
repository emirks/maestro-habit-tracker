import os
import csv
import logging
from psycopg2 import pool
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connection details
DB_URL = os.getenv('NEON_DB_URL')  # Make sure NEON_DB_URL is set in your .env file
DB_URL = "postgresql://maestro_bot_db_user:QovYPe012aaCnmzA91Gu6hpLRclfoNUm@dpg-crgm0v2j1k6c739jcu3g-a.frankfurt-postgres.render.com/maestro_bot_db"

# Create a connection pool
connection_pool = pool.SimpleConnectionPool(
    1,  # Minimum number of connections in the pool
    10,  # Maximum number of connections in the pool
    DB_URL
)

if connection_pool:
    logger.info("Connection pool created successfully")

# Folder where your CSV files are located
csv_folder = 'db_data/'

def import_csv_to_db(file_name, query, columns):
    """
    Function to import CSV data into the database.
    
    :param file_name: The name of the CSV file to import.
    :param query: The SQL insert query string.
    :param columns: Number of columns expected in the CSV file.
    """
    conn = connection_pool.getconn()
    cursor = conn.cursor()
    
    try:
        file_path = os.path.join(csv_folder, file_name)
        with open(file_path, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # Skip the header row
            for row in reader:
                if len(row) == columns:
                    cursor.execute(query, row)
                else:
                    logger.warning(f"Skipping row in {file_name}: {row}, due to incorrect number of columns.")
        
        conn.commit()
        logger.info(f"Data from {file_name} imported successfully.")
    
    except Exception as e:
        conn.rollback()
        logger.error(f"Error importing {file_name}: {e}")
    
    finally:
        cursor.close()
        connection_pool.putconn(conn)

# Import users.csv
import_csv_to_db(
    'users.csv',
    "INSERT INTO users (user_id, username) VALUES (%s, %s)",
    2  # Number of columns
)

# Import tracking_channels.csv
import_csv_to_db(
    'tracking_channels.csv',
    """
    INSERT INTO tracking_channels (
        channel_id, user1_id, user2_id, user3_id, user4_id, 
        user5_id, user6_id, user7_id, user8_id
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """,
    9  # Number of columns
)

# Import habits.csv with id (Primary Key)
import_csv_to_db(
    'habits.csv',
    "INSERT INTO habits (id, user_id, tracking_channel_id, habit_name, time_location, identity) VALUES (%s, %s, %s, %s, %s, %s)",
    6  # Number of columns (including id)
)

# Import tracking.csv
import_csv_to_db(
    'tracking.csv',
    "INSERT INTO tracking (habit_id, week_key, completed, streak) VALUES (%s, %s, %s, %s)",
    4  # Number of columns
)

# Close all connections in the pool after finishing
connection_pool.closeall()

logger.info("All data imported and connection pool closed.")
