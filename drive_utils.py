import streamlit as st
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import os

# === AUTENTICAZIONE ===
def connect_drive():
    gauth = GoogleAuth()

    # Usa i secrets
    client_config = {
        "client_id": st.secrets["google_drive"]["client_id"],
        "client_secret": st.secrets["google_drive"]["client_secret"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        "client_type": "web"
    }

    os.makedirs("conf", exist_ok=True)
    with open("conf/client_secrets.json", "w") as f:
        import json
        json.dump({"installed": client_config}, f)

    gauth.LoadClientConfigFile("conf/client_secrets.json")

    # Questo è il file che caricherai su GitHub una volta autenticato in locale
    creds_path = "conf/mycreds.txt"

    try:
        gauth.LoadCredentialsFile(creds_path)
    except:
        gauth.LocalWebserverAuth()  # Solo in locale, non Streamlit Cloud
        gauth.SaveCredentialsFile(creds_path)

    if gauth.credentials is None:
        raise RuntimeError("⚠️ Autenticazione fallita. Esegui in locale per autenticare e salvare il token.")
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()

    return GoogleDrive(gauth)

    # Salvataggio token per login automatico
    gauth.LoadCredentialsFile("conf/mycreds.txt")
    if gauth.credentials is None:
        if os.environ.get("STREAMLIT_CLOUD") == "1":
            gauth.CommandLineAuth()  # Evita il problema del browser su Streamlit Cloud
        else:
            gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()
    gauth.SaveCredentialsFile("conf/mycreds.txt")

    return GoogleDrive(gauth)

# === CREA CARTELLA DATI (se non esiste) ===
def get_or_create_drive_folder(drive, folder_name="dati_salvati"):
    file_list = drive.ListFile({'q': "mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
    folder = next((f for f in file_list if f['title'] == folder_name), None)
    if folder:
        return folder['id']
    folder_metadata = {'title': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
    folder = drive.CreateFile(folder_metadata)
    folder.Upload()
    return folder['id']

# === CARICA UN FILE ===
def upload_file_to_drive(drive, folder_id, local_path):
    file_drive = drive.CreateFile({
        "title": os.path.basename(local_path),
        "parents": [{"id": folder_id}]
    })
    file_drive.SetContentFile(local_path)
    file_drive.Upload()

# === SCARICA TUTTI I FILE ===
def download_all_from_drive(drive, folder_id, local_folder="dati_salvati"):
    os.makedirs(local_folder, exist_ok=True)
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()
    for file_drive in file_list:
        dest_path = os.path.join(local_folder, file_drive['title'])
        if not os.path.exists(dest_path):
            file_drive.GetContentFile(dest_path)
