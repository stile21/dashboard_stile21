import streamlit as st
import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

UPLOAD_FOLDER = "uploaded_files"  # cartella locale temporanea
DRIVE_FOLDER_NAME = "StreamlitAppFiles"  # Nome cartella su Drive (puoi cambiarlo)

# ➡ Autenticazione Google
def authenticate_drive():
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    return GoogleDrive(gauth)

# ➡ Crea cartella su Drive (se non esiste)
def get_or_create_drive_folder(drive, folder_name):
    folders = drive.ListFile({'q': f"title='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
    if folders:
        return folders[0]['id']
    folder_metadata = {'title': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
    folder = drive.CreateFile(folder_metadata)
    folder.Upload()
    return folder['id']

# ➡ Upload file su Google Drive
def upload_file_to_drive(file_path, filename, drive, folder_id):
    file_drive = drive.CreateFile({'title': filename, 'parents': [{'id': folder_id}]})
    file_drive.SetContentFile(file_path)
    file_drive.Upload()

# ➡ Scarica tutti i file dalla cartella Drive
def download_files_from_drive(drive, folder_id, destination_folder):
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()
    os.makedirs(destination_folder, exist_ok=True)
    for file_drive in file_list:
        file_path = os.path.join(destination_folder, file_drive['title'])
        file_drive.GetContentFile(file_path)

# ➡ APP STREAMLIT
def main():
    st.title("📂 Gestione File Persistenti con Google Drive")

    # Autenticazione + scarica tutti i file all’avvio
    drive = authenticate_drive()
    folder_id = get_or_create_drive_folder(drive, DRIVE_FOLDER_NAME)
    download_files_from_drive(drive, folder_id, UPLOAD_FOLDER)
    st.success("✅ File scaricati da Google Drive!")

    # File uploader Streamlit
    uploaded_files = st.file_uploader("Carica file Excel o Immagini", accept_multiple_files=True)
    if uploaded_files:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        for uploaded_file in uploaded_files:
            file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            upload_file_to_drive(file_path, uploaded_file.name, drive, folder_id)
            st.success(f"✅ {uploaded_file.name} caricato su Google Drive!")

    # Mostra elenco file locali
    if st.button("📋 Mostra file locali"):
        files = os.listdir(UPLOAD_FOLDER)
        if files:
            st.write("File presenti localmente:")
            st.write(files)
        else:
            st.write("❌ Nessun file trovato.")

if __name__ == "__main__":
    main()