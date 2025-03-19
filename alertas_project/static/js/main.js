document.addEventListener('DOMContentLoaded', function() {
    // Smooth scrolling para los enlaces internos
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                window.scrollTo({
                    top: target.offsetTop - 70,
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Navbar transparente al inicio y con color al hacer scroll
    const navbar = document.querySelector('.navbar');
    
    if (navbar) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 50) {
                navbar.classList.add('navbar-scrolled');
            } else {
                navbar.classList.remove('navbar-scrolled');
            }
        });
    }
    
    // Animación para los elementos al hacer scroll
    const animateElements = document.querySelectorAll('.animate-on-scroll');
    
    function checkScroll() {
        animateElements.forEach(element => {
            const elementTop = element.getBoundingClientRect().top;
            const elementVisible = 150;
            
            if (elementTop < window.innerHeight - elementVisible) {
                element.classList.add('animate');
            }
        });
    }
    
    // Ejecutar al cargar y al hacer scroll
    if (animateElements.length > 0) {
        window.addEventListener('scroll', checkScroll);
        checkScroll();
    }
    
    // Contador para estadísticas
    const statCounters = document.querySelectorAll('.stat-counter');
    
    function startCounting() {
        statCounters.forEach(counter => {
            const target = parseInt(counter.getAttribute('data-target'));
            const duration = 2000; // 2 segundos
            const step = Math.ceil(target / (duration / 30)); // 30 FPS
            
            let current = 0;
            const timer = setInterval(() => {
                current += step;
                counter.textContent = current;
                
                if (current >= target) {
                    counter.textContent = target.toLocaleString();
                    clearInterval(timer);
                }
            }, 30);
        });
    }
    
    // Iniciar contadores cuando son visibles
    if (statCounters.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    startCounting();
                    observer.disconnect();
                }
            });
        });
        
        if (document.querySelector('.stats-section')) {
            observer.observe(document.querySelector('.stats-section'));
        }
    }
    
    // CÓDIGO MEJORADO: Manejo de imágenes de logos institucionales
    const institutionLogos = document.querySelectorAll('.institution-logo-img');
    
    // Función para manejar errores de carga de imágenes
    function handleImageError(img) {
        img.style.display = 'none';
        // Buscar el elemento de texto alternativo y mostrarlo
        const textLogo = img.nextElementSibling;
        if (textLogo && textLogo.classList.contains('logo-text')) {
            textLogo.style.display = 'flex';
        }
    }
    
    // Función para ajustar tamaño de imágenes
    function adjustImageSize(img) {
        // Si la imagen ya está cargada
        if (img.complete && img.naturalHeight !== 0) {
            checkImageProportions(img);
        } else {
            // Si la imagen aún no está cargada, esperar al evento load
            img.addEventListener('load', function() {
                checkImageProportions(img);
            });
        }
    }
    
    // Verificar proporciones de la imagen y aplicar clases según corresponda
    function checkImageProportions(img) {
        // Si es un emblema nacional específico
        if (img.src.includes('brasil') || img.src.includes('escudo-nacional')) {
            img.classList.add('logo-national-emblem');
        } 
        // Si la imagen es más cuadrada que rectangular
        else if (img.naturalWidth / img.naturalHeight > 0.8) {
            img.classList.add('logo-emblem');
        }
        
        // Ajustar aún más si la imagen es excesivamente grande
        if (img.naturalWidth > 100 || img.naturalHeight > 100) {
            // Reducir más si la imagen es muy grande
            img.style.maxWidth = '24px';
            img.style.maxHeight = '24px';
        }
    }
    
    // Aplicar a todas las imágenes de logos
    institutionLogos.forEach(img => {
        // Manejo de errores
        img.addEventListener('error', function() {
            handleImageError(this);
        });
        
        // Ajuste de tamaño
        adjustImageSize(img);
        
        // Añadir regla para forzar tamaño más pequeño a escudos nacionales
        if (img.src.includes('brasil')) {
            img.classList.add('logo-national-emblem');
        }
    });
    
    // Cambiar el texto del botón para expandir/colapsar descripción 
    const showMoreBtns = document.querySelectorAll('.show-more-btn');
    showMoreBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const isCollapsed = this.getAttribute('aria-expanded') === 'false';
            if (isCollapsed) {
                this.innerHTML = '<i class="bi bi-arrows-collapse"></i> Ver menos';
            } else {
                this.innerHTML = '<i class="bi bi-arrows-expand"></i> Ver más';
            }
        });
    });
});