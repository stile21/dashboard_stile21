
import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from oauth2client.client import OAuth2WebServerFlow

def connect_drive():
    import streamlit as st
    flow = OAuth2WebServerFlow(
        client_id=st.secrets["google_drive"]["client_id"],
        client_secret=st.secrets["google_drive"]["client_secret"],
        scope="https://www.googleapis.com/auth/drive",
        redirect_uri="urn:ietf:wg:oauth:2.0:oob"
    )
    auth_url = flow.step1_get_authorize_url()
    st.info("🔐 Autorizza l'accesso a Google Drive:")
    st.write(f"[Autorizza qui]({auth_url})")
    code = st.text_input("🔑 Incolla il codice di autorizzazione qui sotto:")
    if not code:
        st.stop()
    credentials = flow.step2_exchange(code)
    gauth = GoogleAuth()
    gauth.credentials = credentials
    drive = GoogleDrive(gauth)
    st.success("✅ Connessione a Google Drive riuscita.")
    return drive

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
