const quotes = [
    "A much-needed space for policy practitioners to learn from each other.",
    "Exactly the kind of open, practical conversation policy teams need more of.",
    "A rare chance to step outside formal structures and work through real challenges together.",
    "Collaborative, participant-led, and focused on the topics people actually care about."
];

const quoteElement = document.getElementById("rotating-quote");

let currentQuote = 0;

function rotateQuote() {

    if (!quoteElement) {
        return;
    }

    quoteElement.style.opacity = "0";

    setTimeout(() => {

        quoteElement.textContent = quotes[currentQuote];

        quoteElement.style.opacity = "1";

        currentQuote += 1;

        if (currentQuote >= quotes.length) {
            currentQuote = 0;
        }

    }, 120);
}

rotateQuote();

setInterval(rotateQuote, 4000);
