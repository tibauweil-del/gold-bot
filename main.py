import yfinance as yf
import time
import requests
import os
import numpy as np
from datetime import datetime

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
RECAP_ENVOYE = False

def envoyer_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    try:
        requests.get(url)
    except:
        print("Erreur Telegram")

def detecter_liquidite_pro(df, tolerance=0.0008):
    """Analyse H1 : Mémoire de 500h pour les zones de poids"""
    highs = df['High'].values
    lows = df['Low'].values
    bsl_zones, ssl_zones = [], []
    taille_memoire = min(len(df), 500) 

    for i in range(len(df) - taille_memoire, len(df)):
        p_h, p_l = highs[i], lows[i]
        if np.sum(np.abs(highs - p_h) < (p_h * tolerance)) >= 3:
            if not any(abs(z - p_h) < 10 for z in bsl_zones): bsl_zones.append(p_h)
        if np.sum(np.abs(lows - p_l) < (p_l * tolerance)) >= 3:
            if not any(abs(z - p_l) < 10 for z in ssl_zones): ssl_zones.append(p_l)
    return bsl_zones, ssl_zones

def calculer_poc(df_m5):
    """Simule le Carnet d'Ordres (Point of Control) sur les dernières 2h"""
    # On cherche le prix où le volume a été le plus massif (VAP)
    bins = 20
    hist, bin_edges = np.histogram(df_m5['Close'], bins=bins, weights=df_m5['Volume'])
    poc_index = np.argmax(hist)
    return (bin_edges[poc_index] + bin_edges[poc_index+1]) / 2

def formater_alerte(direction, zone, prix, vol, tp, sl, poc):
    """Alerte Haute Précision avec confirmation POC"""
    ratio = abs((tp - prix) / (prix - sl))
    message = (f"🏛️ ELITE {direction} (M5 Trigger)\n"
               f"----------------------------\n"
               f"Zone H1 nettoyée : {zone:.2f}$\n"
               f"Volume M5 (Injection) : {vol:.0f} ⚡\n"
               f"POC (Point de Contrôle) : {poc:.2f}$ 🔥\n"
               f"----------------------------\n"
               f"⚡ ENTRÉE : {prix:.2f}$\n"
               f"🎯 TARGET : {tp:.2f}$\n"
               f"🛡️ STOP LOSS : {sl:.2f}$\n"
               f"----------------------------\n"
               f"Ratio : 1:{ratio:.1f}")
    envoyer_telegram(message)

def moteur_v6_elite():
    global RECAP_ENVOYE
    # 1. ANALYSE MACRO (H1)
    data_h1 = yf.Ticker("GC=F").history(period="1mo", interval="1h")
    # 2. ANALYSE MICRO (M5) pour la vitesse d'exécution
    data_m5 = yf.Ticker("GC=F").history(period="2d", interval="5m")
    
    if data_h1.empty or data_m5.empty: return

    prix_actuel = data_m5['Close'].iloc[-1]
    vol_m5 = data_m5['Volume'].iloc[-1]
    vol_moyen_m5 = data_m5['Volume'].rolling(window=20).mean().iloc[-1]
    
    bsl, ssl = detecter_liquidite_pro(data_h1)
    poc = calculer_poc(data_m5.tail(24)) # Analyse du volume profile sur les 2 dernières heures
    maintenant = datetime.now()

    # Rapport Quotidien
    if maintenant.hour == 22 and not RECAP_ENVOYE:
        # (Fonction envoi_rapport_final identique à V5.2)
        RECAP_ENVOYE = True
    if maintenant.hour == 23: RECAP_ENVOYE = False

    # FILTRE DE VITESSE : On ne déclenche que si le volume M5 explose (x2.0 pour le scalping)
    if vol_m5 < (vol_moyen_m5 * 2.0): return

    # LOGIQUE DE RÉACTION RAPIDE (M5 RECLAIM)
    for zone_ssl in ssl:
        # Si la bougie M5 précédente a balayé la zone et que l'actuelle réintègre
        if data_m5['Low'].iloc[-2] < zone_ssl and prix_actuel > zone_ssl:
            sl = data_m5['Low'].iloc[-2] - 5 # SL plus serré grâce à la précision M5
            formater_alerte("BUY (Long)", zone_ssl, prix_actuel, vol_m5, max(bsl), sl, poc)
            return

    for zone_bsl in bsl:
        if data_m5['High'].iloc[-2] > zone_bsl and prix_actuel < zone_bsl:
            sl = data_m5['High'].iloc[-2] + 5
            formater_alerte("SELL (Short)", zone_bsl, prix_actuel, vol_m5, min(ssl), sl, poc)
            return

while True:
    moteur_v6_elite()
    time.sleep(300) # Scan toutes les 5 minutes pour ne rien rater
