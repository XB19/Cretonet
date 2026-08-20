from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class Utilisateur(AbstractUser):
    ROLES = [
        ('admin', 'Administrateur'),
        ('designer', 'Designer'),
        ('developpeur', 'Développeur'),
        ('recruteur', 'Recruteur'),
    ]

    id_utilisateur = models.AutoField(primary_key=True)
    role = models.CharField(max_length=20, choices=ROLES, default='designer')
    email = models.EmailField(unique=True)
    date_inscription = models.DateTimeField(default=timezone.now)

    
    telephone = models.CharField(max_length=20, blank=True, null=True) 
    photo_profil = models.ImageField(upload_to='photos_profil/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    adresse = models.CharField(max_length=255, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"




from django.conf import settings

class Project(models.Model):
    CATEGORY_CHOICES = [
        ('design_graphique', 'Design Graphique'),
        ('dev_web', 'Développement Web'),
        ('ui_ux', 'UI/UX'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('pending', 'En attente de validation IA'),
        ('published', 'Publié'),
        ('rejected', 'Refusé'),
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projects')

    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True)

    technologies = models.CharField(max_length=200, blank=True)
    demo_link = models.URLField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.owner.username})"

class ProjectImage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='project_images/')


from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Message(models.Model):
    expediteur = models.ForeignKey(
        User,
        related_name='messages_envoyes',
        on_delete=models.CASCADE
    )
    destinataire = models.ForeignKey(
        User,
        related_name='messages_recus',
        on_delete=models.CASCADE
    )
    contenu = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)

    # 🔹 Lien optionnel vers l'offre
    offre = models.ForeignKey(
        'Offer',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='messages'
    )

    def __str__(self):
        return f"{self.expediteur} → {self.destinataire} : {self.contenu[:20]}"




from django.urls import reverse

class Offer(models.Model):
    CATEGORY_CHOICES = [
        ('design', 'Design Graphique'),
        ('dev', 'Développement Web'),
        ('mobile', 'Développement Mobile'),
        ('uiux', 'UI/UX Design'),
        ('video', 'Montage / Motion Design'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('pending', 'En attente'),
        ('available', 'Disponible'),
        ('completed', 'Terminé'),
        ('rejected', 'Refusé'),
    ]

    WORK_MODE_CHOICES = [
        ('online', 'En ligne'),
        ('onsite', 'Présentiel'),
        ('hybrid', 'Hybride'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='offers'
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    required_profile = models.CharField(max_length=255)
    work_mode = models.CharField(max_length=20, choices=WORK_MODE_CHOICES, default='online')
    location = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')  
    deadline = models.DateField()
    file = models.FileField(upload_to='offer_files/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Offre : {self.title} ({self.owner.username})"
    
    def get_absolute_url(self):
        return reverse('offer_detail', args=[self.id])
    


# ==========================
# SIGNALEMENTS
# ==========================

class Report(models.Model):

    REPORT_TYPES = [
        ('project', 'Projet'),
        ('offer', 'Offre'),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports_sent'
    )

    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPES
    )

    project = models.ForeignKey(
        'Project',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports'
    )

    offer = models.ForeignKey(
        'Offer',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reports'
    )

    reason = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    resolved = models.BooleanField(
        default=False
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Signalement"
        verbose_name_plural = "Signalements"

    def __str__(self):
        if self.project:
            return f"Projet signalé : {self.project.title}"

        if self.offer:
            return f"Offre signalée : {self.offer.title}"

        return f"Signalement #{self.id}"

    def get_target(self):
        return self.project or self.offer