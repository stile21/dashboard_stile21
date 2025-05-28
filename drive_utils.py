from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import os
import streamlit as st

# Autenticazione con caching del token
def connect_drive():
    gauth = GoogleAuth()

    # Usa client_id/client_secret da secrets TOML
    gauth.settings['client_config_backend'] = 'settings'
    gauth.settings['client_config'] = {
        "client_id": st.secrets["google_drive"]["client_id"],
        "client_secret": st.secrets["google_drive"]["client_secret"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
    }

    # Percorso di salvataggio token (supportato da Streamlit Cloud)
    token_path = "/mount/tmp/token_drive.json" if "STREAMLIT_CLOUD" in os.environ else "token_drive.json"
    gauth.LoadCredentialsFile(token_path)

    if gauth.credentials is None:
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()

    gauth.SaveCredentialsFile(token_path)
    return GoogleDrive(gauth)

# Ottieni o crea la cartella "dati_salvati" su Drive
def get_or_create_drive_folder(drive, folder_name="dati_salvati"):
    file_list = drive.ListFile({
        'q': "title='%s' and mimeType='application/vnd.google-apps.folder' and trashed=false" % folder_name
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

# Carica un file su Google Drive dentro la cartella
def upload_file_to_drive(drive, folder_id, file_path):
    file_name = os.path.basename(file_path)
    gfile = drive.CreateFile({'title': file_name, 'parents': [{'id': folder_id}]})
    gfile.SetContentFile(file_path)
    gfile.Upload()

# Scarica tutti i file da Drive nella cartella locale
def download_all_from_drive(drive, folder_id, local_folder):
    os.makedirs(local_folder, exist_ok=True)
    file_list = drive.ListFile({
        'q': f"'{folder_id}' in parents and trashed=false"
    }).GetList()

    for f in file_list:
        local_path = os.path.join(local_folder, f['title'])
        if not os.path.exists(local_path):  # evita sovrascritture inutili
            f.GetContentFile(local_path)
