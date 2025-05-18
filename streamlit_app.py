import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
from fpdf import FPDF
import base64
from login_utils import carica_utenti, salva_utenti, verifica_password, hash_password
# Layout + Footer
st.set_page_config(page_title="Dashboard Incassi Stile21", layout="wide")
st.markdown("""
    <style>
        #footer-text {
            position: fixed;
            bottom: 0;
            width: 100%;
            background-color: #f0f2f6;
            padding: 10px;
            text-align: center;
            font-weight: bold;
            color: #333;
            border-top: 1px solid #ccc;
        }
    </style>
    <div id="footer-text">📊 Dashboard Incassi Stile21</div>
""", unsafe_allow_html=True)

# Login
with st.sidebar:
    st.header("🔐 Login")

    if "login_ok" not in st.session_state:
        st.session_state.login_ok = False
        st.session_state.username = ""

    if not st.session_state.login_ok:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if username and password:
            utenti = carica_utenti()
            if username in utenti and verifica_password(password, utenti[username]):
                st.session_state.login_ok = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Credenziali non valide.")
    else:
        st.success(f"👋 Benvenuto, {st.session_state.username}")
        if st.button("🔓 Logout"):
            st.session_state.login_ok = False
            st.session_state.username = ""
            st.rerun()
if not st.session_state.login_ok:
    st.stop()

username = st.session_state.username

# Menu modifica utenti
if username == "admin":
    st.markdown("---")
    st.subheader("⚙️ Gestione Utenti (solo admin)")

    utenti = carica_utenti()
    st.write("👥 Utenti esistenti:")
    st.table(list(utenti.keys()))

    with st.expander("➕ Aggiungi o modifica utente"):
        with st.form("form_nuovo_utente"):
            nuovo_user = st.text_input("Nuovo username")
            nuova_pass = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Salva utente")
            if submitted:
                if nuovo_user and nuova_pass:
                    utenti[nuovo_user] = hash_password(nuova_pass)
                    salva_utenti(utenti)
                    st.success(f"Utente '{nuovo_user}' salvato.")
                else:
                    st.warning("Inserisci username e password.")

    with st.expander("🗑️ Rimuovi utente"):
        user_da_rimuovere = st.selectbox("Scegli utente", [u for u in utenti if u != "admin"])
        if st.button("Elimina utente"):
            if user_da_rimuovere in utenti:
                del utenti[user_da_rimuovere]
                salva_utenti(utenti)
                st.success(f"Utente '{user_da_rimuovere}' eliminato.")

# Upload
uploaded_file = st.file_uploader("Carica il file Excel riepilogativo", type=["xlsx"])

@st.cache_data
def load_file(file):
    xls = pd.ExcelFile(file)
    df = pd.read_excel(xls, "Dettaglio Giornaliero")
    df["Data"] = pd.to_datetime(df["Data"])
    df["Negozio"] = df["Negozio"].replace({
    2063: "Velletri (2063)",
    "2063": "Velletri (2063)",
    2254: "Ariccia (2254)",
    "2254": "Ariccia (2254)",
    2339: "Terracina (2339)",
    "2339": "Terracina (2339)"
})
    return df

# Cartella dati salvati
if not os.path.exists("dati_salvati"):
    os.makedirs("dati_salvati")

if uploaded_file:
    nome_file = uploaded_file.name
    with open(os.path.join("dati_salvati", nome_file), "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success(f"File salvato come {nome_file}")

# Carica tutti i dati salvati
all_dfs = []
for file in os.listdir("dati_salvati"):
    if file.endswith(".xlsx"):
        try:
            df = pd.read_excel(os.path.join("dati_salvati", file), sheet_name="Dettaglio Giornaliero")
            df["Data"] = pd.to_datetime(df["Data"])
            df["Negozio"] = df["Negozio"].replace({
    2063: "Velletri (2063)",
    2254: "Ariccia (2254)",
    2339: "Terracina (2339)"
})
            all_dfs.append(df)
        except:
            pass

if not all_dfs:
    st.info("Carica almeno un file Excel per iniziare.")
    st.stop()

# Filtri
df = pd.concat(all_dfs, ignore_index=True).drop_duplicates()
negozi = df["Negozio"].unique().tolist()
st.sidebar.header("📆 Filtri")
negozio_sel = st.sidebar.selectbox("Negozio:", ["Tutti"] + negozi)
min_date, max_date = df["Data"].min(), df["Data"].max()
date_range = st.sidebar.date_input("Intervallo di date:", [min_date, max_date])

filtered_df = df.copy()
if negozio_sel != "Tutti":
    filtered_df = filtered_df[filtered_df["Negozio"] == negozio_sel]
filtered_df = filtered_df[(filtered_df["Data"] >= pd.to_datetime(date_range[0])) & (filtered_df["Data"] <= pd.to_datetime(date_range[1]))]

st.subheader("📊 Risultati filtrati")
st.dataframe(filtered_df.sort_values(by="Data", ascending=False), use_container_width=True)

# Totali
st.markdown("---")
st.subheader("📋 Totali riepilogativi")
colonne = ["Vendite (incl. shopper senza gift)", "Resi", "Gift Card", "Shopper", "Totali Generali (incl. resi, shopper, gift)"]
totali = filtered_df[colonne].sum().round(2)
for k in colonne:
    if k == "Vendite (incl. shopper senza gift)":
        val = totali[k]
        st.markdown(f"<div style='background-color:#fff4c2;padding:10px'><b>{k}</b>: {val:,.2f} EUR</div>".replace(",", "X").replace(".", ",").replace("X", "."), unsafe_allow_html=True)
    else:
        val = totali.get(k, 0.0)
        st.write(f"**{k}**: {val:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", "."))

# Confronti
st.markdown("---")
st.subheader("📍 Confronto tra negozi")
col1, col2 = st.columns(2)
with col1:
    negozio1 = st.selectbox("Negozio 1", negozi, key="negozio1")
with col2:
    negozio2 = st.selectbox("Negozio 2", negozi, key="negozio2")

colonne_confronto = ["Vendite (incl. shopper senza gift)", "Resi", "Gift Card", "Shopper"]
df1 = df[(df["Negozio"] == negozio1) & (df["Data"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])))]
df2 = df[(df["Negozio"] == negozio2) & (df["Data"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])))]
for col in colonne_confronto:
    s1 = df1[col].sum()
    s2 = df2[col].sum()
    s1_fmt = f"{s1:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    s2_fmt = f"{s2:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    st.write(f"### {col}")
    st.write(f"{negozio1}: **{s1_fmt} EUR**, {negozio2}: **{s2_fmt} EUR**")
    fig = px.bar(x=[negozio1, negozio2], y=[s1, s2], title=f"{col} - Confronto tra negozi")
    st.plotly_chart(fig, use_container_width=True)

# Confronto tra periodi
st.markdown("---")
st.subheader("📍 Confronto tra periodi")
negozio_conf = st.selectbox("Negozio per confronto:", negozi, key="negozio_confronto")
p1 = st.date_input("Periodo 1", [min_date, max_date], key="p1")
p2 = st.date_input("Periodo 2", [min_date, max_date], key="p2")

if len(p1) == 2 and len(p2) == 2:
    d1 = df[(df["Negozio"] == negozio_conf) & (df["Data"].between(pd.to_datetime(p1[0]), pd.to_datetime(p1[1])))]
    d2 = df[(df["Negozio"] == negozio_conf) & (df["Data"].between(pd.to_datetime(p2[0]), pd.to_datetime(p2[1])))]
    for col in colonne:
        s1 = d1[col].sum()
        s2 = d2[col].sum()
        s1_fmt = f"{s1:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        s2_fmt = f"{s2:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        st.write(f"### {col}")
        st.write(f"Periodo 1: **{s1_fmt} EUR**, Periodo 2: **{s2_fmt} EUR**")
        diff = s2 - s1
        perc = (diff / s1 * 100) if s1 != 0 else 0
        diff_fmt = f"{diff:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        perc_fmt = f"{perc:.2f}".replace(".", ",")
        colore = 'green' if diff >= 0 else 'red'
        st.markdown(f"<span style='color:{colore}'>Differenza: <strong>{diff_fmt} EUR</strong> ({perc_fmt}%)</span>", unsafe_allow_html=True)
        fig = px.bar(x=["Periodo 1", "Periodo 2"], y=[s1, s2], title=f"{col} - {negozio_conf}")
        st.plotly_chart(fig, use_container_width=True)

# PDF export
st.markdown("---")
st.subheader("📤 Esporta in PDF")
pdf = FPDF()
pdf.add_page()
if os.path.exists("logo_terranova_resized.jpg"):
    pdf.image("logo_terranova_resized.jpg", x=10, y=8, w=60)
pdf.set_font("Arial", size=12)
pdf.ln(30)
pdf.cell(200, 10, txt="Report Incassi Stile21", ln=True, align="C")
pdf.cell(200, 10, txt=f"Periodo: {date_range[0]} - {date_range[1]}", ln=True, align="C")
pdf.cell(200, 10, txt=f"Negozio: {negozio_sel}", ln=True, align="C")
pdf.ln(10)
for k in colonne:
    val = f"{totali[k]:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    pdf.cell(200, 10, txt=f"{k}: {val} EUR", ln=True)
pdf_output = pdf.output(dest="S").encode("latin1")
b64_pdf = base64.b64encode(pdf_output).decode()
href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="riepilogo_incassi.pdf">📄 Scarica PDF</a>'
st.markdown(href, unsafe_allow_html=True)
