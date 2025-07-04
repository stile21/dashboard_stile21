import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
from fpdf import FPDF
from datetime import datetime
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

# 📅 Riquadro Date Assenti
st.subheader("📅 Date assenti")

import holidays
italian_holidays = holidays.IT()

# Date iniziali specifiche per ogni negozio
date_iniziali = {
    "Velletri (2063)": pd.to_datetime("2022-06-22"),
    "Ariccia (2254)": pd.to_datetime("2023-12-23"),
    "Terracina (2339)": pd.to_datetime("2025-05-18"),
}

note_file = "dati_note_mancanti.xlsx"

# Carica note salvate se esistono
if os.path.exists(note_file):
    df_note = pd.read_excel(note_file)
else:
    df_note = pd.DataFrame(columns=["Negozio", "Data", "Note"])

# Trova date mancanti giornaliere per ogni negozio
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

# Merge con eventuali note salvate
df_mancanti["Data"] = pd.to_datetime(df_mancanti["Data"])
df_note["Data"] = pd.to_datetime(df_note["Data"])
df_merge = pd.merge(df_mancanti, df_note, on=["Negozio", "Data"], how="left", suffixes=("", "_y"))
df_merge["Note"] = df_merge["Note_y"].combine_first(df_merge["Note"])
df_merge = df_merge[["Negozio", "Data", "Note"]]

# Raggruppa per negozio con colore festivo
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

st.subheader("📊 Risultati filtrati")
df_ordinato = filtered_df.sort_values(by="Data", ascending=False).reset_index(drop=True)
df_ordinato.index = df_ordinato.index + 1  # per iniziare da 1
df_ordinato.index.name = "N."
st.dataframe(df_ordinato, use_container_width=True)

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

# Confronto tra negozi
st.markdown("---")
st.subheader("📍 Confronto tra negozi")

# Imposta negozi predefiniti diversi
negozi_unici = negozi[:3] if len(negozi) >= 3 else negozi + [""] * (3 - len(negozi))

col1, col2, col3 = st.columns(3)
with col1:
    negozio1 = st.selectbox("Negozio 1", negozi, index=negozi.index(negozi_unici[0]), key="negozio1")
with col2:
    negozio2 = st.selectbox("Negozio 2", negozi, index=negozi.index(negozi_unici[1]), key="negozio2")
with col3:
    negozio3 = st.selectbox("Negozio 3", negozi, index=negozi.index(negozi_unici[2]), key="negozio3")

colonne_confronto = ["Vendite (incl. shopper senza gift)", "Resi", "Gift Card", "Shopper"]

df1 = df[(df["Negozio"] == negozio1) & (df["Data"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])))]
df2 = df[(df["Negozio"] == negozio2) & (df["Data"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])))]
df3 = df[(df["Negozio"] == negozio3) & (df["Data"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])))]

for col in colonne_confronto:
    s1 = df1[col].sum()
    s2 = df2[col].sum()
    s3 = df3[col].sum()
    s1_fmt = f"{s1:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    s2_fmt = f"{s2:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    s3_fmt = f"{s3:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    st.write(f"### {col}")
    st.write(f"{negozio1}: **{s1_fmt} EUR**, {negozio2}: **{s2_fmt} EUR**, {negozio3}: **{s3_fmt} EUR**")

    fig = px.bar(x=[negozio1, negozio2, negozio3], y=[s1, s2, s3], title=f"{col} - Confronto tra negozi")
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

# ✅ Esporta PDF – Confronto tra Negozi (con fpdf2)
if st.button("📤 Esporta PDF – Confronto tra Negozi"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(200, 10, txt="Confronto tra Negozi", ln=True, align="C")
    pdf.set_font("Helvetica", size=12)
    pdf.cell(200, 10, txt=f"Periodo: {date_range[0]} - {date_range[1]}", ln=True, align="C")
    pdf.ln(10)

    for col in colonne_confronto:
        s1 = df1[col].sum()
        s2 = df2[col].sum()
        s3 = df3[col].sum()
        s1_fmt = f"{s1:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        s2_fmt = f"{s2:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        s3_fmt = f"{s3:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(200, 10, txt=col, ln=True)
        pdf.set_font("Helvetica", size=12)
        pdf.cell(200, 10, txt=f"{negozio1}: {s1_fmt} EUR", ln=True)
        pdf.cell(200, 10, txt=f"{negozio2}: {s2_fmt} EUR", ln=True)
        pdf.cell(200, 10, txt=f"{negozio3}: {s3_fmt} EUR", ln=True)
        pdf.ln(5)

    pdf_output = pdf.output(dest="S")
    b64 = base64.b64encode(pdf_output).decode()
    st.markdown(
        f"""<a href="data:application/pdf;base64,{b64}" download="confronto_negozi.pdf">
            <button style='padding:10px 20px;background-color:#4CAF50;color:white;border:none;border-radius:5px;'>
            📄 Scarica PDF Confronto Negozi
            </button>
        </a>""",
        unsafe_allow_html=True
    )


# ✅ Esporta PDF – Confronto tra Periodi (con indentazione corretta)
if st.button("📤 Esporta PDF – Confronto tra Periodi"):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    if os.path.exists("logo_terranova_resized.jpg"):
        pdf.image("logo_terranova_resized.jpg", x=10, y=8, w=50)
        pdf.ln(25)

    pdf.set_font("Helvetica", 'B', 16)
    titolo = f"Confronto tra Periodi – {negozio_conf}".replace("–", "-")
    pdf.cell(0, 10, titolo, ln=True, align="C")
    pdf.set_font("Helvetica", '', 12)
    pdf.cell(0, 10, f"Periodo 1: {p1[0].strftime('%d/%m/%Y')} - {p1[1].strftime('%d/%m/%Y')}", ln=True, align="C")
    pdf.cell(0, 10, f"Periodo 2: {p2[0].strftime('%d/%m/%Y')} - {p2[1].strftime('%d/%m/%Y')}", ln=True, align="C")
    pdf.cell(0, 10, f"Data di esportazione: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(10)

    for col in colonne:
        s1 = d1[col].sum()
        s2 = d2[col].sum()
        diff = s2 - s1
        perc = (diff / s1 * 100) if s1 != 0 else 0

        s1_fmt = f"{s1:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        s2_fmt = f"{s2:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        diff_fmt = f"{diff:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        perc_fmt = f"{perc:.2f}".replace(".", ",")

        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 10, col, ln=True)
        pdf.set_font("Helvetica", '', 11)
        pdf.cell(0, 8, f"Periodo 1: {s1_fmt} EUR", ln=True)
        pdf.cell(0, 8, f"Periodo 2: {s2_fmt} EUR", ln=True)
        pdf.cell(0, 8, f"Differenza: {diff_fmt} EUR ({perc_fmt}%)", ln=True)
        pdf.ln(4)

    pdf_output = pdf.output(dest="S")
    b64 = base64.b64encode(pdf_output).decode()
    st.markdown(
        f"""<a href="data:application/pdf;base64,{b64}" download="confronto_periodi.pdf">
            <button style='padding:10px 20px;background-color:#4CAF50;color:white;border:none;border-radius:5px;'>
            📄 Scarica PDF Confronto Periodi
            </button>
        </a>""",
        unsafe_allow_html=True
    )