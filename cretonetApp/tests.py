from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from .models import Utilisateur, Project, Report
from .ai_moderation import moderer_contenu

PASSWORD = "Xk7!qzP9vLmN2024"


class InscriptionTests(TestCase):
    """Un compte peut être créé avec chacun des 3 rôles (tâche 3)."""

    def test_inscription_designer_developpeur_recruteur(self):
        for kind, expected_role in [
            ("designer", "designer"),
            ("developpeur", "developpeur"),
            ("recruteur", "recruteur"),
        ]:
            with self.subTest(kind=kind):
                response = self.client.post(
                    reverse("inscription_role", kwargs={"kind": kind}),
                    {
                        "username": f"user_{kind}",
                        "email": f"{kind}@example.com",
                        "role": expected_role,
                        "telephone": "",
                        "adresse": "",
                        "password1": PASSWORD,
                        "password2": PASSWORD,
                    },
                )
                self.assertRedirects(response, reverse("connexion"))
                user = Utilisateur.objects.get(email=f"{kind}@example.com")
                self.assertEqual(user.role, expected_role)


class ConnexionTests(TestCase):
    """Un utilisateur créé peut se connecter avec son email et son mot de passe."""

    def test_connexion_par_email(self):
        Utilisateur.objects.create_user(
            username="jdoe", email="jdoe@example.com", password=PASSWORD, role="designer"
        )
        response = self.client.post(
            reverse("connexion"),
            {"username": "jdoe@example.com", "password": PASSWORD},
        )
        self.assertTrue(response.wsgi_request.user.is_authenticated)


class ModerationTests(TestCase):
    """moderer_contenu est déterministe et fonctionne hors ligne."""

    @patch("cretonetApp.ai_moderation.os.getenv", return_value=None)
    def test_contenu_avec_mot_interdit_est_rejete(self, mock_getenv):
        resultat = moderer_contenu("Titre normal", "Ceci contient de la drogue.")
        self.assertEqual(resultat, "REJECTED")

    @patch("cretonetApp.ai_moderation.os.getenv", return_value=None)
    def test_contenu_professionnel_est_approuve(self, mock_getenv):
        resultat = moderer_contenu(
            "Recherche développeur web",
            "Nous recherchons un développeur Django pour une mission de 3 mois.",
        )
        self.assertEqual(resultat, "APPROVED")


class AccesAdminTests(TestCase):
    """Un designer est redirigé, un admin accède aux pages d'administration."""

    def setUp(self):
        self.designer = Utilisateur.objects.create_user(
            username="designer1", email="designer1@example.com", password=PASSWORD, role="designer"
        )
        self.admin = Utilisateur.objects.create_user(
            username="admin1", email="admin1@example.com", password=PASSWORD, role="admin"
        )

    def test_designer_est_redirige(self):
        self.client.login(username="designer1@example.com", password=PASSWORD)
        response = self.client.get(reverse("admin_user_list"))
        self.assertRedirects(response, reverse("home"))

    def test_admin_accede(self):
        self.client.login(username="admin1@example.com", password=PASSWORD)
        response = self.client.get(reverse("admin_user_list"))
        self.assertEqual(response.status_code, 200)


class PublicationTests(TestCase):
    """Un recruteur ne peut pas publier un projet, un designer le peut."""

    def setUp(self):
        self.recruteur = Utilisateur.objects.create_user(
            username="recruteur1", email="recruteur1@example.com", password=PASSWORD, role="recruteur"
        )
        self.designer = Utilisateur.objects.create_user(
            username="designer2", email="designer2@example.com", password=PASSWORD, role="designer"
        )

    def _payload(self):
        return {
            "title": "Portfolio test",
            "description": "Un projet de test.",
            "category": "dev_web",
            "technologies": "Django",
            "demo_link": "",
            "action": "draft",
        }

    def test_recruteur_ne_peut_pas_publier(self):
        self.client.login(username="recruteur1@example.com", password=PASSWORD)
        self.client.post(reverse("add_project"), self._payload())
        self.assertFalse(Project.objects.filter(owner=self.recruteur).exists())

    def test_designer_peut_publier(self):
        self.client.login(username="designer2@example.com", password=PASSWORD)
        self.client.post(reverse("add_project"), self._payload())
        self.assertTrue(Project.objects.filter(owner=self.designer).exists())


class SignalementTests(TestCase):
    """Un utilisateur connecté peut créer un Report sur un projet."""

    def test_creation_report(self):
        owner = Utilisateur.objects.create_user(
            username="owner1", email="owner1@example.com", password=PASSWORD, role="designer"
        )
        reporter = Utilisateur.objects.create_user(
            username="reporter1", email="reporter1@example.com", password=PASSWORD, role="designer"
        )
        project = Project.objects.create(
            owner=owner, title="Projet signalé", description="...", category="dev_web", status="published"
        )

        self.client.login(username="reporter1@example.com", password=PASSWORD)
        self.client.post(
            reverse("create_report"),
            {"report_type": "project", "reason": "Contenu inapproprié", "project_id": project.id},
        )

        self.assertTrue(
            Report.objects.filter(reporter=reporter, project=project).exists()
        )
