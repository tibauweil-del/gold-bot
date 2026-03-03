import yfinance as yf
import time
import requests
import os
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def envoyer_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    try:
        requests.get(url)
    except:
        print("Erreur d'envoi Telegram")

def moteur_algo_final():
    # 1. Récupération des données (48h pour avoir le contexte d'hier et aujourd'hui)
    gold = yf.Ticker("GC=F") 
    df = gold.history(period="2d", interval="60m")
    
    if df.empty:
        print("Erreur : Impossible de récupérer les données")
        return

    prix_actuel = df['Close'].iloc[-1]
    # On définit le Range de travail sur les dernières 24 bougies (1 jour de trading)
    high_24h = df['High'].iloc[-24:].max()
    low_24h = df['Low'].iloc[-24:].min()
    amplitude = high_24h - low_24h

    # 2. Logique de Biais par rapport au Point Pivot (50% du Range)
    pivot = (high_24h + low_24h) / 2
    
    if prix_actuel > pivot:
        # BIAIS BAISSIER : On cherche à vendre le "Premium" (Haut du range)
        direction = "BAISSIÈRE 📉"
        # Entrée "Sniper" : Retracement de 75% du mouvement vers le haut
        zone_entree = low_24h + (amplitude * 0.75)
        target = low_24h # On vise le bas du range (Liquidité)
        stop_loss = high_24h + 5.0 # Invalidation au-dessus du sommet réel
        type_ordre = "Vendre (Sell Limit)"
    else:
        # BIAIS HAUSSIER : On cherche à acheter le "Discount" (Bas du range)
        direction = "HAUSSIÈRE 📈"
        # Entrée "Sniper" : Retracement de 25% du mouvement (achat à bas prix)
        zone_entree = low_24h + (amplitude * 0.25)
        target = high_24h # On vise le haut du range
        stop_loss = low_24h - 5.0 # Invalidation sous le creux réel
        type_ordre = "Acheter (Buy Limit)"

    # 3. Formatage du message "Pro"
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
    print(f"Rapport structurel envoyé à {datetime.now().strftime('%H:%M')}")

while True:
    moteur_algo_final()
    time.sleep(14400) # Analyse toutes les 4 heures
