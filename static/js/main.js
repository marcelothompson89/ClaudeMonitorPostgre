document.addEventListener('DOMContentLoaded', function() {
    // Función mejorada para asegurar que los iconos Bootstrap se muestran correctamente
    function fixBootstrapIcons() {
        // Seleccionar todos los iconos Bootstrap
        const icons = document.querySelectorAll('.bi');
        
        icons.forEach(icon => {
            // Aplicar estilos importantes para asegurar la visualización
            icon.style.display = 'inline-block';
            icon.style.lineHeight = '1';
            icon.style.verticalAlign = 'middle';
            
            // Verificar si el icono es visible
            if (window.getComputedStyle(icon).display === 'none') {
                console.log('Corrigiendo visibilidad de icono:', icon);
                icon.style.display = 'inline-block';
            }
            
            // Verificar si el icono tiene un contenedor padre que sea círculo
            const parentCircle = icon.closest('.icon-bg, .icon-circle');
            if (parentCircle) {
                // Asegurar que el contenedor esté correctamente configurado
                parentCircle.style.display = 'inline-flex';
                parentCircle.style.alignItems = 'center';
                parentCircle.style.justifyContent = 'center';
                parentCircle.style.borderRadius = '50%';
                parentCircle.style.position = 'relative';
                
                // Centrar el icono dentro del círculo
                icon.style.position = 'absolute';
                icon.style.top = '50%';
                icon.style.left = '50%';
                icon.style.transform = 'translate(-50%, -50%)';
            }
        });
        
        // Mejorar los logos institucionales
        const institutionLogos = document.querySelectorAll('.institution-logo-img');
        institutionLogos.forEach(img => {
            // Si la imagen ya está cargada
            if (img.complete && img.naturalHeight !== 0) {
                adjustLogoImage(img);
            } else {
                // Si la imagen aún no está cargada
                img.addEventListener('load', function() {
                    adjustLogoImage(img);
                });
            }
            
            // Manejo de errores de carga
            img.addEventListener('error', function() {
                handleLogoImageError(img);
            });
        });
    }

    // Función para corregir los círculos azules alargados y ocultar los números
    function fixCirclesAndNumbers() {
        // Primero, asegurémonos de que todos los contenedores de íconos tengan dimensiones cuadradas
        const iconContainers = document.querySelectorAll('.feature-icon .icon-bg, .feature-icon .rounded-circle, .feature-card .feature-icon > span, .feature-card .feature-icon > div');
        
        iconContainers.forEach(container => {
            // Aplicar dimensiones cuadradas
            container.style.width = '80px';
            container.style.height = '80px';
            container.style.minWidth = '80px';
            container.style.maxWidth = '80px';
            container.style.borderRadius = '50%';
            container.style.display = 'flex';
            container.style.justifyContent = 'center';
            container.style.alignItems = 'center';
            container.style.backgroundColor = '#0d6efd';
            container.style.color = 'white';
            container.style.position = 'relative';
            container.style.overflow = 'hidden';
            
            // Importante: añadir aspect-ratio para asegurar forma circular
            container.style.aspectRatio = '1 / 1';
        });
        
        // Asegurar que los íconos dentro de los círculos estén bien posicionados
        const icons = document.querySelectorAll('.feature-icon i, .feature-icon .bi, .feature-card .feature-icon i');
        
        icons.forEach(icon => {
            icon.style.position = 'absolute';
            icon.style.top = '50%';
            icon.style.left = '50%';
            icon.style.transform = 'translate(-50%, -50%)';
            icon.style.fontSize = '2rem';
            icon.style.margin = '0';
            icon.style.padding = '0';
            icon.style.lineHeight = '1';
        });
        
        // Corregir los círculos en la sección "Cómo Funciona"
        const howItWorksCircles = document.querySelectorAll('#how-it-works .step-icon .icon-circle, #how-it-works .icon-bg, #how-it-works .rounded-circle');
        
        howItWorksCircles.forEach(circle => {
            circle.style.width = '60px';
            circle.style.height = '60px';
            circle.style.borderRadius = '50%';
            circle.style.backgroundColor = '#0d6efd';
            circle.style.color = 'white';
            circle.style.display = 'flex';
            circle.style.alignItems = 'center';
            circle.style.justifyContent = 'center';
            circle.style.margin = '0 auto 1rem auto';
            circle.style.aspectRatio = '1 / 1';
        });
        
        // Ocultar los números delante de los títulos en "Cómo Funciona"
        const stepNumbers = document.querySelectorAll('#how-it-works .step-number, .how-it-works .step-number');
        
        stepNumbers.forEach(number => {
            number.style.display = 'none';
        });
        
        // Corregir específicamente los elementos que tienen clases compuestas
        const composedClassElements = document.querySelectorAll('[class*="feature-icon bg-primary"], [class*="icon-bg rounded-circle"]');
        
        composedClassElements.forEach(element => {
            element.style.width = '80px';
            element.style.height = '80px';
            element.style.minWidth = '80px';
            element.style.maxWidth = '80px';
            element.style.borderRadius = '50%';
            element.style.display = 'flex';
            element.style.justifyContent = 'center';
            element.style.alignItems = 'center';
            element.style.backgroundColor = '#0d6efd';
            element.style.color = 'white';
            element.style.aspectRatio = '1 / 1';
        });
    }

    // Función para ajustar imágenes de logos
    function adjustLogoImage(img) {
        // Verificar si es un tipo de logo específico
        if (img.src.toLowerCase().includes('brasil') || 
            img.src.toLowerCase().includes('escudo-nacional')) {
            img.classList.add('logo-national-emblem');
        } 
        // Verificar proporciones
        else if (img.naturalWidth / img.naturalHeight > 0.8) {
            img.classList.add('logo-emblem');
        }
        
        // Ajustar tamaño si la imagen es muy grande
        if (img.naturalWidth > 100 || img.naturalHeight > 100) {
            img.style.maxWidth = '100%';
            img.style.maxHeight = '100%';
            img.style.width = 'auto';
            img.style.height = 'auto';
        }
    }

    // Función para manejar errores de imágenes
    function handleLogoImageError(img) {
        img.style.display = 'none';
        // Buscar y mostrar texto alternativo
        const logoContainer = img.closest('.institution-logo');
        if (logoContainer) {
            // Crear elemento de texto alternativo si no existe
            let textLogo = logoContainer.querySelector('.logo-text');
            if (!textLogo) {
                textLogo = document.createElement('div');
                textLogo.className = 'logo-text';
                // Extraer iniciales del nombre de la institución si está disponible
                const institutionName = img.alt || 'IN';
                const initials = institutionName.split(' ')
                    .map(word => word[0])
                    .join('')
                    .substring(0, 2)
                    .toUpperCase();
                textLogo.textContent = initials;
                logoContainer.appendChild(textLogo);
            }
            textLogo.style.display = 'flex';
        }
    }
    
    // Función para limpiar el campo de búsqueda
    function clearSearch() {
        const searchInput = document.getElementById('header_search_text');
        if (searchInput) {
            searchInput.value = '';
            const searchForm = document.getElementById('searchForm');
            if (searchForm) {
                searchForm.submit();
            }
        }
    }
    
    // Asignar la función clearSearch al botón de limpiar
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', clearSearch);
    }
    
    // También inicializar las fechas y sincronizar formularios
    const startDateInput = document.getElementById('id_start_date');
    const endDateInput = document.getElementById('id_end_date');
    const minDateAttr = startDateInput ? startDateInput.getAttribute('data-min-date') : null;
    const maxDateAttr = endDateInput ? endDateInput.getAttribute('data-max-date') : null;
    
    if (startDateInput && minDateAttr) {
        startDateInput.value = minDateAttr;
    }
    
    if (endDateInput && maxDateAttr) {
        endDateInput.value = maxDateAttr;
    }
    
    // Sincronizar formularios de filtro y búsqueda
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
        filterForm.addEventListener('submit', function() {
            const headerSearchText = document.getElementById('header_search_text');
            const hiddenSearchText = document.getElementById('hidden_search_text');
            
            if (headerSearchText && hiddenSearchText) {
                hiddenSearchText.value = headerSearchText.value;
            }
        });
    }
    
    const searchForm = document.getElementById('searchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', function() {
            // Agregar los valores del formulario de filtros
            if (filterForm) {
                const filterInputs = filterForm.querySelectorAll('input, select');
                filterInputs.forEach(function(input) {
                    if (input.name && input.name !== 'search_text' && input.value) {
                        // Verificar si ya existe un campo oculto con este nombre
                        const existingInput = searchForm.querySelector(`input[name="${input.name}"]`);
                        if (!existingInput) {
                            const hiddenInput = document.createElement('input');
                            hiddenInput.type = 'hidden';
                            hiddenInput.name = input.name;
                            hiddenInput.value = input.value;
                            searchForm.appendChild(hiddenInput);
                        }
                    }
                });
            }
        });
    }
    
    // Ejecutar las funciones para corregir los iconos
    fixBootstrapIcons();
    fixCirclesAndNumbers();
    
    // Ejecutar de nuevo después de un tiempo para asegurar que los recursos externos estén cargados
    setTimeout(function() {
        fixBootstrapIcons();
        fixCirclesAndNumbers();
    }, 500);
    
    // Ejecutar también cuando la ventana esté completamente cargada
    window.addEventListener('load', function() {
        fixBootstrapIcons();
        fixCirclesAndNumbers();
    });
    
    // Si hay un redimensionamiento de ventana, volver a aplicar
    window.addEventListener('resize', fixCirclesAndNumbers);
    
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
    
    // Manejar el toggle del filtro de palabras clave

    const toggleKeywordFilter = document.getElementById('toggleKeywordFilter');
    if (toggleKeywordFilter) {
        toggleKeywordFilter.addEventListener('change', function() {
            // Corregir la URL para que funcione en todos los entornos
            let url;
            
            if (toggleKeywordFilter.hasAttribute('data-url')) {
                url = toggleKeywordFilter.getAttribute('data-url');
            } else {
                // Construir URL absoluta basada en la ubicación actual
                const baseUrl = window.location.pathname.includes('/alertas') 
                    ? '/alertas/toggle-filtro-keywords/' 
                    : '/toggle-filtro-keywords/';
                url = baseUrl;
            }
            
            console.log('URL para toggle:', url); // Depuración
            
            const xhr = new XMLHttpRequest();
            xhr.open('POST', url);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            
            // Obtener el token CSRF
            const csrfTokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
            if (csrfTokenElement) {
                xhr.setRequestHeader('X-CSRFToken', csrfTokenElement.value);
            } else {
                console.error('No se encontró el token CSRF');
            }
            
            xhr.onload = function() {
                console.log('Respuesta recibida:', xhr.status, xhr.responseText); // Depuración
                if (xhr.status === 200) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        if (response.success) {
                            location.reload();
                        } else {
                            console.error('Error en la respuesta:', response);
                            alert('Ocurrió un error al cambiar el estado del filtro: ' + (response.error || 'Error desconocido'));
                        }
                    } catch (e) {
                        console.error('Error al procesar la respuesta:', e, 'Texto de respuesta:', xhr.responseText);
                        alert('Error al procesar la respuesta del servidor');
                    }
                } else {
                    console.error('Error en la solicitud:', xhr.status, xhr.statusText);
                    alert('Ocurrió un error en la solicitud: ' + xhr.status);
                }
            };
            
            xhr.onerror = function(e) {
                console.error('Error en la solicitud AJAX:', e);
                alert('Ocurrió un error de red al cambiar el estado del filtro.');
            };
            
            xhr.send();
        });
    }
    
    // Exportar la función clearSearch para que sea accesible globalmente
    window.clearSearch = clearSearch;
});