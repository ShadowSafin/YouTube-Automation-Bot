# YouTube-Automation-Bot
This is a python script that could randomly take a file from a Google Drive folder and upload it to YouTube with the file name as title and description. After upload it will move the file to another folder to avoid reuploading.

# How to run Run 
Add your own google drive API client secret and YouTube Data V3 API Client secret in the directory. Replace the already existing client secrets. 

Make sure to Add - "Google drive API OAuth2.0 file as "credentials.json" and YouTube data v3 API client secret as "client_secret.json" in the main folder".

After adding the client secrets open package.bat file and wait for the process to finish. Now go to "Dist" folder and tap on YouTubeAutomation. The program will open as it is intended.

# Authentication (Method 1)
If you are experienced in python or have experience with google drive + YouTube data v3 API, then go for this method =

Add Google drive API OAuth2.0 file as "credentials.json" and YouTube data v3 API client secret as "client_secret.json" in the main folder.

You must rename the file according to the upper instruction. Renaming it will not chance anything in the file.
# Folder ID
(Source_File_ID) and (Destination_Folder_ID) should be changed with your desired folder id.

# Getting GDrive API Oauth Client Secret 
Go to your google cloud console and enable Google Drive API, then follow the official google documentation - https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid

Make Sure add "http://localhost:8080" as authorised JavaScript Origins and "http://localhost:8080/oauth2callback" + "http://localhost:8080/" as authorised redirect urls.

# Getting YouTube Data V3 API client secret
Go to your google cloud console and enable YouTuve Data v3 API, then follow the official google documentation - https://developers.google.com/youtube/v3/guides/auth/installed-apps#uwp

Make Sure add "http://localhost:8081" as authorised JavaScript Origins and "http://localhost:8081/oauth2callback" + "http://localhost:8081/" as authorised redirect urls.


