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
    PropertyImageForm,
    RealtorApplicationForm,
    RegistrationForm,
)
from .models import Property, Favorite, Inquiry, PropertyImage, RecentlyViewed, Realtor, PropertyType


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
            Property.objects.filter(
                featured=True, is_published=True
            ).select_related("property_type", "location").prefetch_related("images")
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
        ).select_related("property_type", "location").prefetch_related(
            "images"
        ).order_by(
            "-created_at"
        )[: self.HERO_COUNT]

        context["featured_properties"] = self.get_daily_featured_properties()

        context["property_types"] = PropertyType.objects.all()

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

        context["compare_property_ids"] = set(
            self.request.session.get("compare_property_ids", [])
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

        valid_property_types = set(
            PropertyType.objects.values_list("slug", flat=True)
        )
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
        queryset = Property.objects.filter(
            is_published=True
        ).select_related("property_type", "location").prefetch_related("images")

        filters = self.get_filter_values()
        location = filters["location"]
        property_type = filters["property_type"]
        listing_type = filters["listing_type"]

        if location:
            queryset = queryset.filter(
                Q(location__city__icontains=location)
                | Q(location__state__icontains=location)
                | Q(address__icontains=location)
            )

        if property_type:
            queryset = queryset.filter(property_type__slug=property_type)

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

        context["property_types"] = PropertyType.objects.all()
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

        context["compare_property_ids"] = set(
            self.request.session.get("compare_property_ids", [])
        )

        return context


class PropertyDetailView(DetailView):
    model = Property
    template_name = "pages/property-detail.html"
    context_object_name = "property"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        # Published listings are visible to everyone. An unpublished
        # (draft) listing is only visible to the realtor who owns it,
        # so they can preview it from their dashboard — everyone
        # else gets a 404, same as a listing that doesn't exist.
        queryset = Property.objects.select_related("property_type", "location")

        if self.request.user.is_authenticated:
            return queryset.filter(
                Q(is_published=True) | Q(realtor__user=self.request.user)
            )

        return queryset.filter(is_published=True)

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)

        # Record the view only after a successful load -- if the
        # queryset above already 404'd (unpublished, not the owner),
        # execution never reaches here, so nothing gets tracked for
        # a listing the user couldn't actually see.
        if request.user.is_authenticated:
            RecentlyViewed.objects.update_or_create(
                user=request.user,
                property=self.object,
            )

        return response

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

        context["recently_viewed"] = (
            RecentlyViewed.objects.filter(user=self.request.user)
            .select_related(
                "property", "property__property_type", "property__location"
            )[:10]
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

        form = RealtorApplicationForm(request.POST, request.FILES)

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


class RealtorProfileUpdateView(VerifiedRealtorRequiredMixin, UpdateView):
    model = Realtor
    form_class = RealtorApplicationForm
    template_name = "realtors/profile_form.html"
    login_url = reverse_lazy("login")

    def get_object(self, queryset=None):
        # A realtor only ever edits their own profile -- there's no
        # slug/pk in the URL for this one, it's always "you".
        return self.request.user.realtor_profile

    def get_success_url(self):
        messages.success(self.request, "Your profile has been updated.")
        return reverse_lazy("realtor-dashboard")


class RealtorDashboardView(VerifiedRealtorRequiredMixin, TemplateView):
    template_name = "realtors/dashboard.html"
    login_url = reverse_lazy("login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["properties"] = Property.objects.filter(
            realtor=self.request.user.realtor_profile
        ).select_related("property_type", "location")

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
        ).select_related("property_type", "location")

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


MAX_GALLERY_IMAGES = 12


class PropertyImageManageView(VerifiedRealtorRequiredMixin, TemplateView):
    template_name = "realtors/property_images.html"
    login_url = reverse_lazy("login")

    def get_property(self):
        return get_object_or_404(
            Property,
            slug=self.kwargs["slug"],
            realtor=self.request.user.realtor_profile,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        property_obj = self.get_property()
        context["property"] = property_obj
        context["images"] = property_obj.images.all()
        context["max_images"] = MAX_GALLERY_IMAGES
        context["at_limit"] = property_obj.images.count() >= MAX_GALLERY_IMAGES

        context["form"] = kwargs.get("form") or PropertyImageForm()

        return context

    def post(self, request, *args, **kwargs):
        property_obj = self.get_property()

        if property_obj.images.count() >= MAX_GALLERY_IMAGES:
            messages.error(
                request,
                f"You can add up to {MAX_GALLERY_IMAGES} photos per listing.",
            )
            return redirect("property-images", slug=property_obj.slug)

        form = PropertyImageForm(request.POST, request.FILES)

        if form.is_valid():
            gallery_image = form.save(commit=False)
            gallery_image.property = property_obj
            gallery_image.save()

            messages.success(request, "Photo added.")
            return redirect("property-images", slug=property_obj.slug)

        return self.render_to_response(self.get_context_data(form=form))


@require_POST
@login_required
def delete_property_image(request, slug, image_id):
    # Ownership check via the query itself: a realtor can only ever
    # delete a photo on their own listing -- anyone else (or an
    # unrelated image id) gets a plain 404, same as toggle_favorite
    # and update_inquiry_status do elsewhere in this file.
    property_obj = get_object_or_404(
        Property,
        slug=slug,
        realtor__user=request.user,
    )
    image = get_object_or_404(
        PropertyImage, pk=image_id, property=property_obj
    )
    image.delete()

    messages.success(request, "Photo removed.")
    return redirect("property-images", slug=property_obj.slug)


class RealtorListView(ListView):
    model = Realtor
    template_name = "pages/realtor_list.html"
    context_object_name = "realtors"
    paginate_by = 12

    def get_queryset(self):
        # Only verified realtors get a public profile -- a pending
        # application isn't something the public should see or be
        # able to browse to.
        return Realtor.objects.filter(
            is_verified=True
        ).select_related("user")


class RealtorPublicDetailView(DetailView):
    model = Realtor
    template_name = "pages/realtor_detail.html"
    context_object_name = "realtor"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Realtor.objects.filter(
            is_verified=True
        ).select_related("user")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["properties"] = Property.objects.filter(
            realtor=self.object, is_published=True
        ).select_related("property_type", "location").prefetch_related(
            "images"
        )

        return context


MAX_COMPARE_PROPERTIES = 3
COMPARE_SESSION_KEY = "compare_property_ids"


@require_POST
def toggle_compare(request, slug):
    property_obj = get_object_or_404(Property, slug=slug, is_published=True)

    compare_ids = request.session.get(COMPARE_SESSION_KEY, [])

    if property_obj.id in compare_ids:
        compare_ids.remove(property_obj.id)
        message = f'Removed "{property_obj.title}" from comparison.'
    else:
        if len(compare_ids) >= MAX_COMPARE_PROPERTIES:
            messages.error(
                request,
                f"You can compare up to {MAX_COMPARE_PROPERTIES} properties "
                "at a time. Remove one first.",
            )
            next_url = request.POST.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect(property_obj.get_absolute_url())

        compare_ids.append(property_obj.id)
        message = f'Added "{property_obj.title}" to comparison.'

    # Session values must be JSON-serializable and session changes
    # need to be flagged explicitly when mutating a mutable object
    # (like this list) in place, rather than reassigning it outright.
    request.session[COMPARE_SESSION_KEY] = compare_ids
    request.session.modified = True

    messages.success(request, message)

    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)

    return redirect(property_obj.get_absolute_url())


class CompareView(TemplateView):
    template_name = "pages/compare.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        compare_ids = self.request.session.get(COMPARE_SESSION_KEY, [])

        properties = list(
            Property.objects.filter(
                id__in=compare_ids, is_published=True
            ).select_related("property_type", "location", "realtor")
        )
        # filter() doesn't preserve the order properties were added in,
        # so re-sort to match the order in the session list.
        properties.sort(key=lambda p: compare_ids.index(p.id))

        context["properties"] = properties
        context["max_compare"] = MAX_COMPARE_PROPERTIES

        return context


@require_POST
def clear_compare(request):
    request.session[COMPARE_SESSION_KEY] = []
    request.session.modified = True

    messages.success(request, "Comparison cleared.")

    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)

    return redirect("property-list")


class AboutView(TemplateView):
    template_name = "pages/about.html"


class ContactView(TemplateView):
    template_name = "pages/contact.html"


class PropertyMapView(TemplateView):
    template_name = "pages/map.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["properties"] = Property.objects.filter(
            is_published=True,
            location__latitude__isnull=False,
            location__longitude__isnull=False,
        ).select_related("property_type", "location")

        return context