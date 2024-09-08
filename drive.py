import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import re
import json

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate():
    """Authenticate using Google Drive API credentials."""
    creds = None

    # Try to load token.pickle first for existing credentials
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If no valid creds, load from environment variable
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Load credentials from environment variable
            credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
            if credentials_json:
                credentials_dict = json.loads(credentials_json)

                # Write credentials to a temporary file if needed
                with open('credentials_temp.json', 'w') as f:
                    json.dump(credentials_dict, f)

                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials_temp.json', SCOPES
                )
                creds = flow.run_local_server(port=0)

                # Clean up the temporary file after use
                os.remove('credentials_temp.json')

        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return creds


def set_name(service, folder_id, base_name):
    """Sets the next incremental name for a new file."""
    # List all files in the specified folder
    results = service.files().list(q=f"'{folder_id}' in parents", spaces='drive', fields="files(name)").execute()
    files = results.get('files', [])
    
    # Regular expression to match file names with numbers, e.g., "dcbot_1.db"
    pattern = re.compile(rf'{re.escape(base_name)}_(\d+)\.db')

    # Find the highest number from existing files
    max_number = 0
    for file in files:
        match = pattern.match(file['name'])
        if match:
            file_number = int(match.group(1))
            max_number = max(max_number, file_number)
    
    # Return the new file name with incremented number
    new_number = max_number + 1
    new_file_name = f"{base_name}_{new_number}.db"
    return new_file_name

def upload_file(file_path, file_name, folder_id):
    """Uploads a file to a specific folder in Google Drive."""
    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)

    # Set the new file name
    new_file_name = set_name(service, folder_id, file_name)

    # Add the parent folder ID to the file metadata
    file_metadata = {
        'name': new_file_name,
        'parents': [folder_id]  # Specify the folder ID here
    }

    media = MediaFileUpload(file_path, mimetype='application/octet-stream')

    # Upload the file to the specified folder
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f'File uploaded with ID: {file.get("id")} and name: {new_file_name}')

if __name__ == '__main__':
    # Example usage:
    folder_id = 'folder_id'  # Replace with your folder ID
    upload_file('discord_bot.db', 'discord_bot', folder_id)
