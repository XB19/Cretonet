# cretonetApp/views.py

from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from .ai_moderation import moderer_contenu
from .decorators import admin_only
from .forms import FormulaireInscription, FormulaireConnexion, ProjectForm, ProfilForm, OfferForm
from .models import Project, ProjectImage, Offer, Message, Utilisateur, User, Report

User = get_user_model()




def index(request):
    prestataires = list(Utilisateur.objects.filter(
        role__in=['designer', 'developpeur']
    ))

    today = timezone.now().date()

    offers = list(Offer.objects.filter(
        status='available'
    ).order_by('-created_at')[:6])  # 👈 LIMITATION ICI

    for prestataire in prestataires:
        prestataire.preview_images = ProjectImage.objects.filter(
            project__owner=prestataire,
            project__status='published'
        ).order_by('-project__created_at')[:3]

    for offer in offers:
        offer.owner_preview_images = ProjectImage.objects.filter(
            project__owner=offer.owner,
            project__status='published'
        ).order_by('-project__created_at')[:3]

    return render(request, 'clients/index.html', {
        'prestataires': prestataires,
        'offers': offers,
    })







ROLE_MAP = {
    'designer': 'designer',
    'developpeur': 'developpeur',
    'recruteur': 'recruteur',
}

# Anciennes valeurs de kind (avant le passage à 3 rôles) : on redirige
# vers le nouveau choix plutôt que de renvoyer une erreur.
LEGACY_ROLE_KINDS = {'client', 'prestataire'}

ROLE_LABELS = {
    'designer': 'Designer',
    'developpeur': 'Développeur',
    'recruteur': 'Recruteur',
}

def choisir_role(request):
    """Page qui propose : Designer / Développeur / Recruteur"""
    return render(request, 'clients/choisir_role.html')


def inscription_role(request, kind):
    """
    kind : 'designer', 'developpeur' ou 'recruteur' (slug)
    Rend le formulaire avec le champ role pré-rempli et caché.
    Après inscription réussie, redirige vers la page de connexion.
    """
    kind = kind.lower()
    if kind in LEGACY_ROLE_KINDS:
        return redirect('choisir_role')
    if kind not in ROLE_MAP:
        return redirect('choisir_role')

    role_value = ROLE_MAP[kind]

    if request.method == "POST":
        form = FormulaireInscription(request.POST, role=role_value)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = role_value   
            user.save()

            messages.success(request, "Votre compte a été créé ! Connectez-vous pour continuer.")

            return redirect('connexion')
        else:
            print(form.errors)  
    else:
        form = FormulaireInscription(role=role_value)

    return render(request, 'clients/inscription_role.html', {
        'form': form,
        'kind': kind,
        'role_label': ROLE_LABELS[role_value]
    })


def connexion(request):
    if request.method == "POST":
        form = FormulaireConnexion(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)  # connecter l'utilisateur

            # 🔹 Redirection selon rôle
            if user.role == 'admin':
                return redirect('admin_dashboard')  # vers ton dashboard admin
            elif user.role in ['designer', 'developpeur', 'recruteur']:
                return redirect('mon_profil')  # profil client/prestataire
            else:
                return redirect('home')  # au cas où rôle inconnu
    else:
        form = FormulaireConnexion()

    return render(request, 'clients/connexion.html', {'form': form})



@login_required
def deconnexion(request):
    logout(request)
    return redirect('home')




def profil(request):
    user = request.user
    projets = Project.objects.filter(owner=user).order_by('-created_at')

    context = {
        'user': user,
        'projets': projets,
    }
    return render(request, 'clients/profil.html', context)



@login_required
def trouver_prestataire(request):
    return render(request, 'clients/trouver_prestataire.html')

@login_required
def publier_offre(request):
    return render(request, 'clients/publier_offre.html')

@login_required
def trouver_offre(request):
    return render(request, 'clients/trouver_offre.html')





def liste_prestataires(request):
    # Récupérer les paramètres GET
    q = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()

    # Filtrer les prestataires
    prestataires = User.objects.filter(
        role__in=['designer', 'developpeur']  # uniquement les prestataires
    )

    if q:
        prestataires = prestataires.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )

    if role:
        prestataires = prestataires.filter(role__iexact=role.lower())  # ignore case

    prestataires = list(prestataires)
    for prestataire in prestataires:
        prestataire.preview_images = ProjectImage.objects.filter(
            project__owner=prestataire,
            project__status='published'
        ).order_by('-project__created_at')[:3]

    context = {
        'prestataires': prestataires,
        'q': q,
        'role': role,
    }
    return render(request, 'clients/liste_prestataires.html', context)








@login_required
def add_project(request):

    # Vérification du rôle
    if request.user.role not in ['designer', 'developpeur']:
        messages.error(request, "Vous n'avez pas l'autorisation de publier un projet.")
        return redirect('home')

    if request.method == "POST":

        form = ProjectForm(request.POST)
        images = request.FILES.getlist('images')

        # action bouton
        action = request.POST.get("action")

        if form.is_valid():

            title = form.cleaned_data.get("title")
            description = form.cleaned_data.get("description")

            # MODERATION UNIQUEMENT SI PUBLICATION
            moderation_rejetee = False
            if action == "publish":
                resultat = moderer_contenu(title, description)
                moderation_rejetee = (resultat == "REJECTED")

            # 📦 Création projet
            project = form.save(commit=False)
            project.owner = request.user
            if action == "draft":
                project.status = "draft"
            elif moderation_rejetee:
                project.status = "pending"
            else:
                project.status = "published"
            project.save()

            # 📷 Sauvegarde images
            for image in images:
                ProjectImage.objects.create(
                    project=project,
                    image=image
                )

            # 💾 Brouillon
            if action == "draft":
                messages.info(request, "💾 Brouillon enregistré.")
                return redirect("add_project")

            if moderation_rejetee:
                messages.warning(
                    request,
                    "Votre publication a été mise en attente de vérification par un administrateur."
                )
            else:
                # ✅ Succès
                messages.success(request, "✅ Projet publié avec succès.")
            return redirect("profil_utilisateur", user_id=request.user.id_utilisateur)

        else:
            messages.error(request, "⚠️ Veuillez corriger les erreurs du formulaire.")

    else:
        form = ProjectForm()

    return render(request, "clients/add_project.html", {"form": form})



@login_required
def edit_project(request, pk):
    # Récupération du projet
    project = get_object_or_404(Project, pk=pk, owner=request.user)

    if request.method == "POST":
        # Si le formulaire est soumis
        title = request.POST.get('title')
        description = request.POST.get('description')
        category = request.POST.get('category')
        status = request.POST.get('status', 'draft')

        # MODERATION : seulement si le projet passe/reste publié
        if status == 'published':
            resultat = moderer_contenu(title, description)
            if resultat == "REJECTED":
                status = 'pending'

        # Mise à jour
        project.title = title
        project.description = description
        project.category = category
        project.status = status
        project.save()

        # Gestion fichiers images (simplifiée)
        if request.FILES.getlist('images'):
            for f in request.FILES.getlist('images'):
                project.images.create(image=f)

        if status == 'pending':
            return JsonResponse({'message': "Votre publication a été mise en attente de vérification par un administrateur."})
        return JsonResponse({'message': 'Projet mis à jour !'})

    # GET → renvoyer le template avec les données existantes
    context = {
        'project': project,
        'images': project.images.all(),  # si tu as un modèle lié pour images
    }
    return render(request, 'clients/project_edit.html', context)



@login_required
def delete_project(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    
    if request.method == "POST":
        project.delete()
        # Remplacer 'profile' par ton nom d'URL correct et utiliser id_utilisateur
        return redirect('profil')
    
    return render(request, 'clients/supprimer_projet.html', {'object': project})




@login_required
def modifier_profil(request):
    utilisateur = request.user

    if request.method == "POST":
        form = ProfilForm(request.POST, request.FILES, instance=utilisateur)
        if form.is_valid():
            form.save()
            return redirect('profil')  # redirige vers la page profil
    else:
        form = ProfilForm(instance=utilisateur)

    return render(request, 'clients/modifier_profil.html', {'form': form})



def project_detail(request, pk):
    projet = get_object_or_404(Project, id=pk)
    return render(request, 'clients/project_detail.html', {'projet': projet})



def public_portfolio(request, username):
    user = get_object_or_404(User, username=username)
    projects = user.projects.all()
    return render(request, 'CretonetApp/public_portfolio.html', {'user': user, 'projects': projects})



@login_required
def mon_profil(request):
    """
    Affiche le profil de l'utilisateur connecté.
    """
    user = request.user

    context = {
        'user': user,
        'is_owner': True,
        'projets': [],
        'offres': [],
        'brouillons_projets': [],
        'brouillons_offres': [],
    }

    if user.role in ['designer', 'developpeur']:
        context['projets'] = user.projects.filter(status='published').order_by('-created_at','-id')
        context['brouillons_projets'] = user.projects.filter(status='draft').order_by('-created_at', '-id')

    elif user.role == 'recruteur':
        context['offres'] = user.offers.filter(status='available').order_by('-created_at','-id')
        context['brouillons_offres'] = user.offers.filter(status='draft').order_by('-created_at','-id')

    return render(request, 'clients/profil.html', context)


def profil_utilisateur(request, user_id):
    """
    Affiche le profil d'un utilisateur (projets, offres, brouillons).
    """
    user = get_object_or_404(Utilisateur, id_utilisateur=user_id)
    is_owner = request.user.is_authenticated and request.user == user

    context = {
        'user': user,
        'is_owner': is_owner,
        'projets': [],
        'offres': [],
        'brouillons_projets': [],
        'brouillons_offres': [],
    }

    if user.role in ['designer', 'developpeur']:
        context['projets'] = user.projects.filter(status='published').order_by('-created_at', '-id')
        if is_owner:
            context['brouillons_projets'] = user.projects.filter(status='draft').order_by('-created_at', '-id')

    elif user.role == 'recruteur':
        context['offres'] = user.offers.filter(status='available').order_by('-created_at','-id')
        if is_owner:
            context['brouillons_offres'] = user.offers.filter(status='draft').order_by('-created_at','-id')

    return render(request, 'clients/profil.html', context)








@login_required
def messagerie(request, user_id=None):
    user = request.user
    destinataire = None
    conversation = []
    prefill_message = ""
    prefill_offer_id = request.GET.get('offer_id')  
    message_prefill = request.GET.get('message')     

    contact_ids_envoyes = Message.objects.filter(expediteur=user).values_list('destinataire__id_utilisateur', flat=True)
    contact_ids_recus = Message.objects.filter(destinataire=user).values_list('expediteur__id_utilisateur', flat=True)
    contact_ids = set(list(contact_ids_envoyes) + list(contact_ids_recus))

    utilisateurs = User.objects.filter(id_utilisateur__in=contact_ids)


    if user_id:
        destinataire = get_object_or_404(User, id_utilisateur=user_id)
        conversation = Message.objects.filter(
            (Q(expediteur=user) & Q(destinataire=destinataire)) |
            (Q(expediteur=destinataire) & Q(destinataire=user))
        ).order_by('created_at')

        Message.objects.filter(expediteur=destinataire, destinataire=user, lu=False).update(lu=True)
        offer_instance = None
        if prefill_offer_id:
            offer_instance = get_object_or_404(Offer, pk=prefill_offer_id)
            prefill_message = f"Bonjour, je suis intéressé par votre offre intitulée « {offer_instance.title} »…"
        elif message_prefill:
            prefill_message = message_prefill

        if request.method == 'POST':
            contenu = request.POST.get('contenu')
            if contenu:
                Message.objects.create(
                    expediteur=user,
                    destinataire=destinataire,
                    contenu=contenu,
                    offre=offer_instance  # On lie automatiquement le message à l'offre si existante
                )
                # Redirection pour vider le formulaire et afficher le message envoyé
                return redirect('messagerie', user_id=destinataire.id_utilisateur)

    # ----- 5️⃣ Context pour le template -----
    context = {
        'utilisateurs': utilisateurs,
        'destinataire': destinataire,
        'conversation': conversation,
        'messages': conversation,
        'prefill_message': prefill_message,
    }

    return render(request, 'clients/messagerie.html', context)












def navbar_context(request):
    if request.user.is_authenticated:
        # Nombre total de messages non lus
        messages_non_lus = Message.objects.filter(destinataire=request.user, lu=False)

        # Liste des utilisateurs qui t'ont envoyé au moins un message non lu
        utilisateurs_non_lus = messages_non_lus.values(
            'expediteur__id_utilisateur', 'expediteur__username', 'expediteur__photo_profil'
        ).annotate(nb_messages=Count('id'))

        return {
            'messages_non_lus': messages_non_lus.count(),
            'utilisateurs_non_lus': utilisateurs_non_lus
        }
    return {}





@login_required
def messagerie_detail(request, user_id):
    destinataire = get_object_or_404(User, id_utilisateur=user_id)

    messages = Message.objects.filter(
        (Q(expediteur=request.user) & Q(destinataire=destinataire)) |
        (Q(expediteur=destinataire) & Q(destinataire=request.user))
    ).order_by('created_at')

    return render(request, 'clients/messagerie_detail.html', {
        'destinataire': destinataire,
        'messages': messages
    })




@login_required
def publish_offer(request, offer_id=None):
    if request.user.role != 'recruteur':
        return HttpResponseForbidden("Vous n'avez pas l'autorisation de publier une offre.")

    offer = get_object_or_404(Offer, id=offer_id, owner=request.user) if offer_id else None
    form = OfferForm(request.POST or None, request.FILES or None, instance=offer)

    if request.method == 'POST' and form.is_valid():
        offer_instance = form.save(commit=False)
        offer_instance.owner = request.user
        action = request.POST.get('action')

        if action == 'draft':
            offer_instance.status = 'draft'
            offer_instance.save()
            messages.success(request, "Votre offre a été enregistrée comme brouillon.")
            return redirect('mon_profil')

        # Modération AVANT publication
        decision = moderer_contenu(offer_instance.title, offer_instance.description)
        if decision == "REJECTED":
            offer_instance.status = 'pending'
            offer_instance.save()
            messages.warning(
                request,
                "Votre publication a été mise en attente de vérification par un administrateur."
            )
            return redirect('mon_profil')

        offer_instance.status = 'available'
        offer_instance.save()
        messages.success(request, "Votre offre a été publiée avec succès.")
        return redirect('mon_profil')

    return render(request, 'clients/publish_offer.html', {'form': form, 'offer': offer})


@login_required
def offer_success(request):
    return render(request, 'clients/success.html')


# Optionnel : modification du statut depuis le profil
@login_required
def update_offer_status(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id)

    # Vérifie que l'utilisateur est bien le propriétaire
    if offer.owner != request.user:
        return HttpResponseForbidden("Vous n'avez pas l'autorisation de modifier cette offre.")

    if request.method == "POST":
        status = request.POST.get('status')
        if status in ['available', 'completed']:
            offer.status = status
            offer.save()
            messages.success(request, "Statut de l'offre mis à jour avec succès.")
        else:
            messages.error(request, "Statut invalide.")

    return redirect('offer_detail', pk=offer.id)  # redirection vers la page profil








def offer_detail(request, pk):
    offer = get_object_or_404(Offer, pk=pk)

    # Vérifie si l'utilisateur connecté est le propriétaire
    is_owner = request.user == offer.owner

    # Autres offres (sauf celle affichée)
    other_offers = Offer.objects.exclude(pk=pk).order_by('-created_at')[:6]

    # Construire le message à envoyer via la messagerie
    base_message = f"Bonjour, je suis intéressé par votre offre intitulée « {offer.title} ». Vous pouvez la consulter ici : {request.build_absolute_uri(offer.get_absolute_url())}"
    encoded_message = urlencode({'message': base_message})  # encode pour URL

    return render(request, 'clients/offer_detail.html', {
        'offer': offer,
        'is_owner': is_owner,
        'other_offers': other_offers,
        'encoded_message': encoded_message,  # on passe au template
    })


@login_required
def edit_offer(request, pk):
    offer = get_object_or_404(Offer, pk=pk)

    if offer.owner != request.user:
        messages.error(request, "Vous n'avez pas l'autorisation de modifier cette offre.")
        return redirect('liste_offres')

    if request.method == 'POST':
        form = OfferForm(request.POST, request.FILES, instance=offer)
        if form.is_valid():
            offer = form.save(commit=False)  # On récupère l'objet sans sauvegarder

            # Vérifie quel bouton a été cliqué
            action = request.POST.get('action')
            if action == 'draft':
                offer.status = 'draft'
            else:
                # MODERATION : l'offre doit passer/rester disponible
                resultat = moderer_contenu(offer.title, offer.description)
                offer.status = 'pending' if resultat == "REJECTED" else 'available'

            offer.save()  # Sauvegarde avec le statut correct

            if offer.status == 'draft':
                messages.success(request, "Brouillon enregistré avec succès.")
            elif offer.status == 'pending':
                messages.warning(
                    request,
                    "Votre publication a été mise en attente de vérification par un administrateur."
                )
            else:
                messages.success(request, "Offre publiée avec succès.")

            return redirect('offer_detail', pk=offer.id)
        else:
            messages.error(request, "Veuillez corriger les erreurs.")
    else:
        form = OfferForm(instance=offer)

    return render(request, 'clients/edit_offer.html', {'form': form, 'offer': offer})

@login_required
def delete_offer(request, pk):
    offer = get_object_or_404(Offer, pk=pk)

    
    if offer.owner != request.user:
        messages.error(request, "Vous n'avez pas l'autorisation de supprimer cette offre.")
        return redirect('profil')

    if request.method == 'POST':
        offer.delete()
        messages.success(request, "Offre supprimée avec succès.")
        return redirect('profil')

    return render(request, 'clients/delete_offer.html', {'offer': offer})



def offers_list(request):
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    offers = Offer.objects.filter(status='available')

    if q:
        offers = offers.filter(title__icontains=q)

    if category:
        offers = offers.filter(category=category)

    for offer in offers:
        offer.owner_preview_images = ProjectImage.objects.filter(
            project__owner=offer.owner,
            project__status='published'
        ).order_by('-project__created_at')[:3]

    context = {
        'offers': offers,
        'q': q,
        'category': category,
    }
    return render(request, 'clients/liste_offres.html', context)



def google_login_with_role(request, role):
    # Sauvegarder le rôle choisi dans la session
    request.session['role'] = role
    # Rediriger vers l’authentification Google
    return redirect(reverse('social:begin', args=['google-oauth2']))



#admin




@login_required
@admin_only
def admin_dashboard(request):
    # Comptes globaux
    users_count = Utilisateur.objects.count()
    projects_count = Project.objects.count()
    offers_count = Offer.objects.count()

    # Projets par catégorie
    projects_by_category = Project.objects.values('category')\
                            .annotate(count=Count('id'))\
                            .order_by('category')
    projects_by_category_dict = {p['category']: p['count'] for p in projects_by_category}

    # Offres par catégorie
    offers_by_category = Offer.objects.values('category')\
                            .annotate(count=Count('id'))\
                            .order_by('category')
    offers_by_category_dict = {o['category']: o['count'] for o in offers_by_category}

    # Utilisateurs par rôle (⚠ ici on change id -> id_utilisateur)
    users_by_role = Utilisateur.objects.values('role')\
                        .annotate(count=Count('id_utilisateur'))\
                        .order_by('role')
    users_by_role_dict = {u['role']: u['count'] for u in users_by_role}

    context = {
        'users_count': users_count,
        'projects_count': projects_count,
        'offers_count': offers_count,
        'projects_by_category': projects_by_category_dict,
        'offers_by_category': offers_by_category_dict,
        'users_by_role': users_by_role_dict,
    }

    return render(request, 'admin/dashboard.html', context)





@login_required
@admin_only
def admin_users(request):
    users = User.objects.all()
    return render(request, 'admin/users.html', {'users': users})







# Liste des utilisateurs

@login_required
@admin_only
def admin_user_list(request):
    user_list = User.objects.all().order_by('-date_inscription')
    paginator = Paginator(user_list, 10)  # 10 utilisateurs par page

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    start_index = page_obj.start_index()  # ici c'est une méthode

    context = {
        'users': page_obj,
        'start_index': start_index,  # passe dans le template
    }
    return render(request, 'admin/users.html', context)



# Ajouter un utilisateur
@login_required
@admin_only
def admin_user_add(request):
    if request.method == "POST":
        email = request.POST.get("email")
        role = request.POST.get("role")
        password = request.POST.get("password")
        # Créer l'utilisateur
        user = User.objects.create_user(email=email, password=password, role=role)
        messages.success(request, "Utilisateur ajouté avec succès !")
        return redirect('admin_user_list')
    return render(request, 'admin/users_add.html')

# Voir un utilisateur
@login_required
@admin_only
def admin_user_detail(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    return render(request, 'admin/users_detail.html', {'user': user})

# Modifier un utilisateur
@login_required
@admin_only
def admin_user_edit(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        user.email = request.POST.get("email")
        user.role = request.POST.get("role")
        user.save()
        messages.success(request, "Utilisateur mis à jour !")
        return redirect('admin_user_list')
    return render(request, 'admin/users_edit.html', {'user': user})

# Supprimer un utilisateur
@login_required
@admin_only
def admin_user_delete(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    user.delete()
    messages.success(request, "Utilisateur supprimé !")
    return redirect('admin_user_list')


@login_required
@admin_only
def admin_project_list(request):
    projects = Project.objects.all().order_by('-created_at')  # Les plus récents en premier
    paginator = Paginator(projects, 10)  # 10 projets par page

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'projects': page_obj
    }
    return render(request, 'admin/projects.html', context)


@login_required
@admin_only
def admin_project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    return render(request, 'admin/project_detail.html', {
        'project': project
    })

@login_required
@admin_only
def admin_project_add(request):
    if request.method == 'POST':
        Project.objects.create(
            owner_id=request.POST.get('owner'),
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            category=request.POST.get('category'),
            technologies=request.POST.get('technologies'),
        )
        return redirect('admin_project_list')

    users = User.objects.all()
    return render(request, 'admin/project_form.html', {
        'users': users,
        'mode': 'add'
    })



@login_required
@admin_only
def admin_project_edit(request, pk):
    # Récupérer le projet ou renvoyer 404
    project = get_object_or_404(Project, pk=pk)
    
    # Tous les utilisateurs pour la sélection du propriétaire
    users = User.objects.all()

    if request.method == 'POST':
        owner_id = request.POST.get('owner')
        title = request.POST.get('title')
        description = request.POST.get('description')
        category = request.POST.get('category')
        technologies = request.POST.get('technologies')

        # Validation basique
        if not owner_id or not title or not description:
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")
            return render(request, 'admin/project_edit.html', {
                'project': project,
                'users': users
            })

        try:
            owner = User.objects.get(id=owner_id)
        except User.DoesNotExist:
            messages.error(request, "Utilisateur sélectionné invalide.")
            return render(request, 'admin/project_edit.html', {
                'project': project,
                'users': users
            })

        # Mettre à jour le projet
        project.owner = owner
        project.title = title
        project.description = description
        project.category = category
        project.technologies = technologies
        project.save()

        messages.success(request, "Projet mis à jour avec succès !")
        return redirect('admin_project_list')  # ← redirection vers la liste

    # GET : afficher le formulaire
    return render(request, 'admin/project_edit.html', {
        'project': project,
        'users': users
    })


@login_required
@admin_only
def admin_project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)

    if request.method == 'POST':
        project.delete()
        return redirect('admin_project_list')

    return render(request, 'admin/project_confirm_delete.html', {
        'project': project
    })




# Liste des offres avec pagination
@login_required
@admin_only
def admin_offer_list(request):
    offers_list = Offer.objects.all().order_by('-created_at')
    paginator = Paginator(offers_list, 10)  # 10 offres par page
    page_number = request.GET.get('page')
    offers = paginator.get_page(page_number)
    return render(request, 'admin/offers.html', {'offers': offers})

# Détail d'une offre
@login_required
@admin_only
def admin_offer_detail(request, pk):
    offer = get_object_or_404(Offer, pk=pk)
    return render(request, 'admin/offer_detail.html', {'offer': offer})

# Supprimer une offre
@login_required
@admin_only
def admin_offer_delete(request, pk):
    offer = get_object_or_404(Offer, pk=pk)
    if request.method == "POST":
        offer.delete()
        return redirect('admin_offer_list')
    return render(request, 'admin/offer_delete.html', {'offer': offer})


# ==========================
# ADMIN VALIDATIONS
# ==========================

@login_required
@admin_only
def admin_validation_list(request):

    filter_type = request.GET.get('filter', 'pending')

    # =====================================
    # OFFRES
    # =====================================

    pending_offers = Offer.objects.filter(
        status='pending'
    ).order_by('-created_at')

    approved_offers = Offer.objects.filter(
        status='available'
    ).order_by('-created_at')

    rejected_offers = Offer.objects.filter(
        status='rejected'
    ).order_by('-created_at')

    # =====================================
    # PROJETS
    # =====================================

    pending_projects = Project.objects.filter(
        status='pending'
    ).order_by('-created_at')

    approved_projects = Project.objects.filter(
        status='published'
    ).order_by('-created_at')

    rejected_projects = Project.objects.filter(
        status='rejected'
    ).order_by('-created_at')

    # =====================================
    # FILTRE PRINCIPAL
    # =====================================

    if filter_type == 'approved':

        offers = approved_offers
        projects = approved_projects

    elif filter_type == 'rejected':

        offers = rejected_offers
        projects = rejected_projects

    else:

        offers = pending_offers
        projects = pending_projects

    context = {

        # LISTES
        'offers': offers,
        'projects': projects,

        # COUNTS OFFRES
        'pending_offers_count': pending_offers.count(),
        'approved_offers_count': approved_offers.count(),
        'rejected_offers_count': rejected_offers.count(),

        # COUNTS PROJETS
        'pending_projects_count': pending_projects.count(),
        'approved_projects_count': approved_projects.count(),
        'rejected_projects_count': rejected_projects.count(),

        # TOTALS
        'approved_count': (
            approved_offers.count()
            + approved_projects.count()
        ),

        'rejected_count': (
            rejected_offers.count()
            + rejected_projects.count()
        ),

        # FILTRE ACTIF
        'current_filter': filter_type,
    }

    return render(
        request,
        'admin/validations.html',
        context
    )

@login_required
@admin_only
def approve_offer(request, pk):

    offer = get_object_or_404(
        Offer,
        pk=pk
    )

    offer.status = 'available'
    offer.save()

    messages.success(
        request,
        "Offre validée avec succès."
    )

    return redirect('admin_validation_list')



@login_required
@admin_only
def reject_offer(request, pk):

    offer = get_object_or_404(
        Offer,
        pk=pk
    )

    offer.status = 'rejected'
    offer.save()

    messages.warning(
        request,
        "Offre refusée."
    )

    return redirect('admin_validation_list')


@login_required
@admin_only
def approve_project(request, pk):

    project = get_object_or_404(
        Project,
        pk=pk
    )

    project.status = 'published'
    project.save()

    messages.success(
        request,
        "Projet validé avec succès."
    )

    return redirect('admin_validation_list')


@login_required
@admin_only
def reject_project(request, pk):

    project = get_object_or_404(
        Project,
        pk=pk
    )

    project.status = 'rejected'
    project.save()

    messages.warning(
        request,
        "Projet refusé."
    )

    return redirect('admin_validation_list')


# ==========================
# ADMIN SIGNALEMENTS
# ==========================

@login_required
@admin_only
def admin_report_list(request):

    reports = Report.objects.all().order_by(
        '-created_at'
    )

    context = {
        'reports': reports
    }

    return render(
        request,
        'admin/reports.html',
        context
    )

# ==========================
# ADMIN MESSAGES
# ==========================




@login_required
@admin_only
def admin_message_list(request):

    messages_qs = Message.objects.select_related(
        'expediteur',
        'destinataire',
        'offre'
    ).order_by('-created_at')

    # =========================
    # SEARCH
    # =========================
    query = request.GET.get('q')
    if query:
        messages_qs = messages_qs.filter(
            Q(expediteur__username__icontains=query) |
            Q(destinataire__username__icontains=query) |
            Q(contenu__icontains=query) |
            Q(offre__title__icontains=query)
        )

    # =========================
    # FILTERS
    # =========================
    filter_type = request.GET.get('filter')
    now = timezone.now()

    if filter_type == "today":
        messages_qs = messages_qs.filter(created_at__date=now.date())

    elif filter_type == "month":
        messages_qs = messages_qs.filter(
            created_at__gte=now - timedelta(days=30)
        )

    elif filter_type == "unread":
        messages_qs = messages_qs.filter(lu=False)

    elif filter_type == "read":
        messages_qs = messages_qs.filter(lu=True)

    # =========================
    # PAGINATION
    # =========================
    paginator = Paginator(messages_qs, 8)
    page_number = request.GET.get('page')
    messages_list = paginator.get_page(page_number)

    # =========================
    # CONTEXT
    # =========================
    context = {
        'messages_list': messages_list,
        'total_messages': messages_qs.count(),
        'query': query,
        'filter_type': filter_type,
    }

    return render(request, 'admin/messages.html', context)


# ==========================
# ADMIN STATISTIQUES
# ==========================

@login_required
@admin_only
def admin_stats(request):

    total_users = Utilisateur.objects.count()

    total_projects = Project.objects.count()

    total_offers = Offer.objects.count()

    total_messages = Message.objects.count()

    designers = Utilisateur.objects.filter(
        role='designer'
    ).count()

    developpeurs = Utilisateur.objects.filter(
        role='developpeur'
    ).count()

    recruteurs = Utilisateur.objects.filter(
        role='recruteur'
    ).count()

    context = {

        'total_users': total_users,
        'total_projects': total_projects,
        'total_offers': total_offers,
        'total_messages': total_messages,

        'designers': designers,
        'developpeurs': developpeurs,
        'recruteurs': recruteurs,
    }

    return render(
        request,
        'admin/stats.html',
        context
    )


# ==========================
# ADMIN PARAMETRES
# ==========================

@login_required
@admin_only
def admin_settings(request):

    context = {}

    return render(
        request,
        'admin/settings.html',
        context
    )





@login_required
@admin_only
def admin_message_detail(request, id):

    message = get_object_or_404(Message, id=id)


    return render(
        request,
        'admin/message_detail.html',
        {
            'message': message
        }
    )


@login_required
@admin_only
def admin_delete_message(request, id):

    message = get_object_or_404(Message, id=id)

    message.delete()

    return redirect('admin_messages')






@login_required
def create_report(request):

    if request.method != "POST":
        messages.error(request, "Action non autorisée.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    report_type = request.POST.get("report_type")
    reason = request.POST.get("reason")

    # =========================
    # VALIDATION DE BASE
    # =========================
    if not report_type or not reason:
        messages.error(request, "Veuillez remplir tous les champs.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    report = Report(
        reporter=request.user,
        report_type=report_type,
        reason=reason
    )

    # =========================
    # CAS PROJECT
    # =========================
    if report_type == "project":

        project_id = request.POST.get("project_id")

        if not project_id:
            messages.error(request, "Projet introuvable.")
            return redirect(request.META.get('HTTP_REFERER', '/'))

        project = get_object_or_404(Project, id=project_id)
        report.project = project

    # =========================
    # CAS OFFER
    # =========================
    elif report_type == "offer":

        offer_id = request.POST.get("offer_id")

        if not offer_id:
            messages.error(request, "Offre introuvable.")
            return redirect(request.META.get('HTTP_REFERER', '/'))

        offer = get_object_or_404(Offer, id=offer_id)
        report.offer = offer

    else:
        messages.error(request, "Type de signalement invalide.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    # =========================
    # SAUVEGARDE
    # =========================
    report.save()

    messages.success(request, "🚩 Signalement envoyé avec succès.")

    return redirect(request.META.get('HTTP_REFERER', '/'))



@login_required
@admin_only
def admin_report_detail(request, id):
    report = get_object_or_404(Report, id=id)
    return render(request, "admin/report_detail.html", {"report": report})


@login_required
@admin_only
def resolve_report(request, id):
    report = get_object_or_404(Report, id=id)
    report.resolved = True
    report.save()
    return redirect('admin_report_list')

@login_required
@admin_only
def delete_report(request, id):
    report = get_object_or_404(Report, id=id)
    report.delete()
    return redirect('admin_report_list')