import json
import bcrypt

FILE_UTENTI = "utenti.json"

def carica_utenti():
    try:
        with open(FILE_UTENTI, "r") as f:
            return json.load(f)
    except:
        return {}

def salva_utenti(utenti):
    with open(FILE_UTENTI, "w") as f:
        json.dump(utenti, f, indent=4)

def verifica_password(password_inserita, password_hashata):
    return bcrypt.checkpw(password_inserita.encode(), password_hashata.encode())

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()