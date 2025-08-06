from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os

def connect_drive():
    gauth = GoogleAuth()
    
    # Configura PyDrive per usare la chiave del service account
    gauth.settings['client_config_backend'] = 'service'
    gauth.settings['service_config'] = {
        "client_service_email": "streamlit-bot@dashboardstile21.iam.gserviceaccount.com",
        "client_user_email": "",
        "private_key_file": "service_account.json"
    }

    gauth.ServiceAuth()
    return GoogleDrive(gauth)

def get_or_create_drive_folder(drive, folder_name):
    file_list = drive.ListFile({
        'q': f"title='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    }).GetList()

    if file_list:
        return file_list[0]['id']
    else:
        folder_metadata = {
            'title': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = drive.CreateFile(folder_metadata)
        folder.Upload()
        return folder['id']

def upload_file_to_drive(local_path, drive, folder_id):
    file_drive = drive.CreateFile({
        'title': os.path.basename(local_path),
        'parents': [{'id': folder_id}]
    })
    file_drive.SetContentFile(local_path)
    file_drive.Upload()

def download_all_from_drive(drive, folder_id, local_dir):
    os.makedirs(local_dir, exist_ok=True)
    file_list = drive.ListFile({
        'q': f"'{folder_id}' in parents and trashed=false"
    }).GetList()

    for file in file_list:
        file_path = os.path.join(local_dir, file['title'])
        file.GetContentFile(file_path)