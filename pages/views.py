import random
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils.text import slugify
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.http import Http404, JsonResponse

from .forms import (
    InquiryForm,
    LoginForm,
    PropertyForm,
    RealtorApplicationForm,
    RegistrationForm,
)
from .models import Property, Favorite, Inquiry, Realtor


class HomeView(TemplateView):
    template_name = "pages/home.html"

    HERO_COUNT = 5
    FEATURED_COUNT = 6

    def get_daily_featured_properties(self):
        """Pick a rotating subset of featured properties, seeded by
        today's date. Everyone sees the same set on a given day, and
        it automatically changes at midnight without any scheduled
        task — no admin action needed to "refresh" the homepage."""
        featured = list(
            Property.objects.filter(featured=True, is_published=True)
        )

        rng = random.Random(date.today().isoformat())
        rng.shuffle(featured)

        return featured[: self.FEATURED_COUNT]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Explicit ordering (matches the model's default, but stated
        # here so "latest properties first" can't silently break if
        # Property.Meta.ordering ever changes).
        context["hero_properties"] = Property.objects.filter(
            is_published=True
        ).order_by("-created_at")[: self.HERO_COUNT]

        context["featured_properties"] = self.get_daily_featured_properties()

        context["property_types"] = Property.PROPERTY_TYPES

        context["favorite_property_ids"] = set()

        if self.request.user.is_authenticated:
            favorited_ids = list(context["hero_properties"]) + list(
                context["featured_properties"]
            )
            context["favorite_property_ids"] = set(
                Favorite.objects.filter(
                    user=self.request.user,
                    property__in=favorited_ids,
                ).values_list("property_id", flat=True)
            )
        return context

class PropertyListView(ListView):
    model = Property
    template_name = "pages/properties.html"
    context_object_name = "properties"
    paginate_by = 9

    ORDERING_CHOICES = {
        "newest": "-created_at",
        "oldest": "created_at",
        "price_asc": "price",
        "price_desc": "-price",
    }

    def _parse_decimal(self, raw):
        raw = (raw or "").strip()
        if not raw:
            return None
        try:
            value = Decimal(raw)
        except (InvalidOperation, ValueError):
            return None
        if value < 0:
            return None
        return value

    def _parse_positive_int(self, raw):
        raw = (raw or "").strip()
        if not raw:
            return None
        try:
            value = int(raw)
        except ValueError:
            return None
        if value < 0:
            return None
        return value

    def get_filter_values(self):
        """Return only valid, safe-to-display filter values."""
        location = self.request.GET.get("location", "").strip()[:100]
        property_type = self.request.GET.get("property_type", "")
        listing_type = self.request.GET.get("listing_type", "")
        ordering = self.request.GET.get("ordering", "newest")

        valid_property_types = {
            value for value, _ in Property.PROPERTY_TYPES
        }
        valid_listing_types = {
            value for value, _ in Property.LISTING_TYPES
        }

        min_price = self._parse_decimal(self.request.GET.get("min_price"))
        max_price = self._parse_decimal(self.request.GET.get("max_price"))

        # Don't let an inverted range silently return nothing confusing.
        if min_price is not None and max_price is not None and min_price > max_price:
            min_price, max_price = max_price, min_price

        return {
            "location": location,
            "property_type": (
                property_type if property_type in valid_property_types else ""
            ),
            "listing_type": (
                listing_type if listing_type in valid_listing_types else ""
            ),
            "min_price": min_price,
            "max_price": max_price,
            "bedrooms": self._parse_positive_int(self.request.GET.get("bedrooms")),
            "bathrooms": self._parse_positive_int(self.request.GET.get("bathrooms")),
            "ordering": (
                ordering if ordering in self.ORDERING_CHOICES else "newest"
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

        if filters["min_price"] is not None:
            queryset = queryset.filter(price__gte=filters["min_price"])

        if filters["max_price"] is not None:
            queryset = queryset.filter(price__lte=filters["max_price"])

        if filters["bedrooms"] is not None:
            queryset = queryset.filter(bedrooms__gte=filters["bedrooms"])

        if filters["bathrooms"] is not None:
            queryset = queryset.filter(bathrooms__gte=filters["bathrooms"])

        queryset = queryset.order_by(
            self.ORDERING_CHOICES[filters["ordering"]]
        )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = self.get_filter_values()

        # Ordering defaults to "newest" even with no other filters active,
        # so exclude it from the "are any filters active" check.
        active_filter_values = {
            key: value for key, value in filters.items() if key != "ordering"
        }

        context["property_types"] = Property.PROPERTY_TYPES
        context["listing_types"] = Property.LISTING_TYPES
        context["ordering_choices"] = [
            ("newest", "Newest first"),
            ("oldest", "Oldest first"),
            ("price_asc", "Price: low to high"),
            ("price_desc", "Price: high to low"),
        ]
        context["selected_filters"] = filters
        context["has_active_filters"] = any(active_filter_values.values())

        # Preserve every filter (minus "page") across pagination links.
        querystring = self.request.GET.copy()
        querystring.pop("page", None)
        context["querystring"] = querystring.urlencode()

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


def generate_unique_slug(title, exclude_pk=None):
    base_slug = slugify(title)[:190] or "property"
    slug = base_slug
    counter = 1

    queryset = Property.objects.all()
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)

    while queryset.filter(slug=slug).exists():
        counter += 1
        slug = f"{base_slug}-{counter}"

    return slug


class VerifiedRealtorRequiredMixin(LoginRequiredMixin):
    """Only lets verified realtors through; everyone else is sent to
    the application page, whether they haven't applied yet or are
    still waiting on approval."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            realtor_profile = getattr(request.user, "realtor_profile", None)

            if not realtor_profile or not realtor_profile.is_verified:
                messages.error(
                    request,
                    "You need an approved realtor account to access this page.",
                )
                return redirect("realtor-apply")

        return super().dispatch(request, *args, **kwargs)


class RealtorApplyView(LoginRequiredMixin, TemplateView):
    template_name = "realtors/apply.html"
    login_url = reverse_lazy("login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["realtor_profile"] = getattr(
            self.request.user, "realtor_profile", None
        )

        if not context["realtor_profile"] and "form" not in context:
            context["form"] = RealtorApplicationForm()

        return context

    def post(self, request, *args, **kwargs):
        if getattr(request.user, "realtor_profile", None):
            messages.info(
                request, "You have already applied to become a realtor."
            )
            return redirect("realtor-apply")

        form = RealtorApplicationForm(request.POST)

        if form.is_valid():
            realtor = form.save(commit=False)
            realtor.user = request.user
            realtor.save()

            messages.success(
                request,
                "Your realtor application has been submitted for review.",
            )
            return redirect("realtor-apply")

        return self.render_to_response(self.get_context_data(form=form))


class RealtorDashboardView(VerifiedRealtorRequiredMixin, TemplateView):
    template_name = "realtors/dashboard.html"
    login_url = reverse_lazy("login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["properties"] = Property.objects.filter(
            realtor=self.request.user.realtor_profile
        )

        context["new_inquiry_count"] = Inquiry.objects.filter(
            property__realtor=self.request.user.realtor_profile,
            status="new",
        ).count()
        return context


class PropertyCreateView(VerifiedRealtorRequiredMixin, CreateView):
    model = Property
    form_class = PropertyForm
    template_name = "realtors/property_form.html"
    login_url = reverse_lazy("login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = False
        return context

    def form_valid(self, form):
        property_obj = form.save(commit=False)
        property_obj.realtor = self.request.user.realtor_profile
        property_obj.slug = generate_unique_slug(property_obj.title)
        property_obj.save()

        messages.success(self.request, "Listing created.")
        return redirect("realtor-dashboard")


class PropertyUpdateView(VerifiedRealtorRequiredMixin, UpdateView):
    model = Property
    form_class = PropertyForm
    template_name = "realtors/property_form.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    login_url = reverse_lazy("login")

    def get_queryset(self):
        # A realtor may only edit their own listings.
        return Property.objects.filter(
            realtor=self.request.user.realtor_profile
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True
        return context

    def form_valid(self, form):
        # Keep the slug stable on edit so existing links/favorites
        # to this property keep working.
        property_obj = form.save(commit=False)
        property_obj.slug = self.object.slug
        property_obj.save()

        messages.success(self.request, "Listing updated.")
        return redirect("realtor-dashboard")


class RealtorInquiryListView(VerifiedRealtorRequiredMixin, ListView):
    model = Inquiry
    template_name = "realtors/inquiries.html"
    context_object_name = "inquiries"
    login_url = reverse_lazy("login")

    STATUS_FILTER_CHOICES = Inquiry.STATUS_CHOICES

    def get_queryset(self):
        queryset = Inquiry.objects.filter(
            property__realtor=self.request.user.realtor_profile
        ).select_related("property")

        status = self.request.GET.get("status", "")
        valid_statuses = {value for value, _ in Inquiry.STATUS_CHOICES}

        if status in valid_statuses:
            queryset = queryset.filter(status=status)

        return queryset
    
    def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context["status_choices"] = self.STATUS_FILTER_CHOICES
            context["selected_status"] = self.request.GET.get("status", "")
            return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = self.STATUS_FILTER_CHOICES
        context["selected_status"] = self.request.GET.get("status", "")
        return context


@require_POST
@login_required
def update_inquiry_status(request, pk):
    inquiry = get_object_or_404(
        Inquiry.objects.select_related("property__realtor"),
        pk=pk,
    )

    # Ownership check: a realtor may only update the status of
    # inquiries on their own listings, not anyone else's.
    realtor_profile = getattr(request.user, "realtor_profile", None)
    if not realtor_profile or inquiry.property.realtor_id != realtor_profile.id:
        raise Http404

    new_status = request.POST.get("status")
    valid_statuses = {value for value, _ in Inquiry.STATUS_CHOICES}

    if new_status in valid_statuses:
        inquiry.status = new_status
        inquiry.save(update_fields=["status", "updated_at"])
        messages.success(request, "Inquiry status updated.")
    else:
        messages.error(request, "That isn't a valid status.")

    return redirect("realtor-inquiries")