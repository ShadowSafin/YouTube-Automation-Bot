import os
import random
import re
import time
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

# If modifying these SCOPES, delete the file token.json.
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive']
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# Hardcoded Information
DRIVE_CREDENTIALS_PATH = 'credentials.json'  # Update with your Google Drive credentials file path
YOUTUBE_CREDENTIALS_PATH = 'client_secrets.json'  # Update with your YouTube client secrets file path
SOURCE_FOLDER_ID = 'your_source_folder_id'  # Update with the source folder ID in Google Drive
DESTINATION_FOLDER_ID = 'your_destination_folder_id'  # Update with the destination folder ID in Google Drive
TAGS = ["tag1", "tag2", "tag3"]  # Update with relevant YouTube tags

# Function to authenticate and get Google Drive service
def authenticate_google_drive(drive_credentials_path):
    creds = None
    if os.path.exists('token_drive.json'):
        creds = Credentials.from_authorized_user_file('token_drive.json', DRIVE_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(drive_credentials_path, DRIVE_SCOPES)
            creds = flow.run_local_server(port=8000)  # Run local server on port 8000
        with open('token_drive.json', 'w') as token:
            token.write(creds.to_json())

    service = build('drive', 'v3', credentials=creds)
    return service

# Function to authenticate and get YouTube service
def authenticate_youtube(youtube_credentials_path):
    creds = None
    if os.path.exists('token_youtube.json'):
        creds = Credentials.from_authorized_user_file('token_youtube.json', YOUTUBE_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(youtube_credentials_path, YOUTUBE_SCOPES)
            creds = flow.run_local_server(port=8000)  # Run local server on port 8000
        with open('token_youtube.json', 'w') as token:
            token.write(creds.to_json())

    service = build('youtube', 'v3', credentials=creds)
    return service

# Function to get a random file from a specific Google Drive folder
def get_random_file(service, folder_id):
    results = service.files().list(
        q=f"'{folder_id}' in parents and mimeType contains 'video/'",
        spaces='drive',
        fields='nextPageToken, files(id, name)',
        pageSize=100
    ).execute()

    items = results.get('files', [])
    if items:
        return random.choice(items)
    return None

# Function to move the file to a different folder
def move_file_to_folder(service, file_id, target_folder_id):
    file = service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents'))

    service.files().update(
        fileId=file_id,
        addParents=target_folder_id,
        removeParents=previous_parents,
        fields='id, parents'
    ).execute()

    print(f"File moved to folder: {target_folder_id}")

# Function to clean up file name for YouTube title
def clean_file_name(file_name):
    title = os.path.splitext(file_name)[0]
    title = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', title)
    title = title[:100]
    return title.strip() or "Untitled Video"

# Function to upload video to YouTube
def upload_video_to_youtube(service, video_file_path, title, description, tags):
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '22'  # Set category ID here
        },
        'status': {
            'privacyStatus': 'public',
            'madeForKids': False
        }
    }

    media = MediaFileUpload(video_file_path, chunksize=-1, resumable=True, mimetype='video/*')
    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if 'id' in response:
            print(f"Video uploaded successfully. Video ID: {response['id']}")
        elif 'error' in response:
            raise Exception(f"An error occurred: {response['error']}")

# Main function
def main():
    drive_service = authenticate_google_drive(DRIVE_CREDENTIALS_PATH)
    youtube_service = authenticate_youtube(YOUTUBE_CREDENTIALS_PATH)

    random_file = get_random_file(drive_service, SOURCE_FOLDER_ID)
    if random_file:
        file_name = random_file['name']
        file_id = random_file['id']

        cleaned_file_name = clean_file_name(file_name)

        print(f"Random file selected: {cleaned_file_name}")

        file_request = drive_service.files().get_media(fileId=file_id)
        video_file_path = f"./{file_name}"
        with open(video_file_path, 'wb') as video_file:
            downloader = MediaIoBaseDownload(video_file, file_request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

        try:
            upload_video_to_youtube(youtube_service, video_file_path, cleaned_file_name, cleaned_file_name, TAGS)
        except Exception as e:
            print(f"An error occurred: {e}")

        move_file_to_folder(drive_service, file_id, DESTINATION_FOLDER_ID)
        time.sleep(20)  # Wait for 20 seconds after uploading

if __name__ == "__main__":
    main()
