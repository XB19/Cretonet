from django.urls import path
from . import views
from .views import (
    admin_dashboard,
    admin_user_list,
    admin_project_list,
    admin_offer_list,
)


urlpatterns = [
    # Page d'accueil
    path('', views.index, name='home'),

    # Authentification
    path('connexion/', views.connexion, name='connexion'),
    path('deconnexion/', views.deconnexion, name='deconnexion'),
    path('choisir-role/', views.choisir_role, name='choisir_role'),
    path('inscription/<str:kind>/', views.inscription_role, name='inscription_role'),

# PROFIL UTILISATEUR

# Profil de l'utilisateur connecté
path('profil/', views.mon_profil, name='profil'),  # alias pour /profil/

# Ancienne route existante pour le profil connecté (optionnelle)
path('mon-profil/', views.mon_profil, name='mon_profil'),

# Voir le profil d’un autre utilisateur par son ID
path('profil/<int:user_id>/', views.profil_utilisateur, name='profil_utilisateur'),

# Modifier son profil
path('profil/modifier/', views.modifier_profil, name='modifier_profil'),
    

    # Messagerie
    path('messagerie/', views.messagerie, name='messagerie'),
    path('messagerie/<int:user_id>/', views.messagerie, name='messagerie'),
    path('messagerie_detail/<int:user_id>/', views.messagerie_detail, name='messagerie_detail'),
    path('messagerie/<int:user_id>/offre/<int:offer_id>/', views.messagerie, name='messagerie_offer'),



    # Projets
    path('projects/add/', views.add_project, name='add_project'),

    path('projet/<int:pk>/', views.project_detail, name='project_detail'),
    path('project/edit/<int:pk>/', views.edit_project, name='edit_project'),
    path('project/delete/<int:pk>/', views.delete_project, name='delete_project'),

    # Portfolios
    path('portfolio/<str:username>/', views.public_portfolio, name='public_portfolio'),

    path('publier-offre/', views.publish_offer, name='publish_offer'),
    path('offre-publiee/', views.offer_success, name='offer_success'),
    path('offre/<int:pk>/', views.offer_detail, name='offer_detail'),
    path('offre/<int:pk>/edit/', views.edit_offer, name='edit_offer'),
    path('offre/<int:pk>/delete/', views.delete_offer, name='delete_offer'),
    path('offre/<int:offer_id>/changer-status/', views.update_offer_status, name='change_offer_status'),
    path('prestataires/', views.liste_prestataires, name='prestataires_list'),
    path('offres/', views.offers_list, name='offers_list'),
    path('auth/google/<str:role>/', views.google_login_with_role, name='google_login_role'),


    #admin
    # --- ADMIN ---
    path('ad/dashboard/', admin_dashboard, name='admin_dashboard'),
    path('ad/utilisateurs/', views.admin_user_list, name='admin_user_list'),
    path('ad/projets/', views.admin_project_list, name='admin_project_list'),
    path('ad/offres/', views.admin_offer_list, name='admin_offer_list'),
     path('offres/<int:pk>/', views.admin_offer_detail, name='admin_offer_detail'),
    path('offres/<int:pk>/delete/', views.admin_offer_delete, name='admin_offer_delete'),
    path('utilisateurs/', views.admin_user_list, name='admin_user_list'),
    path('utilisateurs/ajouter/', views.admin_user_add, name='admin_user_add'),
    path('utilisateurs/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('utilisateurs/<int:user_id>/modifier/', views.admin_user_edit, name='admin_user_edit'),
    path('utilisateurs/<int:user_id>/supprimer/', views.admin_user_delete, name='admin_user_delete'),
    path('projects/', views.admin_project_list, name='admin_project_list'),
    path('projects/add/', views.admin_project_add, name='admin_project_add'),
    path('projects/<int:pk>/', views.admin_project_detail, name='admin_project_detail'),
    path('projects/<int:pk>/edit/', views.admin_project_edit, name='admin_project_edit'),
    path('projects/<int:pk>/delete/', views.admin_project_delete, name='admin_project_delete'),
    path('create-report/', views.create_report, name='create_report'),

# Validations
path(
    'ad/validations/',
    views.admin_validation_list,
    name='admin_validation_list'
),

# Signalements
path(
    'ad/signalements/',
    views.admin_report_list,
    name='admin_report_list'
),

# Messages
path(
    'ad/messages/',
    views.admin_message_list,
    name='admin_message_list'
),

# Statistiques
path(
    'ad/statistiques/',
    views.admin_stats,
    name='admin_stats'
),

# Paramètres
path(
    'ad/parametres/',
    views.admin_settings,
    name='admin_settings'
),

path(
    'messages/<int:id>/',
    views.admin_message_detail,
    name='admin_message_detail'
),

path(
    'messages/delete/<int:id>/',
    views.admin_delete_message,
    name='admin_delete_message'
),

# ==========================================
# VALIDATION OFFRES
# ==========================================

path(
    'ad/offres/<int:pk>/approve/',
    views.approve_offer,
    name='approve_offer'
),

path(
    'ad/offres/<int:pk>/reject/',
    views.reject_offer,
    name='reject_offer'
),

# ==========================================
# VALIDATION PROJETS
# ==========================================

path(
    'ad/projects/<int:pk>/approve/',
    views.approve_project,
    name='approve_project'
),

path(
    'ad/projects/<int:pk>/reject/',
    views.reject_project,
    name='reject_project'
),

path('ad/signalements/<int:id>/', views.admin_report_detail, name='admin_report_detail'),
path('ad/signalements/<int:id>/resolve/', views.resolve_report, name='resolve_report'),
path('ad/signalements/<int:id>/delete/', views.delete_report, name='delete_report'),


]
