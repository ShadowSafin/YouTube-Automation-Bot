import os
import random
import re
import time
from flask import Flask, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

app = Flask(__name__)

# Configuration
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive']
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
DRIVE_CREDENTIALS_PATH = 'credentials.json'
YOUTUBE_CREDENTIALS_PATH = 'client_secrets.json'
SOURCE_FOLDER_ID = 'your_source_folder_id'
DESTINATION_FOLDER_ID = 'your_destination_folder_id'
TAGS = ["tag1", "tag2", "tag3"]

def authenticate_google_drive():
    creds = None
    if os.path.exists('token_drive.json'):
        creds = Credentials.from_authorized_user_file('token_drive.json', DRIVE_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(DRIVE_CREDENTIALS_PATH, DRIVE_SCOPES)
            creds = flow.run_console()  # Change to run_console for headless environments
        with open('token_drive.json', 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def authenticate_youtube():
    creds = None
    if os.path.exists('token_youtube.json'):
        creds = Credentials.from_authorized_user_file('token_youtube.json', YOUTUBE_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(YOUTUBE_CREDENTIALS_PATH, YOUTUBE_SCOPES)
            creds = flow.run_console()  # Change to run_console for headless environments
        with open('token_youtube.json', 'w') as token:
            token.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds)

def get_random_file(service, folder_id):
    results = service.files().list(
        q=f"'{folder_id}' in parents and mimeType contains 'video/'",
        spaces='drive',
        fields='files(id, name)',
        pageSize=100
    ).execute()
    items = results.get('files', [])
    return random.choice(items) if items else None

def move_file_to_folder(service, file_id, target_folder_id):
    file = service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents'))
    service.files().update(
        fileId=file_id,
        addParents=target_folder_id,
        removeParents=previous_parents,
        fields='id, parents'
    ).execute()

def clean_file_name(file_name):
    title = os.path.splitext(file_name)[0]
    title = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', title)
    return title[:100].strip() or "Untitled Video"

def upload_video_to_youtube(service, video_file_path, title, description, tags):
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '24'  # Category ID for Entertainment
        },
        'status': {
            'privacyStatus': 'public',
            'madeForKids': False
        }
    }
    media = MediaFileUpload(video_file_path, chunksize=-1, resumable=True, mimetype='video/*')
    request = service.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if 'id' in response:
            return response['id']
        elif 'error' in response:
            raise Exception(f"An error occurred: {response['error']}")

def automatic_upload():
    drive_service = authenticate_google_drive()
    youtube_service = authenticate_youtube()

    random_file = get_random_file(drive_service, SOURCE_FOLDER_ID)
    if random_file:
        file_name = random_file['name']
        file_id = random_file['id']
        cleaned_file_name = clean_file_name(file_name)

        file_request = drive_service.files().get_media(fileId=file_id)
        video_file_path = f"./{file_name}"
        with open(video_file_path, 'wb') as video_file:
            downloader = MediaIoBaseDownload(video_file, file_request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

        video_id = upload_video_to_youtube(youtube_service, video_file_path, cleaned_file_name, cleaned_file_name, TAGS)
        move_file_to_folder(drive_service, file_id, DESTINATION_FOLDER_ID)
        os.remove(video_file_path)

        return video_id
    else:
        raise Exception("No video files found.")

if __name__ == "__main__":
    try:
        port = int(os.environ.get("PORT", 5000))
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"An error occurred: {e}")
