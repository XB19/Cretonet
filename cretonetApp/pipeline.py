ROLE_MAP = {
    'designer': 'designer',
    'developpeur': 'developpeur',
    'recruteur': 'recruteur',
}


def set_role_from_session(backend, user, response, *args, is_new=False, **kwargs):
    """
    Définit le rôle de l'utilisateur créé via OAuth selon la session.

    Uniquement à la création du compte : sur les connexions suivantes,
    l'utilisateur peut déjà exister (compte classique retrouvé via
    associate_by_email, ou reconnexion Google) et son rôle ne doit pas
    être réinitialisé à chaque connexion.
    """
    if user and is_new:
        # Récupérer le rôle choisi (valeur de repli si absent/inconnu)
        role = backend.strategy.session_get('role')
        user.role = ROLE_MAP.get(role, 'designer')
        user.save()
