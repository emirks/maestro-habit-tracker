import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
import re
import json
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define Google Drive API scope
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate():
    """Authenticate using Google Drive API credentials (Service Account or OAuth)."""
    creds = None

    # Try to load token.pickle first for existing credentials
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If no valid creds, try to load credentials from a service account or environment variable
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Load credentials from the environment variable for the service account
            service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            if service_account_json:
                # Parse the service account credentials from the environment variable
                service_account_info = json.loads(service_account_json)
                creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)

        # Save the credentials for the next run (if it's not already from the service account)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def generate_timestamped_name(base_name):
    """Generates a new file name based on the current timestamp in a more readable format."""
    # More readable format: YYYY-MM-DD_HH-MM-SS
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{base_name}_{timestamp}.db"

def upload_file(file_path, file_name, folder_id):
    """Uploads a file to a specific folder in Google Drive."""
    # Authenticate and create the Google Drive service
    service = build('drive', 'v3', credentials=authenticate())

    # Ensure that the file exists and is accessible
    if not os.path.exists(file_path):
        logger.error(f"File '{file_path}' not found.")
        return

    # Check if the file size is 0 bytes before uploading
    if os.path.getsize(file_path) == 0:
        logger.error(f"File '{file_path}' is empty (0 bytes). Aborting upload.")
        raise ValueError(f"File '{file_path}' is empty (0 bytes) and cannot be uploaded.")

    # Set the new file name with a readable timestamp
    new_file_name = generate_timestamped_name(file_name)

    # Add the parent folder ID to the file metadata
    file_metadata = {
        'name': new_file_name,
        'parents': [folder_id]  # Specify the folder ID here
    }

    # Use resumable=True for safer file uploads
    media = MediaFileUpload(file_path, mimetype='application/octet-stream', resumable=True)

    try:
        # Upload the file to the specified folder
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logger.info(f'File uploaded with ID: {file.get("id")} and name: {new_file_name}')
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise

def download_latest_file(folder_id, base_name):
    """Downloads the latest file with the given base name (based on timestamp) from Google Drive to the current directory."""
    creds = authenticate()
    
    # Disable cache discovery to avoid errors and create the Drive API service
    service = build('drive', 'v3', credentials=creds, cache_discovery=False)

    logger.info("Fetching files from Google Drive...")
    
    # List all files in the specified folder
    try:
        results = service.files().list(q=f"'{folder_id}' in parents", spaces='drive', fields="files(id, name, size)").execute()
        files = results.get('files', [])
    except Exception as e:
        logger.error(f"Failed to list files in Google Drive folder: {e}")
        return

    if not files:
        logger.info("No files found in the folder.")
        return

    # Log details about all files found
    logger.info(f"{len(files)} file(s) found in Google Drive folder.")
    for file in files:
        logger.info(f"Found file: {file['name']} (size: {file.get('size', 'unknown')} bytes)")


    # Regular expression to match file names with readable timestamps, e.g., "discord_bot_YYYY-MM-DD_HH-MM-SS.db"
    pattern = re.compile(rf'{re.escape(base_name)}_(\d{{4}}-\d{{2}}-\d{{2}}_\d{{2}}-\d{{2}}-\d{{2}})\.db')

    # Find the file with the most recent timestamp
    latest_file = None
    latest_timestamp = None
    for file in files:
        match = pattern.match(file['name'])
        if match:
            file_timestamp = match.group(1)  # Extract the timestamp part of the filename
            if latest_timestamp is None or file_timestamp > latest_timestamp:
                latest_timestamp = file_timestamp
                latest_file = file

    if not latest_file:
        logger.info("No matching files found with the given base name.")
        return
    
    logger.info(f"Latest file found: {latest_file['name']} (size: {latest_file.get('size', 'unknown')} bytes)")

    # Prepare to download the latest file
    file_id = latest_file['id']
    file_path = os.path.join(os.getcwd(), 'discord_bot.db')  # Download as 'discord_bot.db' in the current directory
    temp_file_path = file_path + ".part"  # Use a temporary file for downloading

    # Check if 'discord_bot.db' already exists and back it up
    if os.path.exists(file_path):
        backup_path = file_path + '.bak'
        os.rename(file_path, backup_path)
        logger.info(f"Existing 'discord_bot.db' renamed to 'discord_bot.db.bak'.")

    # Proceed to download the file
    try:
        with open(temp_file_path, 'wb') as temp_file:
            request = service.files().get_media(fileId=file_id)
            downloader = MediaIoBaseDownload(temp_file, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                logger.info(f"Download progress: {int(status.progress() * 100)}% complete.")
        
        # Ensure the file size is not zero after download
        final_size = os.path.getsize(temp_file_path)
        if final_size == 0:
            raise ValueError("Downloaded file is empty (0 bytes).")

        logger.info(f"Download completed. File size: {final_size} bytes")

        # Rename the temporary file to the final file name after successful download
        os.rename(temp_file_path, file_path)
        logger.info(f"File '{latest_file['name']}' downloaded as 'discord_bot.db' in the current directory.")

    except Exception as e:
        # Clean up temporary file if the download fails
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        logger.error(f"Failed to download file: {e}")
        raise


if __name__ == '__main__':
    # Example usage:
    folder_id = 'your_folder_id'  # Replace with your folder ID

    # Upload a file
    upload_file('discord_bot.db', 'discord_bot', folder_id)

    # Download the latest file
    download_latest_file(folder_id, 'discord_bot')
