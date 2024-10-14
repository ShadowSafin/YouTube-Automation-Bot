import threading
import os
import sys
import time
import webbrowser
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import re

# Function to get the path of resources (e.g., client_secret.json and credentials.json) in bundled executable or development mode
def get_resource_path(relative_path):
    """Get the absolute path to a resource in the same directory as the executable."""
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Running in a normal Python environment
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Reinitialize Flask app with dynamic template and static folder paths
def get_template_folder():
    if hasattr(sys, '_MEIPASS'):  # Check if running in a bundled executable
        return os.path.join(sys._MEIPASS, 'templates')
    return 'templates'  # Default folder when running from source

def get_static_folder():
    if hasattr(sys, '_MEIPASS'):  # Check if running in a bundled executable
        return os.path.join(sys._MEIPASS, 'static')
    return 'static'  # Default folder when running from source

# Initialize Flask app with template and static folder paths
app = Flask(__name__, template_folder=get_template_folder(), static_folder=get_static_folder())
app.secret_key = 'your_secret_key'  # Set the secret key

drive_service = None
youtube_service = None
download_progress = 0
upload_progress = 0
logs = []

# Function to authenticate Google Drive
def authenticate_google_drive():
    creds = None
    credentials_path = get_resource_path('credentials.json')  # Path to credentials.json
    token_path = get_resource_path('token_drive.json')  # Path to token_drive.json
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, ['https://www.googleapis.com/auth/drive'])
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, ['https://www.googleapis.com/auth/drive'])
            creds = flow.run_local_server(port=8080)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
    
    drive_service = build('drive', 'v3', credentials=creds)
    return drive_service

# Function to authenticate YouTube
def authenticate_youtube():
    creds = None
    client_secret_path = get_resource_path('client_secret.json')  # Path to client_secret.json
    token_path = get_resource_path('token_youtube.json')  # Path to token_youtube.json
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, ['https://www.googleapis.com/auth/youtube.upload'])
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secret_path, ['https://www.googleapis.com/auth/youtube.upload'])
            creds = flow.run_local_server(port=8081)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
    
    youtube_service = build('youtube', 'v3', credentials=creds)
    return youtube_service

# Function to clean up file name for YouTube title
def clean_file_name(file_name):
    title = os.path.splitext(file_name)[0]
    title = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', title)[:100].strip()
    return title if title else "Untitled Video"

# Function to get a random file from Google Drive
def get_random_file(service, folder_id):
    results = service.files().list(
        q=f"'{folder_id}' in parents and mimeType contains 'video/'",
        spaces='drive',
        fields='nextPageToken, files(id, name)',
        pageSize=100
    ).execute()

    items = results.get('files', [])
    if items:
        return items[0]
    return None

# Function to move file to another folder
def move_file_to_another_folder(service, file_id, destination_folder_id):
    file = service.files().get(fileId=file_id).execute()
    previous_parents = ",".join(file.get('parents'))
    service.files().update(
        fileId=file_id,
        addParents=destination_folder_id,
        removeParents=previous_parents,
        fields='id, parents'
    ).execute()

# Function to upload video to YouTube
def upload_video_to_youtube(service, video_file_path, title, description, tags):
    global upload_progress
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '22'  # Category ID for People & Blogs
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
        if status:
            upload_progress = int(status.progress() * 100)
            logs.append(f"Upload Progress: {upload_progress}%")
        if 'id' in response:
            logs.append(f"Video uploaded successfully. Video ID: {response['id']}")
        elif 'error' in response:
            raise Exception(f"An error occurred: {response['error']}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/authenticate_drive', methods=['POST'])
def authenticate_drive():
    global drive_service
    try:
        drive_service = authenticate_google_drive()
        flash("Google Drive authenticated successfully!", "success")
    except Exception as e:
        flash(f"Error authenticating Google Drive: {str(e)}", "danger")
    return redirect(url_for('index'))

@app.route('/authenticate_youtube', methods=['POST'])
def authenticate_youtube_route():
    global youtube_service
    try:
        youtube_service = authenticate_youtube()
        flash("YouTube authenticated successfully!", "success")
    except Exception as e:
        flash(f"Error authenticating YouTube: {str(e)}", "danger")
    return redirect(url_for('index'))

@app.route('/upload_video', methods=['POST'])
def upload_video():
    global drive_service, youtube_service
    source_folder_id = request.form.get('source_folder_id')
    destination_folder_id = request.form.get('destination_folder_id')
    cleanup = request.form.get('cleanup') == 'on'
    loop = request.form.get('loop') == 'true'
    interval = int(request.form.get('interval') or 0)

    # Flash message immediately to notify the user that the upload has started
    flash("Upload started...", "info")
    
    # Start the upload process in a separate thread
    threading.Thread(target=upload_process, args=(source_folder_id, destination_folder_id, cleanup, loop, interval)).start()
    
    return redirect(url_for('index'))

def upload_process(source_folder_id, destination_folder_id, cleanup, loop, interval):
    global download_progress, upload_progress
    try:
        while True:
            random_file = get_random_file(drive_service, source_folder_id)
            
            if random_file:
                file_name = random_file['name']
                cleaned_file_name = clean_file_name(file_name) if cleanup else file_name
                logs.append(f"Downloading {file_name}...")

                # Download the file from Google Drive
                video_file_path = f"./{cleaned_file_name}.mp4"
                file_id = random_file['id']
                request = drive_service.files().get_media(fileId=file_id)
                with open(video_file_path, 'wb') as file:
                    downloader = MediaIoBaseDownload(file, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        if status:
                            download_progress = int(status.progress() * 100)
                            logs.append(f"Download Progress: {download_progress}%")
                
                # Upload the downloaded file to YouTube
                upload_video_to_youtube(youtube_service, video_file_path, cleaned_file_name, cleaned_file_name, ["Movie", "movierecap", "entertainment"])
                logs.append(f"Video {cleaned_file_name} uploaded successfully!")

                # Move the file to the destination folder
                move_file_to_another_folder(drive_service, file_id, destination_folder_id)
                logs.append(f"Moved {cleaned_file_name} to the destination folder.")
            else:
                logs.append("No video found in the source folder.")
            
            if not loop:
                break  # Exit loop if not looping
            time.sleep(interval)  # Wait before the next loop iteration

    except Exception as e:
        logs.append(f"Error uploading video: {str(e)}")

@app.route('/progress', methods=['GET'])
def progress():
    return jsonify(download_progress=download_progress, upload_progress=upload_progress)

@app.route('/logs', methods=['GET'])
def get_logs():
    return jsonify({"logs": logs})

if __name__ == '__main__':
    # Start the Flask app in a new thread
    threading.Thread(target=lambda: app.run(debug=True, use_reloader=False)).start()
    
    # Give the server a moment to start
    time.sleep(1)
    
    # Open the default browser to the localhost where the Flask app is running
    webbrowser.open("http://127.0.0.1:5000/")
