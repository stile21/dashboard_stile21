import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
from fpdf import FPDF
import base64
import holidays
import streamlit.components.v1 as components

from login_utils import carica_utenti, salva_utenti, verifica_password, hash_password
from drive_service import get_drive_service, get_or_create_drive_folder, upload_file_to_drive, download_all_from_drive

# ✅ Deve essere il primo comando Streamlit
st.set_page_config(page_title="Dashboard Incassi Stile21", layout="wide")

# -----------------------
# Costanti metriche
# -----------------------
METRICHE_NEGOZI = [
    "Vendite (incl. shopper senza gift)",
    "Resi",
    "Gift Card",
    "Shopper",
]
METRICHE_PERIODI = METRICHE_NEGOZI + [
    "Totali Generali (incl. resi, shopper, gift)"
]

# -----------------------
# Utilità: scroll fluido verso una sezione
# -----------------------
def scroll_to(section_id: str):
    components.html(
        f"""
        <script>
        const el = window.parent.document.getElementById("{section_id}");
        if (el) {{
            el.scrollIntoView({{behavior: 'smooth', block: 'start'}});
        }}
        </script>
        """,
        height=0,
    )

# -----------------------
# Drive + Footer
# -----------------------
service = get_drive_service()
folder_id = get_or_create_drive_folder(service, "dati_salvati")
download_all_from_drive(service, folder_id, "dati_salvati")

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
            z-index: 9999;
        }
    </style>
    <div id="footer-text">📊 Dashboard Incassi Stile21</div>
""", unsafe_allow_html=True)

# -----------------------
# LOGIN
# -----------------------
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

import base64

# -----------------------
# HEADER (solo dopo login)
# -----------------------
col_logo, col_btns = st.columns([1, 3])  # più spazio ai pulsanti

with col_logo:
    if os.path.exists("logo.png"):
        with open("logo.png", "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <div style="margin-left:30px;">
                <img src="data:image/png;base64,{logo_base64}" width="180">
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.warning("⚠️ Logo non trovato (logo.png)")

with col_btns:
    st.markdown(
        """
        <div style="display: flex; justify-content: flex-end; gap: 30px; align-items: center; height:100%;">
            <a href="#confronto-negozi">
                <button style="background-color:#4DA6FF; color:white; border:none; padding:15px 30px; 
                               border-radius:12px; cursor:pointer; font-size:16px; min-width:220px;">
                    📊 Confronto tra negozi
                </button>
            </a>
            <a href="#confronto-periodi">
                <button style="background-color:#4DA6FF; color:white; border:none; padding:15px 30px; 
                               border-radius:12px; cursor:pointer; font-size:16px; min-width:220px;">
                    ⏳ Confronto tra periodi stesso negozio
                </button>
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )

# linea divisoria
st.markdown("---")

# -----------------------
# Gestione utenti (solo admin)
# -----------------------
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

# -----------------------
# Upload file (solo admin)
# -----------------------
uploaded_file = None
if username == "admin":
    uploaded_file = st.file_uploader("Carica il file Excel riepilogativo", type=["xlsx"])
    if uploaded_file:
        nome_file = uploaded_file.name
        local_path = os.path.join("dati_salvati", nome_file)
        with open(local_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        upload_file_to_drive(service, folder_id, local_path)
        st.success(f"✅ File salvato localmente e su Google Drive: {nome_file}")

# -----------------------
# Caricamento dati
# -----------------------
if not os.path.exists("dati_salvati"):
    os.makedirs("dati_salvati")

all_dfs = []
for file in os.listdir("dati_salvati"):
    if file.endswith(".xlsx"):
        try:
            df_tmp = pd.read_excel(os.path.join("dati_salvati", file), sheet_name="Dettaglio Giornaliero")
            df_tmp["Data"] = pd.to_datetime(df_tmp["Data"])
            df_tmp["Negozio"] = df_tmp["Negozio"].replace({
                2063: "Velletri (2063)",
                "2063": "Velletri (2063)",
                2254: "Ariccia (2254)",
                "2254": "Ariccia (2254)",
                2339: "Terracina (2339)",
                "2339": "Terracina (2339)",
            })
            all_dfs.append(df_tmp)
        except Exception as e:
            st.warning(f"⚠️ Non riesco a leggere {file}: {e}")

if not all_dfs:
    st.info("Carica almeno un file Excel per iniziare.")
    st.stop()

df = pd.concat(all_dfs, ignore_index=True).drop_duplicates()
negozi = df["Negozio"].unique().tolist()

# -----------------------
# Filtri
# -----------------------
st.sidebar.header("📆 Filtri")
min_date, max_date = df["Data"].min(), df["Data"].max()
negozio_sel = st.sidebar.selectbox("Negozio:", ["Tutti"] + negozi)
date_range = st.sidebar.date_input("Intervallo di date:", [min_date, max_date], format="DD/MM/YYYY")

filtered_df = df.copy()
if negozio_sel != "Tutti":
    filtered_df = filtered_df[filtered_df["Negozio"] == negozio_sel]
filtered_df = filtered_df[(filtered_df["Data"] >= pd.to_datetime(date_range[0])) &
                          (filtered_df["Data"] <= pd.to_datetime(date_range[1]))]

# -----------------------
# 📅 Date assenti (solo admin)
# -----------------------
if username == "admin":
    st.subheader("📅 Date assenti (solo admin)")
    italian_holidays = holidays.IT()
    date_iniziali = {
        "Velletri (2063)": pd.to_datetime("2022-06-22"),
        "Ariccia (2254)": pd.to_datetime("2023-12-23"),
        "Terracina (2339)": pd.to_datetime("2025-05-18"),
    }

    note_file = "dati_note_mancanti.xlsx"
    if os.path.exists(note_file):
        df_note = pd.read_excel(note_file)
    else:
        df_note = pd.DataFrame(columns=["Negozio", "Data", "Note"])

    df_mancanti = pd.DataFrame()
    negozi_presenti = df["Negozio"].unique()
    for negozio in negozi_presenti:
        if negozio not in date_iniziali:
            continue
        start_date = date_iniziali[negozio]
        end_date = df[df["Negozio"] == negozio]["Data"].max()
        tutte_le_date = pd.date_range(start=start_date, end=end_date, freq="D")
        date_presenti = df[df["Negozio"] == negozio]["Data"].dt.normalize().unique()
        date_mancanti = sorted(set(tutte_le_date.date) - set(pd.to_datetime(date_presenti).date))
        for data in date_mancanti:
            df_mancanti = pd.concat([
                df_mancanti,
                pd.DataFrame([{"Negozio": negozio, "Data": pd.to_datetime(data), "Note": ""}])
            ], ignore_index=True)

    df_mancanti["Data"] = pd.to_datetime(df_mancanti["Data"])
    df_note["Data"] = pd.to_datetime(df_note["Data"])
    df_merge = pd.merge(df_mancanti, df_note, on=["Negozio", "Data"], how="left", suffixes=("", "_y"))
    df_merge["Note"] = df_merge["Note_y"].combine_first(df_merge["Note"])
    df_merge = df_merge[["Negozio", "Data", "Note"]]

    for negozio in sorted(df_merge["Negozio"].unique()):
        with st.expander(f"📂 {negozio} ({(df_merge['Negozio'] == negozio).sum()} date mancanti)"):
            sotto_df = df_merge[df_merge["Negozio"] == negozio].sort_values("Data").copy()
            sotto_df["Festività"] = sotto_df["Data"].apply(lambda d: italian_holidays.get(d.date()) or "")
            sotto_df_reset = sotto_df.reset_index(drop=True)

            st.write("🟥 Le festività sono evidenziate nella colonna 'Festività'")
            sotto_df_editato = st.data_editor(
                sotto_df_reset,
                column_config={
                    "Note": st.column_config.TextColumn("Note", help="Aggiungi una nota"),
                    "Data": st.column_config.DateColumn("Data"),
                    "Festività": st.column_config.TextColumn("Festività", help="Giorno festivo riconosciuto in Italia"),
                },
                column_order=["Data", "Festività", "Note"],
                num_rows="dynamic",
                use_container_width=True,
                key=f"editor_{negozio}"
            )
            df_merge.loc[sotto_df.index, "Note"] = sotto_df_editato["Note"].values

    if st.button("💾 Salva note mancanti"):
        df_merge.to_excel(note_file, index=False)
        st.success("✅ Note salvate correttamente.")

# -----------------------
# ◀️ Anchor sezione: Confronto tra negozi
# -----------------------
#st.markdown("<div id='confronto-negozi'></div>", unsafe_allow_html=True)
#st.markdown("## 📊 Confronto tra negozi")
#st.write("")

# --- Confronto tra negozi
st.markdown("<div id='confronto-negozi'></div>", unsafe_allow_html=True)

col_titolo, col_btn = st.columns([4, 1])
with col_titolo:
    st.markdown("## 📊 Confronto tra negozi")


# Imposta negozi predefiniti
negozi_unici = negozi[:3] if len(negozi) >= 3 else negozi + [""] * (3 - len(negozi))

col1, col2, col3 = st.columns(3)
with col1:
    negozio1 = st.selectbox("Negozio 1", negozi, index=negozi.index(negozi_unici[0]) if negozi_unici[0] in negozi else 0, key="negozio1")
with col2:
    negozio2 = st.selectbox("Negozio 2", negozi, index=negozi.index(negozi_unici[1]) if negozi_unici[1] in negozi else 0, key="negozio2")
with col3:
    negozio3 = st.selectbox("Negozio 3", negozi, index=negozi.index(negozi_unici[2]) if negozi_unici[2] in negozi else 0, key="negozio3")

df1 = df[(df["Negozio"] == negozio1) & (df["Data"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])))]
df2 = df[(df["Negozio"] == negozio2) & (df["Data"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])))]
df3 = df[(df["Negozio"] == negozio3) & (df["Data"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])))]

with col_btn:
    if st.button("📤 Esporta PDF – Confronto tra Negozi"):
        pdf = FPDF()
        pdf.add_page()
        if os.path.exists("logo.png"):
            pdf.image("logo.png", x=80, y=10, w=50)
            pdf.ln(20)
        pdf.set_font("Helvetica", 'B', 18)
        pdf.set_text_color(0, 102, 204)
        pdf.cell(200, 12, txt="Confronto tra Negozi", ln=True, align="C")
        pdf.ln(5)
        pdf.set_font("Helvetica", size=12)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(200, 10, txt=f"Periodo: {date_range[0].strftime('%d/%m/%Y')} - {date_range[1].strftime('%d/%m/%Y')}", ln=True, align="C")
        pdf.cell(200, 10, txt=f"Data esportazione: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
        pdf.ln(10)
        for col in METRICHE_NEGOZI:
            s1, s2, s3 = df1[col].sum(), df2[col].sum(), df3[col].sum()
            s1_fmt = f"{s1:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            s2_fmt = f"{s2:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            s3_fmt = f"{s3:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            pdf.set_font("Helvetica", 'B', 14)
            pdf.set_text_color(255, 255, 255)
            pdf.set_fill_color(0, 102, 204)
            pdf.cell(200, 10, txt=col, ln=True, align="L", fill=True)
            pdf.set_font("Helvetica", size=12)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(200, 10, txt=f"{negozio1}: {s1_fmt} EUR", ln=True)
            pdf.cell(200, 10, txt=f"{negozio2}: {s2_fmt} EUR", ln=True)
            pdf.cell(200, 10, txt=f"{negozio3}: {s3_fmt} EUR", ln=True)
            pdf.ln(5)
        pdf_output = bytes(pdf.output(dest="S"))
        b64 = base64.b64encode(pdf_output).decode()
        st.markdown(
            f"""<a href="data:application/pdf;base64,{b64}" download="confronto_negozi.pdf">
                <button style='padding:10px 20px;background-color:#2196F3;color:white;border:none;border-radius:5px;'>
                📄 Scarica PDF Confronto Negozi
                </button>
            </a>""",
            unsafe_allow_html=True
        )

for col in METRICHE_NEGOZI:
    s1, s2, s3 = df1[col].sum(), df2[col].sum(), df3[col].sum()
    s1_fmt = f"{s1:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    s2_fmt = f"{s2:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    s3_fmt = f"{s3:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    st.write(f"### {col}")
    st.write(f"{negozio1}: **{s1_fmt} EUR**, {negozio2}: **{s2_fmt} EUR**, {negozio3}: **{s3_fmt} EUR**")
    fig = px.bar(x=[negozio1, negozio2, negozio3], y=[s1, s2, s3], title=f"{col} - Confronto tra negozi")
    st.plotly_chart(fig, use_container_width=True)

# -----------------------
# ◀️ Anchor sezione: Confronto tra periodi
# -----------------------
#st.markdown("<div id='confronto-periodi'></div>", unsafe_allow_html=True)
#st.markdown("## ⏳ Confronto tra periodi dello stesso negozio")
#st.write("")

# --- Confronto tra periodi
st.markdown("<div id='confronto-periodi'></div>", unsafe_allow_html=True)

# linea divisoria
st.markdown("---")

col_titolo_p, col_btn_p = st.columns([4, 1])
with col_titolo_p:
    st.markdown("## ⏳ Confronto tra periodi dello stesso negozio")

negozio_conf = st.selectbox("Negozio per confronto:", negozi, key="negozio_confronto")
p1 = st.date_input("Periodo 1", [min_date, max_date], key="p1", format="DD/MM/YYYY")
p2 = st.date_input("Periodo 2", [min_date, max_date], key="p2", format="DD/MM/YYYY")

with col_btn_p:
    if st.button("📤 Esporta PDF – Confronto tra Periodi"):
        pdf = FPDF()
        pdf.add_page()
        if os.path.exists("logo.png"):
            pdf.image("logo.png", x=80, y=10, w=50)
            pdf.ln(20)
        pdf.set_font("Helvetica", 'B', 18)
        pdf.set_text_color(0, 102, 204)
        pdf.cell(200, 12, txt=f"Confronto tra Periodi - {negozio_conf}", ln=True, align="C")
        pdf.ln(2)
        pdf.set_font("Helvetica", '', 12)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(200, 10, f"Periodo 1: {p1[0].strftime('%d/%m/%Y')} - {p1[1].strftime('%d/%m/%Y')}", ln=True, align="C")
        pdf.cell(200, 10, f"Periodo 2: {p2[0].strftime('%d/%m/%Y')} - {p2[1].strftime('%d/%m/%Y')}", ln=True, align="C")
        pdf.cell(200, 10, f"Data esportazione: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
        pdf.ln(10)

        d1 = df[(df["Negozio"] == negozio_conf) & (df["Data"].between(pd.to_datetime(p1[0]), pd.to_datetime(p1[1])))]
        d2 = df[(df["Negozio"] == negozio_conf) & (df["Data"].between(pd.to_datetime(p2[0]), pd.to_datetime(p2[1])))]

        for col in METRICHE_PERIODI:
            s1 = d1[col].sum()
            s2 = d2[col].sum()
            diff = s2 - s1
            perc = (diff / s1 * 100) if s1 != 0 else 0

            s1_fmt = f"{s1:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            s2_fmt = f"{s2:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            diff_fmt = f"{diff:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            perc_fmt = f"{perc:.2f}".replace(".", ",")

            pdf.set_font("Helvetica", 'B', 14)
            pdf.set_text_color(255, 255, 255)
            pdf.set_fill_color(0, 102, 204)
            pdf.cell(200, 10, txt=col, ln=True, fill=True)

            pdf.set_font("Helvetica", '', 12)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(200, 8, f"Periodo 1: {s1_fmt} EUR", ln=True)
            pdf.cell(200, 8, f"Periodo 2: {s2_fmt} EUR", ln=True)
            pdf.cell(200, 8, f"Differenza: {diff_fmt} EUR ({perc_fmt}%)", ln=True)
            pdf.ln(5)

        pdf_output = bytes(pdf.output(dest="S"))
        b64 = base64.b64encode(pdf_output).decode()
        st.markdown(
            f"""<a href="data:application/pdf;base64,{b64}" download="confronto_periodi.pdf">
                <button style='padding:10px 20px;background-color:#2196F3;color:white;border:none;border-radius:5px;'>
                📄 Scarica PDF Confronto Periodi
                </button>
            </a>""",
            unsafe_allow_html=True
        )

# Mostra i dati e i grafici sotto
if len(p1) == 2 and len(p2) == 2:
    d1 = df[(df["Negozio"] == negozio_conf) & (df["Data"].between(pd.to_datetime(p1[0]), pd.to_datetime(p1[1])))]
    d2 = df[(df["Negozio"] == negozio_conf) & (df["Data"].between(pd.to_datetime(p2[0]), pd.to_datetime(p2[1])))]

    for col in METRICHE_PERIODI:
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