// Simple Javascript typewriter effect for the landing page moto
document.addEventListener('DOMContentLoaded', function() {
    const motoElement = document.getElementById('dynamic-moto');
    if (!motoElement) return; // Exit if element not found

    const motos = [
        "Keeping our campus clean and functional...",
        "Report issues quickly and easily.",
        "Efficient resolution, better environment.",
        "Your feedback helps us improve.",
        "Together, we make a difference."
    ];
    let currentMotoIndex = 0;
    let currentCharIndex = 0;
    let isDeleting = false;
    const typingSpeed = 100; // Speed of typing
    const deletingSpeed = 50; // Speed of deleting
    const delayBetweenMotos = 1500; // Pause after typing a moto

    function typeWriter() {
        const currentMoto = motos[currentMotoIndex];
        let displayedText = '';

        if (isDeleting) {
            // Deleting text
            displayedText = currentMoto.substring(0, currentCharIndex - 1);
            currentCharIndex--;
        } else {
            // Typing text
            displayedText = currentMoto.substring(0, currentCharIndex + 1);
            currentCharIndex++;
        }

        motoElement.textContent = displayedText;

        let currentSpeed = isDeleting ? deletingSpeed : typingSpeed;

        // Check conditions to switch state or moto
        if (!isDeleting && currentCharIndex === currentMoto.length) {
            // Finished typing current moto
            currentSpeed = delayBetweenMotos; // Pause before deleting
            isDeleting = true;
        } else if (isDeleting && currentCharIndex === 0) {
            // Finished deleting current moto
            isDeleting = false;
            currentMotoIndex = (currentMotoIndex + 1) % motos.length; // Move to next moto
            currentSpeed = typingSpeed; // Start typing next one immediately
        }

        setTimeout(typeWriter, currentSpeed);
    }

    // Start the effect
    setTimeout(typeWriter, typingSpeed);
});