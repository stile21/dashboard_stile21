
import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.client import OAuth2WebServerFlow

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import os

def connect_drive():
    gauth = GoogleAuth()

    # Percorso per salvare il token
    token_dir = "/mount/tmp" if os.environ.get("STREAMLIT_CLOUD") else "."
    token_file = os.path.join(token_dir, "token_drive.json")

    gauth.LoadCredentialsFile(token_file)

    if gauth.credentials is None:
        gauth.LocalWebserverAuth()  # Primo accesso
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()

    gauth.SaveCredentialsFile(token_file)

    return GoogleDrive(gauth)
    

def get_or_create_drive_folder(drive, folder_name="StreamlitAppFiles"):
    folders = drive.ListFile({
        'q': f"title='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    }).GetList()
    if folders:
        return folders[0]['id']
    folder_metadata = {'title': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
    folder = drive.CreateFile(folder_metadata)
    folder.Upload()
    return folder['id']

def upload_file_to_drive(drive, folder_id, file_path):
    filename = os.path.basename(file_path)
    file_drive = drive.CreateFile({'title': filename, 'parents': [{'id': folder_id}]})
    file_drive.SetContentFile(file_path)
    file_drive.Upload()

def download_all_from_drive(drive, folder_id, local_folder="dati_salvati"):
    os.makedirs(local_folder, exist_ok=True)
    file_list = drive.ListFile({
        'q': f"'{folder_id}' in parents and trashed=false"
    }).GetList()
    for f in file_list:
        f.GetContentFile(os.path.join(local_folder, f['title']))
