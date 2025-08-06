import os
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import streamlit as st


def get_drive_service():
    creds_dict = st.secrets["google_service_account"]
    creds = service_account.Credentials.from_service_account_info(creds_dict)
    return build("drive", "v3", credentials=creds)


def get_or_create_drive_folder(service, folder_name):
    # Verifica se la cartella esiste
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    files = results.get("files", [])

    if files:
        return files[0]["id"]

    # Altrimenti crea la cartella
    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder"
    }
    file = service.files().create(body=file_metadata, fields="id").execute()
    return file.get("id")


def upload_file_to_drive(file_path, service, folder_id):
    file_name = os.path.basename(file_path)
    file_metadata = {
        "name": file_name,
        "parents": [folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    service.files().create(body=file_metadata, media_body=media, fields="id").execute()


def download_all_from_drive(service, folder_id, local_dir):
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)

    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])

    for file in files:
        file_id = file["id"]
        file_name = file["name"]
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(os.path.join(local_dir, file_name), "wb")
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()