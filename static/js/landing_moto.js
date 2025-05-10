
document.addEventListener('DOMContentLoaded', function() {
    const motoElement = document.getElementById('dynamic-moto');
    if (!motoElement) return;

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
    const typingSpeed = 100; 
    const deletingSpeed = 50; 
    const delayBetweenMotos = 1500; 

    function typeWriter() {
        const currentMoto = motos[currentMotoIndex];
        let displayedText = '';

        if (isDeleting) {
           
            displayedText = currentMoto.substring(0, currentCharIndex - 1);
            currentCharIndex--;
        } else {
            
            displayedText = currentMoto.substring(0, currentCharIndex + 1);
            currentCharIndex++;
        }

        motoElement.textContent = displayedText;

        let currentSpeed = isDeleting ? deletingSpeed : typingSpeed;

        
        if (!isDeleting && currentCharIndex === currentMoto.length) {
            
            currentSpeed = delayBetweenMotos; 
            isDeleting = true;
        } else if (isDeleting && currentCharIndex === 0) {
            
            isDeleting = false;
            currentMotoIndex = (currentMotoIndex + 1) % motos.length; 
            currentSpeed = typingSpeed; 
        }

        setTimeout(typeWriter, currentSpeed);
    }

    
    setTimeout(typeWriter, typingSpeed);
});
