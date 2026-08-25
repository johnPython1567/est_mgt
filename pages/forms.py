from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Inquiry, Location, Property, Realtor


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
    # city/state are plain form fields, not Property model fields --
    # Property links to a Location instead. Keeping these as simple
    # text inputs preserves the exact same form UX (realtors type a
    # city and state like always); save() below resolves that to a
    # Location behind the scenes, creating one if it doesn't exist yet.
    city = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": INPUT_CLASSES}),
    )
    state = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": INPUT_CLASSES}),
    )

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
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Editing an existing property: prefill city/state from its
        # linked Location, since these aren't real Property fields
        # anymore and ModelForm can't prefill them automatically.
        if self.instance and self.instance.pk and self.instance.location_id:
            self.initial["city"] = self.instance.location.city
            self.initial["state"] = self.instance.location.state

    def save(self, commit=True):
        property_obj = super().save(commit=False)

        # Normalize casing so "lagos", "Lagos", and "LAGOS" all
        # resolve to the same Location instead of silently creating
        # near-duplicate rows every time someone types it differently.
        city = self.cleaned_data["city"].strip().title()
        state = self.cleaned_data["state"].strip().title()

        location = Location.objects.filter(
            city__iexact=city, state__iexact=state
        ).first()
        if location is None:
            location = Location.objects.create(
                name=f"{city}, {state}", city=city, state=state
            )
        property_obj.location = location

        if commit:
            property_obj.save()

        return property_obj