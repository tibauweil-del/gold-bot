import yfinance as yf
import time
import requests
import os
import numpy as np
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def envoyer_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    try:
        requests.get(url)
    except:
        print("Erreur d'envoi Telegram")

def detecter_liquidite(df, tolerance=0.0015):
    """Identifie les Equal Highs (BSL) et Equal Lows (SSL)"""
    highs = df['High'].values
    lows = df['Low'].values
    bsl_zones = []
    ssl_zones = []

    for i in range(len(df) - 30, len(df)): # Analyse des 30 dernières zones
        prix_h, prix_l = highs[i], lows[i]
        
        # Compte les sommets/creux alignés dans l'historique
        count_h = np.sum(np.abs(highs - prix_h) < (prix_h * tolerance))
        count_l = np.sum(np.abs(lows - prix_l) < (prix_l * tolerance))
        
        if count_h >= 2 and not any(abs(z - prix_h) < 10 for z in bsl_zones):
            bsl_zones.append(prix_h)
        if count_l >= 2 and not any(abs(z - prix_l) < 10 for z in ssl_zones):
            ssl_zones.append(prix_l)
            
    return bsl_zones, ssl_zones

def moteur_algo_smc():
    # 1. Analyse Multi-Timeframe (H4 pour la structure, H1 pour le sweep)
    gold_h4 = yf.Ticker("GC=F").history(period="1mo", interval="1h")
    if gold_h4.empty: return

    prix_actuel = gold_h4['Close'].iloc[-1]
    bsl, ssl = detecter_liquidite(gold_h4)
    
    # 2. Logique de détection de Manipulation (Sweep & Reclaim)
    for zone_ssl in ssl:
        # On vérifie si la bougie précédente a "mèché" sous la SSL
        a_balaye = gold_h4['Low'].iloc[-2] < zone_ssl
        a_reintegre = prix_actuel > zone_ssl
        
        if a_balaye and a_reintegre:
            # Plan Haussier après nettoyage des stops
            tp = max(bsl) if bsl else prix_actuel + 200
            sl = gold_h4['Low'].iloc[-2] - 10 # SL sous la mèche de manipulation
            
            alerte = (f"🛡️ SMC DETECTED: LIQUIDITY SWEEP\n"
                      f"----------------------------\n"
                      f"Nettoyage SSL effectué à: {zone_ssl:.2f}$\n"
                      f"Prix actuel (Reclaim): {prix_actuel:.2f}$\n"
                      f"----------------------------\n"
                      f"⚡ ENTRÉE (OTE): {prix_actuel:.2f}$\n"
                      f"🎯 TARGET (BSL): {tp:.2f}$\n"
                      f"🛡️ STOP LOSS: {sl:.2f}$\n"
                      f"----------------------------\n"
                      f"Ratio estimé: 1:{abs((tp-prix_actuel)/(prix_actuel-sl)):.1f}")
            envoyer_telegram(alerte)
            return

    for zone_bsl in bsl:
        # On vérifie si la bougie précédente a "mèché" au-dessus de la BSL
        a_balaye = gold_h4['High'].iloc[-2] > zone_bsl
        a_reintegre = prix_actuel < zone_bsl
        
        if a_balaye and a_reintegre:
            # Plan Baissier après nettoyage des acheteurs
            tp = min(ssl) if ssl else prix_actuel - 200
            sl = gold_h4['High'].iloc[-2] + 10 # SL au-dessus de la mèche
            
            alerte = (f"📉 SMC DETECTED: BSL SWEEP\n"
                      f"----------------------------\n"
                      f"Nettoyage BSL effectué à: {zone_bsl:.2f}$\n"
                      f"Prix actuel (Reclaim): {prix_actuel:.2f}$\n"
                      f"----------------------------\n"
                      f"⚡ ENTRÉE (OTE): {prix_actuel:.2f}$\n"
                      f"🎯 TARGET (SSL): {tp:.2f}$\n"
                      f"🛡️ STOP LOSS: {sl:.2f}$\n"
                      f"----------------------------\n"
                      f"Action: Vendre (Short)")
            envoyer_telegram(alerte)
            return

    print(f"[{datetime.now().strftime('%H:%M')}] Marché en zone neutre (Equilibrium).")

# Boucle d'analyse (toutes les heures pour ne pas rater la réintégration)
while True:
    moteur_algo_smc()
    time.sleep(3600)
