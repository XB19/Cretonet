def set_role_from_session(backend, user, response, *args, **kwargs):
    """
    Définit le rôle de l'utilisateur créé via OAuth selon la session.
    """
    if user:
        # Récupérer le rôle choisi
        role = backend.strategy.session_get('role')
        if role:
            if role == 'prestataire':
                # On peut mettre un rôle générique prestataire pour UX
                user.role = 'prestataire'
            elif role == 'recruteur':
                user.role = 'recruteur'
            user.save()
