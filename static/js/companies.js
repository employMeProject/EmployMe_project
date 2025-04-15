document.addEventListener('DOMContentLoaded', function() {
    const carousel = document.querySelector('.vertical-carousel');
    const cards = document.querySelectorAll('.company-card');
    const prevBtn = document.querySelector('.prev-btn');
    const nextBtn = document.querySelector('.next-btn');
    
    let currentIndex = 0;
    const cardHeight = cards[0].offsetHeight;
    const visibleCards = Math.floor(carousel.offsetHeight / cardHeight);
    
    function updateCarousel() {
        const offset = -currentIndex * cardHeight;
        carousel.style.transform = `translateY(${offset}px)`;
        
        // Блокируем кнопки, если достигли границ
        prevBtn.disabled = currentIndex === 0;
        nextBtn.disabled = currentIndex >= cards.length - visibleCards;
    }
    
    prevBtn.addEventListener('click', function() {
        if (currentIndex > 0) {
            currentIndex--;
            updateCarousel();
        }
    });
    
    nextBtn.addEventListener('click', function() {
        if (currentIndex < cards.length - visibleCards) {
            currentIndex++;
            updateCarousel();
        }
    });
    
    // Инициализация
    updateCarousel();
    
    // Добавляем обработчики для свайпов (опционально)
    let startY;
    
    carousel.addEventListener('touchstart', function(e) {
        startY = e.touches[0].clientY;
    });
    
    carousel.addEventListener('touchmove', function(e) {
        if (!startY) return;
        
        const y = e.touches[0].clientY;
        const diff = startY - y;
        
        if (diff > 50 && currentIndex < cards.length - visibleCards) {
            // Свайп вверх
            currentIndex++;
            updateCarousel();
            startY = null;
        } else if (diff < -50 && currentIndex > 0) {
            // Свайп вниз
            currentIndex--;
            updateCarousel();
            startY = null;
        }
    });
});