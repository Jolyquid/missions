import os
import json
import time
import threading
import pandas as pd
import streamlit as st
from glob import glob
from datetime import datetime, timedelta

# Configuration de la page Streamlit
st.set_page_config(layout="wide")

# Chemin vers les fichiers journaux d'Elite Dangerous
LOG_PATH = os.path.join(os.path.expanduser("~"), "Saved Games", "Frontier Developments", "Elite Dangerous")

def get_latest_journals(count=3):
    """Trouve les fichiers journaux les plus récents (par défaut 3)."""
    files = sorted(glob(os.path.join(LOG_PATH, "Journal*.log")), reverse=True)
    return files[:count]  # Retourne les 'count' fichiers les plus récents

def wait_for_file_change(filepath, check_interval=5):
    """Surveille le fichier et déclenche une mise à jour si modifié."""
    last_modified = os.path.getmtime(filepath) if os.path.exists(filepath) else 0

    while True:
        time.sleep(check_interval)
        if not os.path.exists(filepath):
            continue  # Évite une erreur si le fichier est supprimé temporairement

        new_modified = os.path.getmtime(filepath)
        if new_modified != last_modified:
            st.experimental_rerun()  # Relance l'application Streamlit

def format_timestamp(timestamp):
    """Formate la date et l'heure séparément sans le 'Z'."""
    if not timestamp:
        return "No deadline"
    date_part, time_part = timestamp.split("T")
    time_part = time_part.replace("Z", "")  # Supprime le 'Z' final
    return f"{date_part}     -     {time_part}"  # Remplace le format ISO par un format plus lisible

def parse_timestamp(timestamp):
    """Convertit une chaîne de timestamp en objet datetime."""
    if not timestamp:
        return None
    try:
        return datetime.strptime(timestamp.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None

def format_currency(value):
    """Formate les valeurs monétaires."""
    return f"{value:,.0f} CR"  # Format avec séparateurs de milliers et 'CR' pour crédits

def extract_missions(journal_files):
    """Extrait les missions en cours depuis plusieurs fichiers journaux."""
    missions = []
    completed_mission_ids = set()
    
    for journal_file in journal_files:
        with open(journal_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    if event.get("event") == "MissionRedirected":
                        completed_mission_ids.add(event.get("MissionID"))
                    elif event.get("event") == "MissionAccepted":
                        mission_id = event.get("MissionID")
                        if mission_id not in completed_mission_ids:
                            missions.append({
                                "MissionID": mission_id,
                                "Genre": event.get("Name", "Unknown").replace("_", " ").replace("Wing", ""),
                                "Sponsor": event.get("Faction", "Unknown"),
                                "Title": event.get("LocalisedName", "Unknown"),
                                "Target": event.get("TargetFaction", "N/A"),
                                "Destination": event.get("DestinationSystem", "N/A"),
                                "KillCount": event.get("KillCount", 0),
                                "Payout": format_currency(event.get("Reward", 0)),
                                "Coop": event.get("Wing"),
                                "Expiry": format_timestamp(event.get("Expiry")),
                                "ExpiryRaw": parse_timestamp(event.get("Expiry"))
                            })
                except json.JSONDecodeError:
                    continue  # Ignore les lignes invalides
    return missions

# Affichage avec Streamlit
latest_journals = get_latest_journals(3)

if latest_journals:
    st.toast("Surveillance du journal en cours...", icon="🔄")
    if "file_watcher" not in st.session_state:
        st.session_state.file_watcher = threading.Thread(target=wait_for_file_change, args=(latest_journals[0],), daemon=True)
        st.session_state.file_watcher.start()

missions = sorted(extract_missions(latest_journals), key=lambda x: x["Expiry"] or "")

if missions:
    df = pd.DataFrame(missions)
    col1, col2 = st.columns(2)

    with col1:
        st.title("🌐 Elite Dangerous - Actives Missions")
            
    with col2:
        kills_par_faction = df.groupby("Sponsor")["KillCount"].sum().reset_index()
        kills_par_faction.columns = ["Faction", "Total Kills"]
        st.markdown("""<br>""", unsafe_allow_html=True)
        st.write("### Nombre total de kills par faction :")
        st.dataframe(kills_par_faction, use_container_width=True, hide_index=True)

    st.write(f"📌 **{len(missions)} missions actives trouvées**")
    st.dataframe(missions, hide_index=True, height=int(35*21)+3)
    
    total_gains = df["Payout"].replace("[^0-9]", "", regex=True).astype(float).sum()
    st.subheader(f"💰 **Gains totaux estimés : {format_currency(total_gains)}**")
    st.markdown("""<br><br>""", unsafe_allow_html=True)
    
    st.subheader("📊 Statistiques des missions")
    col1, col2 = st.columns(2)
    
    with col1:
        missions_par_faction = df["Sponsor"].value_counts().reset_index()
        missions_par_faction.columns = ["Faction", "Nombre de missions"]
        st.write("### Nombre de missions par faction :")
        st.dataframe(missions_par_faction, use_container_width=True, hide_index=True)
    
    with col2:
        gains_par_faction = df.groupby("Sponsor")["Payout"].apply(lambda x: x.str.replace("[^0-9]", "", regex=True).astype(float).sum()).reset_index()
        gains_par_faction.columns = ["Faction", "Gains Totaux"]
        gains_par_faction["Gains Totaux"] = gains_par_faction["Gains Totaux"].apply(format_currency)
        st.write("### Récompenses totales par faction :")
        st.dataframe(gains_par_faction, use_container_width=True, hide_index=True)

else:
    st.error(f"Aucun fichier journal trouvé dans {LOG_PATH}. Assurez-vous que le jeu a été lancé au moins une fois.")
