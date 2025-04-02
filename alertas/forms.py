# alertas/forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Alerta, Keyword, EmailAlertConfig
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

# Modificar el formulario AlertaFilterForm en forms.py
class AlertaFilterForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        empty_label="<Seleccionar usuario>",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    keywords = forms.MultipleChoiceField(
        choices=[],
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select'})
    )
    
    institution = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    country = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Nuevos campos de filtro
    source_type = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    category = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False
    )
    
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False
    )
    
    search_text = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Buscar por título o descripción'})
    )
    
    # Eliminamos el campo page_size
    
    def __init__(self, *args, **kwargs):
        super(AlertaFilterForm, self).__init__(*args, **kwargs)
        
        # Configurar opciones para instituciones
        institutions = Alerta.objects.values_list('institution', flat=True).distinct().order_by('institution')
        institution_choices = [('', 'Todas')]
        institution_choices.extend([(inst, inst) for inst in institutions if inst])
        self.fields['institution'].choices = institution_choices
        
        # Configurar opciones para países
        countries = Alerta.objects.values_list('country', flat=True).distinct().order_by('country')
        country_choices = [('', 'Todos')]
        country_choices.extend([(country, country) for country in countries if country])
        self.fields['country'].choices = country_choices
        
        # Configurar opciones para tipos de fuente
        source_types = Alerta.objects.values_list('source_type', flat=True).distinct().order_by('source_type')
        source_type_choices = [('', 'Todos')]
        source_type_choices.extend([(st, st) for st in source_types if st])
        self.fields['source_type'].choices = source_type_choices
        
        # Configurar opciones para categorías
        categories = Alerta.objects.values_list('category', flat=True).distinct().order_by('category')
        category_choices = [('', 'Todas')]
        category_choices.extend([(cat, cat) for cat in categories if cat])
        self.fields['category'].choices = category_choices
        
        # Las opciones de keywords se configurarán dinámicamente en la vista
        # cuando se seleccione un usuario

class KeywordForm(forms.ModelForm):
    word = forms.CharField(
        max_length=100, 
        label="Palabra clave",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese una palabra clave'
        })
    )
    
    class Meta:
        model = Keyword
        fields = ['word']

# Envio de Alertas por mail formulario
class EmailAlertConfigForm(forms.ModelForm):
    # Listas desplegables para los campos que deben permitir selección
    source_type = forms.ChoiceField(required=False, label="Tipo de fuente")
    category = forms.ChoiceField(required=False, label="Categoría")
    country = forms.ChoiceField(required=False, label="País")
    institution = forms.ChoiceField(required=False, label="Institución")
    
    class Meta:
        model = EmailAlertConfig
        fields = ['name', 'active', 'keywords', 'source_type', 'category', 
                  'country', 'institution', 'days_back', 'email', 'frequency']
        widgets = {
            'keywords': forms.CheckboxSelectMultiple(),
            'days_back': forms.NumberInput(attrs={'min': 1, 'max': 30}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Filtrar las keywords del usuario
            self.fields['keywords'].queryset = Keyword.objects.filter(user=user, active=True)
        
        # Obtener opciones únicas de la base de datos para los filtros
        countries = [('', '--------')] + [(c, c) for c in Alerta.objects.values_list('country', flat=True).distinct().order_by('country')]
        self.fields['country'].choices = countries
        
        institutions = [('', '--------')] + [(i, i) for i in Alerta.objects.values_list('institution', flat=True).distinct().order_by('institution')]
        self.fields['institution'].choices = institutions
        
        source_types = [('', '--------')] + [(st, st) for st in Alerta.objects.values_list('source_type', flat=True).distinct().order_by('source_type')]
        self.fields['source_type'].choices = source_types
        
        categories = [('', '--------')] + [(c, c) for c in Alerta.objects.values_list('category', flat=True).distinct().order_by('category')]
        self.fields['category'].choices = categories


class CustomUserCreationForm(UserCreationForm):
    # Campo de email requerido y con validación de unicidad
    email = forms.EmailField(
        required=True,
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Ingrese su correo electrónico'
        })
    )
    
    # Campos para nombre y apellido
    first_name = forms.CharField(
        required=True,
        label="Nombre",
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Ingrese su nombre'
        })
    )
    
    last_name = forms.CharField(
        required=True,  # Cambiado a requerido
        label="Apellido",
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Ingrese su apellido'
        })
    )
    
    # Username opcional - se generará a partir del email
    username = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.HiddenInput()  # Oculto, ya que se generará automáticamente
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplicar clase form-control a todos los campos
        for fieldname in self.fields:
            self.fields[fieldname].widget.attrs.update({'class': 'form-control'})
    
    def clean_email(self):
        """Validar que el email sea único"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Este correo electrónico ya está en uso')
        return email
    
    def clean_password1(self):
        """Validación adicional de contraseña"""
        password1 = self.cleaned_data.get('password1')
        
        # Validar longitud mínima
        if password1 and len(password1) < 8:
            raise ValidationError('La contraseña debe tener al menos 8 caracteres')
        
        # Validar que contenga al menos un número
        if password1 and not any(char.isdigit() for char in password1):
            raise ValidationError('La contraseña debe contener al menos un número')
        
        # Validar que contenga al menos una letra
        if password1 and not any(char.isalpha() for char in password1):
            raise ValidationError('La contraseña debe contener al menos una letra')
        
        return password1

class CustomAuthenticationForm(AuthenticationForm):
    """
    Formulario de autenticación personalizado que solo permite iniciar sesión
    con correo electrónico
    """
    username = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Ingrese su correo electrónico'
        })
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Contraseña'
        })
    )

    def clean(self):
        email = self.cleaned_data.get('username')  # En realidad contiene el email
        password = self.cleaned_data.get('password')

        if email and password:
            # Buscar el usuario por email
            from django.contrib.auth.models import User
            try:
                user = User.objects.get(email=email)
                # Usar el nombre de usuario para la autenticación
                self.user_cache = authenticate(
                    self.request, 
                    username=user.username, 
                    password=password
                )
                
                if self.user_cache is None:
                    raise forms.ValidationError(
                        "Por favor, ingrese un correo y contraseña correctos. "
                        "Tenga en cuenta que ambos campos pueden distinguir mayúsculas y minúsculas.",
                        code='invalid_login',
                    )
                else:
                    self.confirm_login_allowed(self.user_cache)
            except User.DoesNotExist:
                raise forms.ValidationError(
                    "No existe una cuenta con este correo electrónico.",
                    code='email_not_found',
                )
            except User.MultipleObjectsReturned:
                raise forms.ValidationError(
                    "Hay un problema con tu cuenta. Por favor contacta al administrador.",
                    code='duplicate_email',
                )
        
        return self.cleaned_data