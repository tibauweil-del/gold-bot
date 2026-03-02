import yfinance as yf
import time
import requests
import os
from datetime import datetime

# Railway récupère ces infos dans l'onglet "Variables"
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def envoyer_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    try:
        requests.get(url)
    except:
        print("Erreur d'envoi Telegram")

def moteur_algo_final():
    # 1. Récupération des données
    gold = yf.Ticker("GC=F") 
    df = gold.history(period="5d", interval="60m")
    
    if df.empty:
        print("Erreur : Impossible de récupérer les données")
        return

    # 2. Calculs manuels (plus fiables)
    prix_actuel = df['Close'].iloc[-1]
    high_recent = df['High'].max()
    low_recent = df['Low'].min()
    
    # Calcul d'une zone d'entrée basée sur le retracement (Équilibre)
    # Pour une vente, on veut que le prix remonte vers le milieu du range récent
    zone_entree = (high_recent + prix_actuel) / 2
    
    # 3. Détermination du Biais
    # Si le prix est plus proche du haut, l'algo anticipe un retour au bas
    if prix_actuel > ((high_recent + low_recent) / 2):
        direction = "BAISSIÈRE 📉"
        target = low_recent
        type_ordre = "Vendre (Sell Limit)"
        stop_loss = high_recent + 5.0
    else:
        direction = "HAUSSIÈRE 📈"
        target = high_recent
        type_ordre = "Acheter (Buy Limit)"
        stop_loss = low_recent - 5.0

    alerte = (f"🎯 GOLD ALGO EXECUTION\n"
              f"----------------------------\n"
              f"Prix Actuel: {prix_actuel:.2f}$\n"
              f"Biais: {direction}\n"
              f"----------------------------\n"
              f"⚡ ZONE D'ENTRÉE: {zone_entree:.2f}$\n"
              f"🎯 CIBLE FINALE: {target:.2f}$\n"
              f"🛡️ STOP LOSS: {stop_loss:.2f}$\n"
              f"----------------------------\n"
              f"Action: {type_ordre}")
    
    envoyer_telegram(alerte)
    print(f"Rapport envoyé à {datetime.now().strftime('%H:%M')}")

# Lancement de la boucle
while True:
    moteur_algo_final()
    time.sleep(14400) # Toutes les 4 heures
