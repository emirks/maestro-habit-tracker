import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2.service_account import Credentials
import io
import re
import logging
from datetime import datetime
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the scope for Google Drive API access
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate():
    """Authenticate using either a Service Account or OAuth."""
    creds = None
    service_account_json = os.environ['GOOGLE_SERVICE_ACCOUNT_JSON']

    
    # Save the service account credentials to a temporary file
    service_account_info = json.loads(service_account_json)
    service_account_path = 'service_account_temp.json'
    
    with open(service_account_path, 'w') as f:
        json.dump(service_account_info, f)
    
    # Authenticate using service account credentials
    creds = Credentials.from_service_account_file(service_account_path, scopes=SCOPES)
    logger.info("Authenticated using Service Account.")
    
    # Remove the temporary file after use
    os.remove(service_account_path)
    

    return creds


def generate_timestamped_name(base_name):
    """Generates a file name in the format discord_bot_timestamp.db"""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{base_name}_{timestamp}.db"

def upload_file(file_path, folder_id, base_name):
    """Uploads a file to a specific folder in Google Drive with a timestamped name."""
    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)

    # Generate a timestamped name for the file
    new_file_name = generate_timestamped_name(base_name)

    # Prepare the file metadata and media for upload
    file_metadata = {
        'name': new_file_name,
        'parents': [folder_id]  # Specify the folder ID here
    }
    media = MediaFileUpload(file_path, mimetype='application/octet-stream')

    try:
        # Upload the file to Google Drive
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logger.info(f'File uploaded successfully with ID: {file.get("id")} and name: {new_file_name}')
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise

def extract_timestamp(file_name):
    """Extracts the timestamp from the file name. Assumes the format is name_YYYY-MM-DD_HH-MM-SS.ext."""
    pattern = r'_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})'
    match = re.search(pattern, file_name)
    if match:
        return match.group(1)
    return None

def download_latest_file(folder_id, base_name, download_name):
    """Downloads the latest file matching the specified base name from Google Drive, ordered by the timestamp in the name."""
    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)

    logger.info("Fetching files from Google Drive...")

    try:
        # List all files in the specified folder (no base_name filter)
        results = service.files().list(
            q=f"'{folder_id}' in parents",  # Only check for files in the specified folder
            spaces='drive',
            fields="files(id, name)",  # Request file id and name
        ).execute()
        files = results.get('files', [])
    except Exception as e:
        logger.error(f"Failed to list files in Google Drive: {e}")
        return

    if not files:
        logger.info("No files found in the drive folder.")
        raise FileNotFoundError("No matching files found in the drive folder.")
    else:
        logger.info(f"Found {len(files)} files in the folder.")

    # Extract timestamps and sort files by the extracted timestamp
    files_with_timestamps = []
    for file in files:
        timestamp = extract_timestamp(file['name'])
        if timestamp:
            files_with_timestamps.append((file, timestamp))
    
    if not files_with_timestamps:
        logger.info("No files found with a valid timestamp in the name.")
        raise FileNotFoundError("No matching files found with a valid timestamp.")

    # Sort files by timestamp in descending order (most recent first)
    files_with_timestamps.sort(key=lambda x: x[1], reverse=True)
    
    # The latest file (first in the list)
    latest_file = files_with_timestamps[0][0]
    logger.info(f"Latest file found: {latest_file['name']} (ID: {latest_file['id']})")

    # Download the latest file
    request = service.files().get_media(fileId=latest_file['id'])
    file_path = os.path.join(os.getcwd(), download_name)

    with io.FileIO(file_path, 'wb') as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            logger.info(f"Download progress: {int(status.progress() * 100)}% complete.")

    logger.info(f"File '{latest_file['name']}' downloaded successfully to {file_path}")

if __name__ == '__main__':
    # Replace with your Google Drive folder ID
    folder_id = '1bpEvZb364J0Sdn6kA7FPfIhdl_6AmWfY'
    
    # # Example: Upload file with a timestamped name
    # upload_file('discord_bot.db', folder_id)

    # Example: Download the latest file matching 'discord_bot'
    download_latest_file(folder_id, 'discord_bot')
