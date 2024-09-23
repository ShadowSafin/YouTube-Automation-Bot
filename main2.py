import os
import random
import re  # For cleaning up file names
import time  # For adding a delay after upload
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
SOURCE_FOLDER_ID = '1qfYtd0yZgDTjJ2UKimfJQgSWVd4AtOl_'  # Update with the source folder ID in Google Drive
DESTINATION_FOLDER_ID = '1DnpkK1rT3YhmwRHwhEFf94tCyz_AL_7s'  # Update with the destination folder ID in Google Drive
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
            creds = flow.run_local_server(port=80)
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
            creds = flow.run_local_server(port=80)
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
    # Remove file extension
    title = os.path.splitext(file_name)[0]
    # Replace invalid characters with a space
    title = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', title)
    # Truncate to maximum allowed length (100 characters)
    title = title[:100].strip()
    
    # Fallback title if the cleaned name is empty
    return title if title else "Untitled Video"

# Function to upload video to YouTube
def upload_video_to_youtube(service, video_file_path, title, description, tags):
    body = {
        'snippet': {
            'title': title,  # Title set as cleaned file name
            'description': description,  # Description set as the cleaned file name
            'tags': tags,
            'categoryId': '22'  # Category ID for People & Blogs
        },
        'status': {
            'privacyStatus': 'public',
            'madeForKids': False  # Set this flag to False for "not made for kids"
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

        # Clean file name for YouTube title
        cleaned_file_name = clean_file_name(file_name)

        print(f"Random file selected: {cleaned_file_name}")

        # Download the file from Google Drive
        file_request = drive_service.files().get_media(fileId=file_id)
        video_file_path = f"./{file_name}"
        with open(video_file_path, 'wb') as video_file:
            downloader = MediaIoBaseDownload(video_file, file_request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    print(f"Download {int(status.progress() * 100)}% complete.")

        # Attempt to upload to YouTube with error handling
        try:
            upload_video_to_youtube(youtube_service, video_file_path, cleaned_file_name, cleaned_file_name, TAGS)
        except Exception as e:
            if 'quotaExceeded' in str(e):
                print("Quota exceeded. Exiting process.")
                return  # Exit after notifying of quota limit
            else:
                print(f"An error occurred: {e}")

        # Wait for 20 seconds after the video is uploaded
        print("Waiting for 20 seconds after upload...")
        time.sleep(20)

        # Move the file to another folder after uploading
        move_file_to_folder(drive_service, file_id, DESTINATION_FOLDER_ID)

        # Optionally delete the file after upload
        os.remove(video_file_path)

    print("Process completed.")

if __name__ == "__main__":
    main()
