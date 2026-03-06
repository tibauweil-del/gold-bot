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
        print("Erreur d'envoi Telegram : Vérifiez vos variables d'environnement.")

def detecter_liquidite_pro(df, tolerance=0.0008):
    """Mémoire augmentée : Analyse les 500 dernières bougies (1 mois de trading)"""
    highs = df['High'].values
    lows = df['Low'].values
    bsl_zones, ssl_zones = [], []

    # On définit la fenêtre de mémoire sur 500 bougies pour capter les zones historiques
    taille_memoire = min(len(df), 500) 

    for i in range(len(df) - taille_memoire, len(df)):
        p_h, p_l = highs[i], lows[i]
        
        # Validation 3 touches : cherche des plateaux horizontaux solides
        if np.sum(np.abs(highs - p_h) < (p_h * tolerance)) >= 3:
            if not any(abs(z - p_h) < 10 for z in bsl_zones): bsl_zones.append(p_h)
            
        if np.sum(np.abs(lows - p_l) < (p_l * tolerance)) >= 3:
            if not any(abs(z - p_l) < 10 for z in ssl_zones): ssl_zones.append(p_l)
            
    return bsl_zones, ssl_zones

def formater_alerte(direction, zone, prix, vol, tp, sl):
    """Structure de message professionnelle pour Telegram"""
    ratio = abs((tp - prix) / (prix - sl))
    message = (f"🏛️ INSTITUTIONAL {direction}\n"
               f"----------------------------\n"
               f"Zone nettoyée : {zone:.2f}$\n"
               f"Volume (Injection) : {vol:.0f} ⚡\n"
               f"----------------------------\n"
               f"⚡ ENTRÉE (Reclaim) : {prix:.2f}$\n"
               f"🎯 TARGET : {tp:.2f}$\n"
               f"🛡️ STOP LOSS : {sl:.2f}$\n"
               f"----------------------------\n"
               f"Ratio : 1:{ratio:.1f}")
    envoyer_telegram(message)

def envoi_rapport_final(bsl, ssl, prix, df):
    """Génère le rapport quotidien corrigé"""
    high_w, low_w = df['High'].max(), df['Low'].min()
    pos = (prix - low_w) / (high_w - low_w) * 100
    
    # Correction de l'inversion : BSL (Haut/Vente), SSL (Bas/Achat)
    bsl_proche = sorted([z for z in bsl if z > prix])[0] if bsl else (max(bsl) if bsl else 0)
    ssl_proche = sorted([z for z in ssl if z < prix])[-1] if ssl else (min(ssl) if ssl else 0)

    msg = (f"🏛️ ANALYSE POST-SESSION US\n"
           f"----------------------------\n"
           f"Gold : {prix:.2f}$\n"
           f"Position Range : {pos:.1f}% ({'PREMIUM 🔴' if pos > 70 else 'DISCOUNT 🟢' if pos < 30 else 'EQUILIBRIUM 🟡'})\n\n"
           f"📋 ZONES DE LIQUIDITÉ MAJEURES :\n"
           f"• BSL (Vente attendue) : {bsl_proche:.2f}$\n"
           f"• SSL (Achat attendu) : {ssl_proche:.2f}$\n"
           f"----------------------------\n"
           f"Filtre Volume : ACTIF (x1.5)")
    envoyer_telegram(msg)

def moteur_algo_smc_pro():
    global RECAP_ENVOYE
    # On télécharge assez de données pour la mémoire de 500h
    data = yf.Ticker("GC=F").history(period="1mo", interval="1h")
    if data.empty or len(data) < 30: return

    prix_actuel = data['Close'].iloc[-1]
    volume_actuel = data['Volume'].iloc[-1]
    volume_moyen = data['Volume'].rolling(window=20).mean().iloc[-1]
    bsl, ssl = detecter_liquidite_pro(data)
    maintenant = datetime.now()

    # Rapport quotidien à 22h
    if maintenant.hour == 22 and not RECAP_ENVOYE:
        envoi_rapport_final(bsl, ssl, prix_actuel, data)
        RECAP_ENVOYE = True
    if maintenant.hour == 23: RECAP_ENVOYE = False

    # Filtre de Volume Institutionnel x1.5
    if volume_actuel < (volume_moyen * 1.5):
        return 

    # Logique d'Achat (SSL Sweep)
    for zone_ssl in ssl:
        if data['Low'].iloc[-2] < zone_ssl and prix_actuel > zone_ssl:
            tp = max(bsl) if bsl else prix_actuel + 100
            sl = data['Low'].iloc[-2] - 8
            formater_alerte("BUY (Long)", zone_ssl, prix_actuel, volume_actuel, tp, sl)
            return

    # Logique de Vente (BSL Sweep)
    for zone_bsl in bsl:
        if data['High'].iloc[-2] > zone_bsl and prix_actuel < zone_bsl:
            tp = min(ssl) if ssl else prix_actuel - 100
            sl = data['High'].iloc[-2] + 8
            formater_alerte("SELL (Short)", zone_bsl, prix_actuel, volume_actuel, tp, sl)
            return

# --- BOUCLE PRINCIPALE ---
while True:
    moteur_algo_smc_pro()
    time.sleep(3600)
