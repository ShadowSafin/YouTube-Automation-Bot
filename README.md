# YouTube-Auto-Upload-From-Gdrive
This is a python script that could randomly take a file from a Google Drive folder and upload it to YouTube with the file name as title and description. After upload it will move the file to another folder to avoid reuploading.

# Authentication
To make the script work add the Google drive API OAuth2.0 file as "credentials.json" and YouTube data v3 API client secret as "client_secret.json" in the folder.

You must rename the file according to the upper instruction. Renaming it will not chance anything in the file.
# Folder ID
(Source_File_ID) and (Destination_Folder_ID) should be changed with your desired folder id.

# Getting GDrive API Oauth Client ID 
Go to your google cloud console and enable Google Drive API, then follow the official google documentation - https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid

Make Sure add "http://localhost:80" as authorised JavaScript Origins and "http://localhost:80/oauth2callback" + "http://localhost:80/" as authorised redirect urls.

# Getting YouTube Data V3 API client secret
Go to your google cloud console and enable YouTuve Data v3 API, then follow the official google documentation - https://developers.google.com/youtube/v3/guides/auth/installed-apps#uwp

Make Sure add "http://localhost:80" as authorised JavaScript Origins and "http://localhost:80/oauth2callback" + "http://localhost:80/" as authorised redirect urls.


