const countdown = document.getElementById("countdown");

const targetDate = new Date("2026-07-23T10:00:00+01:00").getTime();

function renderCountdown() {
    if (!countdown) {
        return;
    }

    const now = new Date().getTime();
    const difference = targetDate - now;

    if (difference <= 0) {
        countdown.innerHTML = `
            <div class="countdown-item">
                <span>0</span>
                <small>days</small>
            </div>
            <div class="countdown-item">
                <span>0</span>
                <small>hours</small>
            </div>
            <div class="countdown-item">
                <span>0</span>
                <small>mins</small>
            </div>
        `;
        return;
    }

    const days = Math.floor(difference / (1000 * 60 * 60 * 24));

    const hours = Math.floor(
        (difference % (1000 * 60 * 60 * 24)) /
        (1000 * 60 * 60)
    );

    const minutes = Math.floor(
        (difference % (1000 * 60 * 60)) /
        (1000 * 60)
    );

    countdown.innerHTML = `
        <div class="countdown-item">
            <span>${days}</span>
            <small>days</small>
        </div>
        <div class="countdown-item">
            <span>${hours}</span>
            <small>hours</small>
        </div>
        <div class="countdown-item">
            <span>${minutes}</span>
            <small>mins</small>
        </div>
    `;
}

renderCountdown();
setInterval(renderCountdown, 60000);
