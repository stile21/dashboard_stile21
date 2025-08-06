import os
import streamlit as st
import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build


# ============================
# CREA ISTANZA DI GOOGLE DRIVE
# ============================
def get_drive_service():
    creds_dict = st.secrets["google_service_account"]

    # Converte correttamente la private_key
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/drive"])
    service = build("drive", "v3", credentials=creds)
    return service


# ==========================================================
# CREA O TROVA UNA CARTELLA NEL DRIVE CON NOME SPECIFICATO
# ==========================================================
def get_or_create_drive_folder(service, folder_name):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    items = results.get("files", [])

    if items:
        return items[0]["id"]  # folder già esistente

    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder"
    }
    file = service.files().create(body=file_metadata, fields="id").execute()
    return file.get("id")


# ========================
# UPLOAD FILE IN UNA CARTELLA
# ========================
def upload_file_to_drive(service, folder_id, file_path):
    from googleapiclient.http import MediaFileUpload

    file_metadata = {
        "name": os.path.basename(file_path),
        "parents": [folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return file.get("id")
def download_all_from_drive(service, folder_id, local_folder="dati_salvati"):