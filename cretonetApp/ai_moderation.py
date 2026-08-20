# ai_moderation.py
import os
from openai import OpenAI

# 🔹 Liste des mots interdits (vérification locale obligatoire)
MOTS_INTERDITS = [
    # Contenu sexuel / pornographique
    "sexe", "porno", "pornographie", "erotique", "hardcore", "adult",
    "fetish", "xxx", "sodomie", "inceste", "zoophilie", "pédophilie",
    "childporn", "nude", "nudité", "masturbation",

    # Violence / crime
    "tuer", "meurtre", "assassinat", "homicide", "vol", "braquage",
    "attaque", "viol", "agression", "kidnapping", "abduction", "terroriste",
    "armes", "explosif", "bomb", "suicide", "crime",

    # Drogues / alcool / tabac
    "drogue", "drogues", "cannabis", "marijuana", "haschisch", "cocaine",
    "heroine", "meth", "alcool", "tabac", "shit", "mdma", "ecstasy",
    "joint", "weed", "pipe", "sniff",

    # Escroqueries / fraude / hacking
    "arnaque", "escroquerie", "fraude", "hack", "phishing", "piratage",
    "spam", "spammy", "scam", "tromperie", "faux", "falsification",

    # Insultes / grossièretés
    "merde", "pute", "connard", "salope", "bâtard", "enculé", "salaud",

    # Jeu / casino / paris illégaux
    "casino", "pari", "gambling", "bet", "loterie", "jackpot", "roulette"
]

def moderer_contenu(titre: str, description: str) -> str:
    """
    Modère le contenu d'un projet.
    Retourne "APPROVED" si OK, "REJECTED" si contenu inapproprié.
    """

    texte = f"{titre} {description}".lower()

    # 🔹 Vérification locale : si un mot interdit apparait **partiellement**, rejeter
    for mot in MOTS_INTERDITS:
        if mot in texte:
            print(f"[MODERATION] Mot interdit détecté : {mot}")
            return "REJECTED"

    # 🔹 Vérification IA pour contexte (optionnelle)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[MODERATION] Clé OpenAI manquante – vérification IA ignorée")
        return "APPROVED"

    try:
        client = OpenAI(api_key=api_key)
        prompt = f"""
Analyse ce contenu publié sur une plateforme professionnelle.
Vérifie si le texte contient :
- spam
- arnaque
- contenu non professionnel
- insultes
- publicité abusive
- mots à connotation sexuelle ou inappropriée pour un environnement professionnel

Répond uniquement par :
APPROVED
ou
REJECTED

Texte :
{titre}
{description}
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": "Tu es un modérateur automatique pour une plateforme professionnelle."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=10
        )
        resultat = response.choices[0].message.content.strip().upper()
        if resultat not in ["APPROVED", "REJECTED"]:
            print("[MODERATION] Réponse IA invalide – on ignore l'IA")
            return "APPROVED"
        return resultat

    except Exception as e:
        print(f"[MODERATION] Erreur IA : {e} – on ignore l'IA")
        return "APPROVED"