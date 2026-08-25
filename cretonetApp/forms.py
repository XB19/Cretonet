# cretonetApp/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Utilisateur

# ===== Formulaire d'inscription (public) =====
class FormulaireInscription(UserCreationForm):
    email = forms.EmailField(label="Email", required=True)
   
    role = forms.ChoiceField(label="Rôle", choices=Utilisateur.ROLES)
    telephone = forms.CharField(label="Téléphone", required=False)
    adresse = forms.CharField(label="Adresse", required=False)

    class Meta:
        model = Utilisateur
        fields = ['username', 'email', 'role', 'telephone', 'adresse', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        """
        Si on passe role='designer' (ou autre) dans kwargs, on initialise le champ role
        avec cette valeur et on le rend HiddenInput pour que l'utilisateur ne le modifie pas.
        """
        role_initial = kwargs.pop('role', None)
        super(FormulaireInscription, self).__init__(*args, **kwargs)


        for field_name, field in self.fields.items():

            field.widget.attrs['class'] = 'form-control'
            # placeholder optionnel
            field.widget.attrs['placeholder'] = field.label


        if role_initial:
            self.fields['role'].initial = role_initial
            self.fields['role'].widget = forms.HiddenInput()  

# ===== Formulaire de connexion =====
class FormulaireConnexion(AuthenticationForm):
    username = forms.EmailField(label='Email', widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Email'
    }))
    password = forms.CharField(label='Mot de passe', widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Mot de passe'
    }))


from django import forms
from django.forms import modelformset_factory
from .models import Project, ProjectImage

# --- Formulaire principal Project ---
class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['title', 'description', 'category', 'technologies', 'demo_link']

    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = field.label
            field.widget.attrs['style'] = 'margin-bottom: 15px;'
        if 'description' in self.fields:
            self.fields['description'].widget.attrs['rows'] = 5

# --- Formulaire pour les images ---
class ProjectImageForm(forms.ModelForm):
    class Meta:
        model = ProjectImage
        fields = ['image']

    def __init__(self, *args, **kwargs):
        super(ProjectImageForm, self).__init__(*args, **kwargs)
        self.fields['image'].widget.attrs.update({
            'class': 'form-control',
            'style': 'margin-bottom: 15px;',
        })

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            valid_extensions = ['jpg', 'jpeg', 'png', 'gif']
            ext = image.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError("Formats autorisés : jpg, jpeg, png, gif")
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Taille maximale : 5 Mo")
        return image

# --- Formset pour plusieurs images ---
ProjectImageFormSet = modelformset_factory(
    ProjectImage,
    form=ProjectImageForm,
    extra=3,
    max_num=5,
    validate_max=True,
)



from django import forms
from .models import Utilisateur


class ProfilForm(forms.ModelForm):
    class Meta:
        model = Utilisateur
        fields = ['first_name', 'last_name', 'email', 'telephone', 'bio', 'photo_profil']

from django import forms
from .models import Offer

class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = [
            'title',
            'description',
            'category',
            'deadline',
            'location',
            'required_profile',
            'file',
        ]

        widgets = {
            'deadline': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'description': forms.Textarea(
                attrs={'rows': 4, 'class': 'form-control'}
            ),
            'category': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'location': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'required_profile': forms.Select(
                attrs={'class': 'form-select'}
            ),
        }

