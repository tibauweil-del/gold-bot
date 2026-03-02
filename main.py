import os
import yfinance as yf
import telebot
from datetime import datetime

# Configuration via les variables d'environnement Railway
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
bot = telebot.TeleBot(TOKEN)

def get_gold_data():
    gold = yf.Ticker("GC=F")
    data = gold.history(period="5d", interval="1h")
    current_price = data['Close'].iloc[-1]
    
    # Calcul des niveaux techniques (Biais Baissier actuel)
    # On reprend les niveaux de tes captures pour la cohérence
    target = 5144.80 
    stop_loss = 5439.10
    entry_zone = current_price * 1.008  # Calcul dynamique de la zone d'entrée
    
    return current_price, entry_zone, target, stop_loss

def send_signal():
    price, entry, tp, sl = get_gold_data()
    
    # Construction du message identique à l'original
    message = (
        "🎯 GOLD ALGO EXECUTION\n"
        "------------------------------\n"
        f"Prix Actuel: {price:.2f}$\n"
        "Biais: BAISSIÈRE 📉\n"
        "------------------------------\n"
        f"⚡ ZONE D'ENTRÉE: {entry:.2f}$\n"
        f"🎯 CIBLE FINALE: {tp:.2f}$\n"
        f"🛡️ STOP LOSS: {sl:.2f}$\n"
        "------------------------------\n"
        "Action: Vendre (Sell Limit)"
    )
    
    bot.send_message(CHAT_ID, message)
    print("Signal envoyé avec succès !")

if __name__ == "__main__":
    send_signal()
