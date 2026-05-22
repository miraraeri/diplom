from django import forms
from .models import *


class BidFilterForm(forms.Form):
    status = forms.ChoiceField(
        choices=[('', 'Все заявки')] + Bids.STATUSES,
        required=False,
        label=''
    )
    search = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(attrs={'placeholder': 'Поиск', 'id': 'search'})
    )


class ComponentFilterForm(forms.Form):
    hardware = forms.ModelChoiceField(
        queryset=Categories.objects.all(),
        required=False,
        empty_label='Все комплектующие'
    )
    search = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(attrs={'placeholder': 'Поиск', 'id': 'search'})
    )


class CreateBidForm(forms.ModelForm):
    class Meta:
        model = Bids
        fields = ['problem_text']
        widgets = {
            'problem_text': forms.Textarea(attrs={'placeholder': 'Описание проблемы'}),
        }


class AuthForm(forms.Form):
    contacts = forms.CharField(
        label='Контакты',
        required=True,
        widget=forms.TelInput(attrs={'placeholder': 'Введите номер телефона'})
        )
    password = forms.CharField(
        label='Пароль',
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Введите пароль'})
    )


class ResolutionForm(forms.ModelForm):
    class Meta:
        model = Bids
        fields = ['resolution']
        widgets = {
            'resolution': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Краткое описание решения...'}),
        }
