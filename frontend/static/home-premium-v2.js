/* ================================================
   FITCOACH AI — Ultra-Premium Home JavaScript
   Slideshow, Cursor, Particles, Parallax, Interactions
   ================================================ */

(function() {
  'use strict';

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPremiumHome);
  } else {
    initPremiumHome();
  }

  // Configuration
  const CONFIG = {
    slideshowInterval: 5000, // 5 seconds
    cursorEnabled: window.innerWidth > 1024,
    particleCount: 30,
    parallaxStrength: 0.05
  };

  // State
  let state = {
    currentSlide: 0,
    slides: [],
    slideshowInterval: null,
    mouseX: 0,
    mouseY: 0,
    cursorTrail: []
  };

  // ─────────────────────────────────────────────────────────────────────────────
  // SLIDESHOW
  // ─────────────────────────────────────────────────────────────────────────────

  async function loadImages() {
    try {
      // Fetch available images from the API or use known images
      const knownImages = [
        'background_01.jpg',
        'background_02.jpg',
        'hero_01.jpg',
        'hero_02.jpg',
        'hero_03.jpg',
        'hero_04.jpg',
        'hero_05.jpg',
        'hero_06.jpg',
        'fitness_bg.webp',
        'gym_portrait.webp',
        'luxury_gym.webp',
        'hero_athlete.webp'
      ];

      // Filter to only existing images
      const validImages = await Promise.all(
        knownImages.map(async (img) => {
          try {
            const response = await fetch(`/assets/images/home/${img}`);
            if (response.ok) {
              return img;
            }
            return null;
          } catch {
            return null;
          }
        })
      );

      state.slides = validImages.filter(img => img !== null);
      
      if (state.slides.length === 0) {
        console.warn('No images found for slideshow');
        return false;
      }

      return true;
    } catch (error) {
      console.error('Error loading images:', error);
      return false;
    }
  }

  function createSlideshow() {
    const heroBackground = document.querySelector('.hero-background');
    if (!heroBackground) return;

    // Clear existing slides
    heroBackground.innerHTML = '';

    // Create slide elements
    state.slides.forEach((img, index) => {
      const slide = document.createElement('div');
      slide.className = `hero-slide ${index === 0 ? 'active' : ''}`;
      
      const image = document.createElement('img');
      image.src = `/assets/images/home/${img}`;
      image.alt = 'Fitness background';
      image.loading = 'lazy';
      
      slide.appendChild(image);
      heroBackground.appendChild(slide);
    });

    // Start slideshow
    startSlideshow();
  }

  function startSlideshow() {
    if (state.slideshowInterval) {
      clearInterval(state.slideshowInterval);
    }

    state.slideshowInterval = setInterval(() => {
      nextSlide();
    }, CONFIG.slideshowInterval);
  }

  function nextSlide() {
    const slides = document.querySelectorAll('.hero-slide');
    if (slides.length === 0) return;

    // Remove active class from current
    slides[state.currentSlide].classList.remove('active');

    // Move to next
    state.currentSlide = (state.currentSlide + 1) % slides.length;

    // Add active class to next
    slides[state.currentSlide].classList.add('active');
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // CUSTOM CURSOR
  // ─────────────────────────────────────────────────────────────────────────────

  function initCursor() {
    if (!CONFIG.cursorEnabled) return;

    // Create cursor elements
    const cursor = document.createElement('div');
    cursor.className = 'custom-cursor';
    
    const cursorDot = document.createElement('div');
    cursorDot.className = 'custom-cursor-dot';
    
    const cursorTrail = document.createElement('div');
    cursorTrail.className = 'cursor-trail';

    document.body.appendChild(cursor);
    document.body.appendChild(cursorDot);
    document.body.appendChild(cursorTrail);

    // Track mouse movement
    let mouseX = 0, mouseY = 0;
    let cursorX = 0, cursorY = 0;
    let trailX = 0, trailY = 0;

    document.addEventListener('mousemove', (e) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
    });

    // Animate cursor
    function animateCursor() {
      // Smooth interpolation
      cursorX += (mouseX - cursorX) * 0.15;
      cursorY += (mouseY - cursorY) * 0.15;
      trailX += (mouseX - trailX) * 0.08;
      trailY += (mouseY - trailY) * 0.08;

      cursor.style.left = `${cursorX - 10}px`;
      cursor.style.top = `${cursorY - 10}px`;
      
      cursorDot.style.left = `${cursorX - 4}px`;
      cursorDot.style.top = `${cursorY - 4}px`;
      
      cursorTrail.style.left = `${trailX - 20}px`;
      cursorTrail.style.top = `${trailY - 20}px`;

      requestAnimationFrame(animateCursor);
    }

    animateCursor();

    // Hover effects
    const hoverElements = document.querySelectorAll('button, a, .glass-card, .quick-card');
    hoverElements.forEach(el => {
      el.addEventListener('mouseenter', () => {
        cursor.classList.add('hover');
      });
      el.addEventListener('mouseleave', () => {
        cursor.classList.remove('hover');
      });
    });

    // Click ripple effect
    document.addEventListener('click', (e) => {
      const ripple = document.createElement('div');
      ripple.className = 'cursor-ripple';
      ripple.style.left = `${e.clientX - 10}px`;
      ripple.style.top = `${e.clientY - 10}px`;
      document.body.appendChild(ripple);
      
      setTimeout(() => {
        ripple.remove();
      }, 600);
    });
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // PARTICLE SYSTEM
  // ─────────────────────────────────────────────────────────────────────────────

  function initParticles() {
    const container = document.createElement('div');
    container.className = 'particle-container';
    document.body.appendChild(container);

    for (let i = 0; i < CONFIG.particleCount; i++) {
      createParticle(container);
    }
  }

  function createParticle(container) {
    const particle = document.createElement('div');
    particle.className = 'particle';
    
    // Random position and timing
    const startX = Math.random() * 100;
    const duration = 10 + Math.random() * 10;
    const delay = Math.random() * 10;
    const size = 2 + Math.random() * 4;
    
    particle.style.left = `${startX}%`;
    particle.style.width = `${size}px`;
    particle.style.height = `${size}px`;
    particle.style.animationDuration = `${duration}s`;
    particle.style.animationDelay = `${delay}s`;
    
    container.appendChild(particle);
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // PARALLAX EFFECT
  // ─────────────────────────────────────────────────────────────────────────────

  function initParallax() {
    const heroContent = document.querySelector('.hero-content');
    const blobs = document.querySelectorAll('.gradient-blob');
    
    if (!heroContent) return;

    document.addEventListener('mousemove', (e) => {
      const x = (e.clientX / window.innerWidth - 0.5) * CONFIG.parallaxStrength;
      const y = (e.clientY / window.innerHeight - 0.5) * CONFIG.parallaxStrength;

      // Parallax hero content
      heroContent.style.transform = `translate(${x * 20}px, ${y * 20}px)`;

      // Parallax gradient blobs
      blobs.forEach((blob, index) => {
        const factor = (index + 1) * 0.5;
        blob.style.transform = `translate(${x * 50 * factor}px, ${y * 50 * factor}px)`;
      });
    });
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // SCROLL ANIMATIONS
  // ─────────────────────────────────────────────────────────────────────────────

  function initScrollAnimations() {
    if (!('IntersectionObserver' in window)) return;

    const observerOptions = {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
          observer.unobserve(entry.target);
        }
      });
    }, observerOptions);

    // Observe all animated elements
    const animatedElements = document.querySelectorAll('.section-header, .quick-card, .glass-card');
    animatedElements.forEach((el, index) => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(40px)';
      el.style.transition = `opacity 0.8s ease ${index * 0.1}s, transform 0.8s ease ${index * 0.1}s`;
      observer.observe(el);
    });
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // NUMBER ANIMATION
  // ─────────────────────────────────────────────────────────────────────────────

  function animateNumber(element, target, duration = 2000) {
    if (!element) return;

    const start = 0;
    const startTime = performance.now();
    
    function update(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      // Easing function
      const easeOutQuart = 1 - Math.pow(1 - progress, 4);
      const current = Math.floor(start + (target - start) * easeOutQuart);
      
      element.textContent = current;
      
      if (progress < 1) {
        requestAnimationFrame(update);
      } else {
        element.textContent = target;
      }
    }
    
    requestAnimationFrame(update);
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // MAIN INITIALIZATION
  // ─────────────────────────────────────────────────────────────────────────────

  async function initPremiumHome() {
    const premiumHome = document.querySelector('.premium-home');
    if (!premiumHome) return;

    // Load images and create slideshow
    const imagesLoaded = await loadImages();
    if (imagesLoaded) {
      createSlideshow();
    }

    // Initialize effects
    initCursor();
    initParticles();
    initParallax();
    initScrollAnimations();

    // Animate stats numbers when visible
    const statsObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const statNumbers = entry.target.querySelectorAll('.stat-number');
          statNumbers.forEach(stat => {
            const target = parseInt(stat.textContent) || 0;
            if (target > 0) {
              animateNumber(stat, target);
            }
          });
          statsObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.5 });

    const heroStats = document.querySelector('.hero-stats');
    if (heroStats) {
      statsObserver.observe(heroStats);
    }
  }

})();
