from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, TemplateView
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from .forms import InquiryForm, LoginForm, RegistrationForm
from .models import Property, Favorite, Inquiry


class HomeView(TemplateView):
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["hero_properties"] = Property.objects.filter(
            is_published=True
        )[:5]

        context["featured_properties"] = Property.objects.filter(
            featured=True,
            is_published=True
        )[:6]
        context["property_types"] = Property.PROPERTY_TYPES

        context["favorite_property_ids"] = set()

        if self.request.user.is_authenticated:
            context["favorite_property_ids"] = set(
                Favorite.objects.filter(
                    user=self.request.user,
                    property__in=context["featured_properties"],
                ).values_list("property_id", flat=True)
            )
        return context

class PropertyListView(ListView):
    model = Property
    template_name = "pages/properties.html"
    context_object_name = "properties"

    def get_filter_values(self):
        """Return only valid, safe-to-display filter values."""
        location = self.request.GET.get("location", "").strip()[:100]
        property_type = self.request.GET.get("property_type", "")
        listing_type = self.request.GET.get("listing_type", "")

        valid_property_types = {
            value for value, _ in Property.PROPERTY_TYPES
        }
        valid_listing_types = {
            value for value, _ in Property.LISTING_TYPES
        }

        return {
            "location": location,
            "property_type": (
                property_type if property_type in valid_property_types else ""
            ),
            "listing_type": (
                listing_type if listing_type in valid_listing_types else ""
            ),
        }

    def get_queryset(self):
        queryset = Property.objects.filter(is_published=True)

        filters = self.get_filter_values()
        location = filters["location"]
        property_type = filters["property_type"]
        listing_type = filters["listing_type"]

        if location:
            queryset = queryset.filter(
                Q(city__icontains=location)
                | Q(state__icontains=location)
                | Q(address__icontains=location)
            )

        if property_type:
            queryset = queryset.filter(property_type=property_type)

        if listing_type:
            queryset = queryset.filter(listing_type=listing_type)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = self.get_filter_values()

        context["property_types"] = Property.PROPERTY_TYPES
        context["listing_types"] = Property.LISTING_TYPES
        context["selected_filters"] = filters
        context["has_active_filters"] = any(filters.values())

        context["favorite_property_ids"] = set()

        if self.request.user.is_authenticated:
            context["favorite_property_ids"] = set(
                Favorite.objects.filter(
                    user=self.request.user,
                    property__in=context["properties"],
                ).values_list("property_id", flat=True)
            )

        return context


class PropertyDetailView(DetailView):
    model = Property
    template_name = "pages/property-detail.html"
    context_object_name = "property"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["is_favorited"] = False

        if self.request.user.is_authenticated:
            context["is_favorited"] = Favorite.objects.filter(
                user=self.request.user,
                property=self.object,
            ).exists()

        initial = {}
        if self.request.user.is_authenticated:
            initial["name"] = (
                self.request.user.get_full_name()
                or self.request.user.username
            )
            initial["email"] = self.request.user.email

        context["inquiry_form"] = InquiryForm(initial=initial)

        return context


class RegisterView(TemplateView):
    template_name = "accounts/register.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("profile")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = RegistrationForm()
        return context

    def post(self, request, *args, **kwargs):
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Your account has been created.")
            return redirect("profile")

        return self.render_to_response({"form": form})


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("home")


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"
    login_url = reverse_lazy("login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["favorites"] = (
            Favorite.objects.filter(user=self.request.user)
            .select_related("property")
        )

        context["inquiries"] = (
            Inquiry.objects.filter(user=self.request.user)
            .select_related("property")
        )

        return context


@require_POST
@login_required
def toggle_favorite(request, slug):
    property_obj = get_object_or_404(
        Property,
        slug=slug,
        is_published=True,
    )

    favorite, created = Favorite.objects.get_or_create(
        user=request.user,
        property=property_obj,
    )

    if created:
        message = "Property saved to your favorites."
    else:
        favorite.delete()
        message = "Property removed from your favorites."

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {
                "is_favorited": created,
                "message": message,
            }
        )

    messages.success(request, message)

    next_url = request.POST.get("next")

    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)

    return redirect(property_obj.get_absolute_url())


class InquiryCreateView(CreateView):
    model = Inquiry
    form_class = InquiryForm
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        self.property_obj = get_object_or_404(
            Property,
            slug=request.POST.get("property"),
            is_published=True,
        )
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        inquiry = form.save(commit=False)
        inquiry.property = self.property_obj

        if self.request.user.is_authenticated:
            inquiry.user = self.request.user

        inquiry.save()

        messages.success(
            self.request,
            "Your inquiry has been sent. The realtor will be in touch shortly.",
        )

        return redirect(self.property_obj.get_absolute_url())

    def form_invalid(self, form):
        for error_list in form.errors.values():
            for error in error_list:
                messages.error(self.request, error)

        return redirect(self.property_obj.get_absolute_url())    
