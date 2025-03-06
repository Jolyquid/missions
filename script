import os
import json
import gspread
import streamlit as st
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Fichier de clés API Google
GOOGLE_CREDENTIALS_FILE = "your_credentials.json"  # Remplace par ton fichier
SPREADSHEET_NAME = "Elite Dangerous Missions"

# Dossier des logs d'Elite Dangerous
log_dir = os.path.expanduser("~/Saved Games/Frontier Developments/Elite Dangerous")

def format_timestamp(timestamp):
    """Format '2025-03-06T14:23:45Z' → '2025-03-06 14:23:45'"""
    return timestamp.replace("T", " ").replace("Z", "")

def clean_mission_name(name):
    if not name:
        return "Unknown"
    name = name.replace("_", " ")  # Remplace les underscores par des espaces
    return name.removesuffix("Wing")  # Supprime " Wing" à la fin s'il est présent

def get_active_missions():
    active_missions = {}

    for file in sorted(os.listdir(log_dir)):
        if file.startswith("Journal") and file.endswith(".log"):
            with open(os.path.join(log_dir, file), "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        event = data.get("event")
                        mission_id = data.get("MissionID")

                        if event == "MissionAccepted" and mission_id:
                            active_missions[mission_id] = {
                                "MissionID": data.get("MissionID"),
                                "Genre": clean_mission_name(data.get("Name")),
                                "Sponsor": data.get("Faction", "Unknown"),
                                "Station": data.get("DestinationStation"),
                                "Title": data.get("LocalisedName"),
                                "Target": data.get("TargetFaction"),
                                "Destination": data.get("DestinationSystem"),
                                "KillCount": data.get("KillCount"),
                                "Payout": data.get("Reward", 0),
                                "Coop Mission": data.get("Wing"),
                                "Expiry": format_timestamp(data.get("Expiry", "No deadline"))  # Ajout du champ Expiry
                            }
                        
                        elif event in ["MissionCompleted", "MissionFailed", "MissionAbandoned", "MissionExpired"]:
                            if mission_id in active_missions:
                                del active_missions[mission_id]  # Supprime les missions terminées

                    except json.JSONDecodeError:
                        continue

    return list(active_missions.values())

# -------------------------------
# Interface avec Streamlit
# -------------------------------

st.set_page_config(layout="wide")  # Permet d'utiliser toute la largeur

st.title("🌐 Missions en cours - Elite Dangerous")

missions = get_active_missions()

if missions:
    st.write(f"📌 **{len(missions)} missions actives trouvées**")
    
    # Convertir en DataFrame
    df = pd.DataFrame(missions)

    # Calcul du temps restant en heures
    now = datetime.utcnow()
    
    def calculate_time_left(expiry):
        if expiry == "No deadline":
            return "N/A"
    
        try:
            expiry_time = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
            remaining_seconds = (expiry_time - datetime.utcnow()).total_seconds()
    
            if remaining_seconds < 0:
                return "Expiré"

            hours = int(remaining_seconds // 3600)
            minutes = int((remaining_seconds % 3600) // 60)
    
            return f"{hours}h{minutes:02d}"  # Format HHhMM
        
        except ValueError:
            return "Erreur format date"

    # Ajouter la colonne "Deadline"
    df["Deadline"] = df["Expiry"].apply(calculate_time_left)

    # Remplacer les valeurs None par "N/A"
    df["Deadline"] = df["Deadline"].apply(lambda x: x if x is not None else "N/A")
    
    # Supprimer la colonne "Expiry"
    if "Expiry" in df.columns:
        df.drop(columns=["Expiry"], inplace=True)
        df.reset_index(drop=True, inplace=True)


    # Afficher le tableau mis à jour
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.subheader("📊 Statistiques des missions")

    # Création de deux colonnes
    col1, col2 = st.columns(2)

    # Nombre de missions par faction
    with col1:
        missions_par_faction = df["Sponsor"].value_counts().reset_index()
        missions_par_faction.columns = ["Faction", "Nombre de missions"]
        st.write("### Nombre de missions par faction :")
        st.dataframe(missions_par_faction, use_container_width=True, hide_index=True)

    # Nombre total de kills par faction
    with col2:
        kills_par_faction = df.groupby("Sponsor")["KillCount"].sum().reset_index()
        kills_par_faction.columns = ["Faction", "Total Kills"]
        st.write("### Nombre total de kills par faction :")
        st.dataframe(kills_par_faction, use_container_width=True, hide_index=True)    
    
    

    # Export vers Google Sheets
    def upload_to_google_sheets(df):
        """Envoie les missions vers Google Sheets"""
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)

        sheet = client.open(SPREADSHEET_NAME).sheet1
        sheet.clear()

        headers = ["MissionID", "Genre", "Sponsor", "Title", "Target", "Destination", "KillCount", "Payout", "Deadline", "Coop Mission"]
        sheet.append_row(headers)

        for _, row in df.iterrows():
            sheet.append_row(row.tolist())

        st.success(f"📤 {len(df)} missions envoyées vers Google Sheets !")

    if st.button("📤 Exporter vers Google Sheets"):
        upload_to_google_sheets(df)

else:
    st.warning("Aucune mission active trouvée.")

st.caption("💡 Données extraites des journaux du jeu Elite Dangerous.")
