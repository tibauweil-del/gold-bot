import yfinance as yf
import time
import requests
import os
import numpy as np
from datetime import datetime

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
RECAP_ENVOYE = False # Pour éviter les envois multiples à 22h

def envoyer_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}/&text={message}"
    try:
        requests.get(url)
    except:
        print("Erreur d'envoi Telegram")

def detecter_liquidite(df, tolerance=0.0015):
    """Repère les Equal Highs (BSL) et Equal Lows (SSL) dynamiquement"""
    highs = df['High'].values
    lows = df['Low'].values
    bsl_zones, ssl_zones = [], []

    # On analyse les zones de prix sur les 100 dernières bougies
    for i in range(len(df) - 50, len(df)):
        p_h, p_l = highs[i], lows[i]
        # Recherche de clusters (alignement de mèches)
        if np.sum(np.abs(highs - p_h) < (p_h * tolerance)) >= 2:
            if not any(abs(z - p_h) < 10 for z in bsl_zones): bsl_zones.append(p_h)
        if np.sum(np.abs(lows - p_l) < (p_l * tolerance)) >= 2:
            if not any(abs(z - p_l) < 10 for z in ssl_zones): ssl_zones.append(p_l)
    return bsl_zones, ssl_zones

def moteur_algo_smc():
    global RECAP_ENVOYE
    # 1. Récupération des données (Contexte 1 mois / Action 1h)
    data = yf.Ticker("GC=F").history(period="1mo", interval="1h")
    if data.empty: return

    prix_actuel = data['Close'].iloc[-1]
    bsl, ssl = detecter_liquidite(data)
    maintenant = datetime.now()

    # --- LOGIQUE DE SESSION (RAPPORT 22H) ---
    if maintenant.hour == 22 and not RECAP_ENVOYE:
        envoi_rapport_final(bsl, ssl, prix_actuel, data)
        RECAP_ENVOYE = True
    if maintenant.hour == 23: RECAP_ENVOYE = False

    # --- LOGIQUE DE TRADING (SWEEP & RECLAIM) ---
    for zone_ssl in ssl:
        # Si le prix a percé la SSL puis est remonté (Manipulation Haussière)
        if data['Low'].iloc[-2] < zone_ssl and prix_actuel > zone_ssl:
            tp = max(bsl) if bsl else prix_actuel + 150
            sl = data['Low'].iloc[-2] - 5 # SL sous la mèche de chasse
            alerte = (f"🛡️ SMC BUY SIGNAL: SSL SWEEP\n"
                      f"----------------------------\n"
                      f"Zone nettoyée: {zone_ssl:.2f}$\n"
                      f"Entrée Reclaim: {prix_actuel:.2f}$\n"
                      f"🎯 TARGET (BSL): {tp:.2f}$\n"
                      f"🛡️ STOP LOSS: {sl:.2f}$\n"
                      f"Ratio: 1:{abs((tp-prix_actuel)/(prix_actuel-sl)):.1f}")
            envoyer_telegram(alerte)
            return

    for zone_bsl in bsl:
        # Si le prix a percé la BSL puis est redescendu (Manipulation Baissière)
        if data['High'].iloc[-2] > zone_bsl and prix_actuel < zone_bsl:
            tp = min(ssl) if ssl else prix_actuel - 150
            sl = data['High'].iloc[-2] + 5 # SL au-dessus de la mèche de chasse
            alerte = (f"📉 SMC SELL SIGNAL: BSL SWEEP\n"
                      f"----------------------------\n"
                      f"Zone nettoyée: {zone_bsl:.2f}$\n"
                      f"Entrée Reclaim: {prix_actuel:.2f}$\n"
                      f"🎯 TARGET (SSL): {tp:.2f}$\n"
                      f"🛡️ STOP LOSS: {sl:.2f}$")
            envoyer_telegram(alerte)
            return

def envoi_rapport_final(bsl, ssl, prix, df):
    high_w, low_w = df['High'].max(), df['Low'].min()
    pos = (prix - low_w) / (high_w - low_w) * 100
    msg = (f"🏛️ RÉCAPITULATIF POST-SESSION US\n"
           f"----------------------------\n"
           f"Clôture Gold: {prix:.2f}$\n"
           f"Position Range Hebdo: {pos:.1f}%\n"
           f"Biais: {'PREMIUM 🔴' if pos > 70 else 'DISCOUNT 🟢' if pos < 30 else 'EQUILIBRIUM 🟡'}\n\n"
           f"📋 ZONES ACTIVES POUR DEMAIN :\n"
           f"• SSL (Achat): {sorted(ssl)[-1] if ssl else 'N/A':.2f}$\n"
           f"• BSL (Vente): {sorted(bsl)[0] if bsl else 'N/A':.2f}$\n"
           f"----------------------------\n"
           f"Bot en veille structurelle.")
    envoyer_telegram(msg)

# Lancement du bot
while True:
    moteur_algo_smc()
    time.sleep(3600) # Vérification horaire
