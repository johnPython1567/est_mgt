from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Inquiry, Property, Realtor


INPUT_CLASSES = (
    "w-full rounded-lg border border-[#CBD5E1] px-4 py-3 text-[#172033] "
    "placeholder-[#94A3B8] focus:border-[#12283F] focus:ring-[#12283F]"
)


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = INPUT_CLASSES

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        user_model = get_user_model()

        if user_model.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account already exists with this email address."
            )

        return email


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = INPUT_CLASSES



class InquiryForm(forms.ModelForm):
    class Meta:
        model = Inquiry
        fields = ["name", "email", "phone", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CLASSES}),
            "email": forms.EmailInput(attrs={"class": INPUT_CLASSES}),
            "phone": forms.TextInput(attrs={"class": INPUT_CLASSES}),
            "message": forms.Textarea(
                attrs={"class": INPUT_CLASSES, "rows": 4}
            ),
        }

class RealtorApplicationForm(forms.ModelForm):
    class Meta:
        model = Realtor
        fields = ["bio", "phone", "agency"]
        widgets = {
            "bio": forms.Textarea(
                attrs={
                    "class": INPUT_CLASSES,
                    "rows": 4,
                    "placeholder": "Tell us about your experience...",
                }
            ),
            "phone": forms.TextInput(attrs={"class": INPUT_CLASSES}),
            "agency": forms.TextInput(attrs={"class": INPUT_CLASSES}),
        }


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            "title",
            "description",
            "property_type",
            "listing_type",
            "price",
            "bedrooms",
            "bathrooms",
            "area",
            "address",
            "city",
            "state",
            "image",
            "is_published",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": INPUT_CLASSES}),
            "description": forms.Textarea(
                attrs={"class": INPUT_CLASSES, "rows": 5}
            ),
            "property_type": forms.Select(attrs={"class": INPUT_CLASSES}),
            "listing_type": forms.Select(attrs={"class": INPUT_CLASSES}),
            "price": forms.NumberInput(attrs={"class": INPUT_CLASSES}),
            "bedrooms": forms.NumberInput(attrs={"class": INPUT_CLASSES}),
            "bathrooms": forms.NumberInput(attrs={"class": INPUT_CLASSES}),
            "area": forms.NumberInput(attrs={"class": INPUT_CLASSES}),
            "address": forms.TextInput(attrs={"class": INPUT_CLASSES}),
            "city": forms.TextInput(attrs={"class": INPUT_CLASSES}),
            "state": forms.TextInput(attrs={"class": INPUT_CLASSES}),
        }