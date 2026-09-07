// Hero photo carousel: crossfades through event photos, with dot navigation.
// Progressive loading: only the first slide has a real `src` on page load;
// every other slide loads via `data-src` just before it's needed, so a mobile
// visitor never pays for all 13 photos up front -- only the ones they see.
(function () {
    var ADVANCE_MS = 5000;

    document.addEventListener('DOMContentLoaded', function () {
        var carousel = document.getElementById('heroCarousel');
        if (!carousel) return;

        var slides = Array.prototype.slice.call(carousel.querySelectorAll('.hero-carousel-slide'));
        var dots = Array.prototype.slice.call(carousel.querySelectorAll('.hero-carousel-dot'));
        if (slides.length < 2) return;

        var current = 0;
        var timer = null;

        function loadSlide(index) {
            var img = slides[index];
            if (img && img.dataset.src) {
                img.src = img.dataset.src;
                delete img.dataset.src;
            }
        }

        function goTo(index) {
            slides[current].classList.remove('is-active');
            if (dots[current]) {
                dots[current].classList.remove('is-active');
                dots[current].setAttribute('aria-selected', 'false');
            }

            current = (index + slides.length) % slides.length;

            loadSlide(current);
            slides[current].classList.add('is-active');
            if (dots[current]) {
                dots[current].classList.add('is-active');
                dots[current].setAttribute('aria-selected', 'true');
            }

            // Preload the next slide now, so it's ready before its turn comes.
            loadSlide((current + 1) % slides.length);
        }

        function next() {
            goTo(current + 1);
        }

        function startAuto() {
            stopAuto();
            timer = setInterval(next, ADVANCE_MS);
        }

        function stopAuto() {
            if (timer) clearInterval(timer);
            timer = null;
        }

        dots.forEach(function (dot) {
            dot.addEventListener('click', function () {
                goTo(parseInt(dot.dataset.index, 10));
                startAuto(); // reset the countdown so it doesn't jump again immediately
            });
        });

        carousel.addEventListener('mouseenter', stopAuto);
        carousel.addEventListener('mouseleave', startAuto);

        // Get the second slide ready to go, then start cycling.
        loadSlide(1);
        startAuto();
    });
})();
