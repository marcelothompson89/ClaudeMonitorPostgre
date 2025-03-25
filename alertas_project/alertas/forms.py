# alertas/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Alerta, Keyword, EmailAlertConfig

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
    
    page_size = forms.IntegerField(
        min_value=10,
        max_value=100,
        initial=50,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
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
        source_types = [('', '--------')] + [(st, st) for st in Alerta.objects.values_list('source_type', flat=True).distinct().order_by('source_type')]
        categories = [('', '--------')] + [(c, c) for c in Alerta.objects.values_list('category', flat=True).distinct().order_by('category')]
        countries = [('', '--------')] + [(c, c) for c in Alerta.objects.values_list('country', flat=True).distinct().order_by('country')]
        institutions = [('', '--------')] + [(i, i) for i in Alerta.objects.values_list('institution', flat=True).distinct().order_by('institution')]
        
        self.fields['source_type'].choices = source_types
        self.fields['category'].choices = categories
        self.fields['country'].choices = countries
        self.fields['institution'].choices = institutions