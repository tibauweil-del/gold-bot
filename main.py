import yfinance as yf
import time
import requests
import os
from datetime import datetime

# Railway récupère ces infos dans l'onglet "Variables"
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def envoyer_telegram(message):
    if not TOKEN or not CHAT_ID:
        print("Erreur: Variables non configurées dans Railway")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=10)
        print("Message envoyé !")
    except Exception as e:
        print(f"Erreur d'envoi Telegram: {e}")

def moteur_algo():
    print(f"[{datetime.now().strftime('%H:%M')}] Analyse Gold en cours...")
    try:
        # Essai avec le Gold (GC=F ou GLD)
        gold = yf.Ticker("GC=F")
        df = gold.history(period="5d", interval="60m")
        if df.empty:
            gold = yf.Ticker("GLD")
            df = gold.history(period="5d", interval="60m")

        if df.empty:
            print("Données introuvables.")
            return

        prix = float(df['Close'].iloc[-1])
        high = float(df['High'].max())
        low = float(df['Low'].min())
        
        # Logique simple : si prix sous la moyenne = Haussier, sinon Baissier
        milieu = (high + low) / 2
        direction = "HAUSSIÈRE 📈" if prix < milieu else "BAISSIÈRE 📉"

        msg = (f"🚀 RAILWAY GOLD BOT\n"
               f"Prix: {prix:.2f}$\n"
               f"Biais: {direction}\n"
               f"Cible: {high if direction == 'HAUSSIÈRE 📈' else low:.2f}$\n"
               f"Stop: {low-5 if direction == 'HAUSSIÈRE 📈' else high+5:.2f}$")
        
        envoyer_telegram(msg)
    except Exception as e:
        print(f"Erreur calcul: {e}")

if __name__ == "__main__":
    print("Bot démarré sur Railway...")
    while True:
        moteur_algo()
        # Pause de 4 heures
        time.sleep(14400)