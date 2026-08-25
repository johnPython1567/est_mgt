console.log("EST-MGT slider JavaScript loaded");

const slides = document.querySelectorAll(".hero-slide");
const dots = document.querySelectorAll(".hero-dot");

console.log("Slides:", slides.length);
console.log("Dots:", dots.length);

let currentSlide = 0;
let sliderTimer = null;


function showSlide(index) {

    if (slides.length === 0) {
        return;
    }

    slides.forEach((slide, slideIndex) => {

        if (slideIndex === index) {
            slide.classList.remove("opacity-0");
            slide.classList.add("opacity-100");
        } else {
            slide.classList.remove("opacity-100");
            slide.classList.add("opacity-0");
        }

    });


    dots.forEach((dot, dotIndex) => {

        if (dotIndex === index) {
            dot.classList.remove("bg-white/60");
            dot.classList.add("bg-white");
        } else {
            dot.classList.remove("bg-white");
            dot.classList.add("bg-white/60");
        }

    });


    currentSlide = index;
}


function nextSlide() {

    const nextIndex =
        (currentSlide + 1) % slides.length;

    showSlide(nextIndex);

}


function startSlider() {

    if (slides.length <= 1) {
        return;
    }

    sliderTimer = setInterval(() => {
        nextSlide();
    }, 5000);

}


function restartSlider() {

    if (sliderTimer) {
        clearInterval(sliderTimer);
    }

    startSlider();

}


dots.forEach((dot) => {

    dot.addEventListener("click", () => {

        const slideIndex =
            Number(dot.dataset.slideTo);

        showSlide(slideIndex);

        restartSlider();

    });

});


showSlide(0);
startSlider();

const siteMessages = document.querySelectorAll("[data-site-message]");

siteMessages.forEach((message) => {
    window.setTimeout(() => {
        message.style.transition = "opacity 300ms ease";
        message.style.opacity = "0";
    }, 4000);

    window.setTimeout(() => {
        message.remove();
    }, 4300);
});


function showFavoriteToast(message) {
    const toast = document.createElement("div");

    toast.textContent = message;

    Object.assign(toast.style, {
        position: "fixed",
        top: "1.5rem",
        right: "1.5rem",
        zIndex: "50",
        maxWidth: "20rem",
        padding: "0.75rem 1rem",
        border: "1px solid #BBF7D0",
        borderRadius: "0.5rem",
        backgroundColor: "#F0FDF4",
        color: "#166534",
        fontWeight: "600",
        fontSize: "0.875rem",
        boxShadow: "0 10px 25px rgba(15, 23, 42, 0.12)",
        transition: "opacity 300ms ease",
    });

    document.body.append(toast);

    window.setTimeout(() => {
        toast.style.opacity = "0";
    }, 4000);

    window.setTimeout(() => {
        toast.remove();
    }, 4300);
}


function updateFavoriteButton(button, isFavorited) {
    const isTextButton = button.dataset.favoriteKind === "text";

    button.setAttribute(
        "aria-label",
        isFavorited
            ? button.dataset.removeLabel
            : button.dataset.addLabel,
    );

    if (isTextButton) {
        button.textContent = isFavorited
            ? "♥ " + button.dataset.removeLabel
            : "♡ " + button.dataset.addLabel;

        button.classList.toggle("border-[#DC2626]", isFavorited);
        button.classList.toggle("text-[#DC2626]", isFavorited);
        button.classList.toggle("border-[#E2E8F0]", !isFavorited);
        button.classList.toggle("text-[#12283F]", !isFavorited);

        return;
    }

    button.textContent = isFavorited ? "♥" : "♡";

    button.classList.toggle("text-[#DC2626]", isFavorited);
    button.classList.toggle("text-[#94A3B8]", !isFavorited);
    button.classList.toggle("hover:text-[#DC2626]", !isFavorited);
}


document.querySelectorAll("[data-favorite-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const propertySlug = form.dataset.propertySlug;
        const matchingForms = document.querySelectorAll(
            `[data-favorite-form][data-property-slug="${propertySlug}"]`,
        );

        const matchingButtons = Array.from(matchingForms)
            .map((matchingForm) =>
                matchingForm.querySelector("[data-favorite-button]"),
            )
            .filter(Boolean);

        matchingButtons.forEach((button) => {
            button.disabled = true;
            button.setAttribute("aria-busy", "true");
        });

        try {
            const response = await fetch(form.action, {
                method: "POST",
                body: new FormData(form),
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            if (response.redirected) {
                window.location.assign(response.url);
                return;
            }

            if (!response.ok) {
                throw new Error("Favorite request failed.");
            }

            const data = await response.json();

            matchingButtons.forEach((button) => {
                updateFavoriteButton(button, data.is_favorited);
            });

            showFavoriteToast(data.message);
        } catch (error) {
            showFavoriteToast(
                "We could not update this favorite. Please try again.",
            );
        } finally {
            matchingButtons.forEach((button) => {
                button.disabled = false;
                button.removeAttribute("aria-busy");
            });
        }
    });
});


const inquiryModal = document.querySelector("[data-inquiry-modal]");

if (inquiryModal) {
    const openButtons = document.querySelectorAll("[data-inquiry-open]");
    const closeButtons = inquiryModal.querySelectorAll(
        "[data-inquiry-close]",
    );
    const backdrop = inquiryModal.querySelector("[data-inquiry-backdrop]");

    function openInquiryModal() {
        inquiryModal.hidden = false;
        const firstField = inquiryModal.querySelector("input, textarea");
        if (firstField) {
            firstField.focus();
        }
    }

    function closeInquiryModal() {
        inquiryModal.hidden = true;
    }

    openButtons.forEach((button) => {
        button.addEventListener("click", openInquiryModal);
    });

    closeButtons.forEach((button) => {
        button.addEventListener("click", closeInquiryModal);
    });

    if (backdrop) {
        backdrop.addEventListener("click", closeInquiryModal);
    }

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !inquiryModal.hidden) {
            closeInquiryModal();
        }
    });
}

const mobileMenuToggle = document.querySelector("[data-mobile-menu-toggle]");
const mobileMenu = document.querySelector("[data-mobile-menu]");

if (mobileMenuToggle && mobileMenu) {
    function openMobileMenu() {
        mobileMenu.hidden = false;
        mobileMenuToggle.setAttribute("aria-expanded", "true");
        mobileMenuToggle.textContent = "✕";
    }

    function closeMobileMenu() {
        mobileMenu.hidden = true;
        mobileMenuToggle.setAttribute("aria-expanded", "false");
        mobileMenuToggle.textContent = "☰";
    }

    mobileMenuToggle.addEventListener("click", () => {
        if (mobileMenu.hidden) {
            openMobileMenu();
        } else {
            closeMobileMenu();
        }
    });

    // Close automatically if the viewport grows past the mobile
    // breakpoint (e.g. rotating a tablet, resizing a browser window)
    // so the panel doesn't stay stuck open behind the desktop nav.
    const desktopBreakpoint = window.matchMedia("(min-width: 768px)");
    desktopBreakpoint.addEventListener("change", (event) => {
        if (event.matches) {
            closeMobileMenu();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !mobileMenu.hidden) {
            closeMobileMenu();
        }
    });
}