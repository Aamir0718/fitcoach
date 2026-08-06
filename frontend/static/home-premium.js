/*===========================================================
  FITCOACH AI — PREMIUM HOME
  Animations: athlete crossfade, phone tilt, particles,
  mini graphs, floating widgets, scroll reveal.
  Scoped — does not touch sidebar, auth or other tabs.
  ============================================================*/

(function () {
  "use strict";

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPremiumHome);
  } else {
    initPremiumHome();
  }

  function initPremiumHome() {
    if (!document.querySelector(".premium-home")) return;

    initLucide();
    setupScrollReveal();
    setupParticles();
    setupCursorGlow();
    setupLiveAthlete();
    setupPhoneTilt();
    setupHeroParallax();
    setupFeatureCards();
    setupPhoneTime();
    setupMiniGraphs();
    setupHeartRatePulse();
    injectFloatingWidgets();
    return safeObserveHomeTab();
  }

  /*────────────── LUCIDE ICONS ──────────────*/
  function initLucide() {
    if (window.lucide) {
      try { lucide.createIcons(); } catch (e) { /* non-fatal */ }
    }
  }

  /*────────────── SCROLL REVEAL ──────────────*/
  function setupScrollReveal() {
    const els = document.querySelectorAll(".premium-home [data-animate]");
    if (!els.length) return;

    if (!("IntersectionObserver" in window)) {
      els.forEach((el) => el.classList.add("visible"));
      return;
    }

    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            obs.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -44px 0px" }
    );

    els.forEach((el) => obs.observe(el));
  }

  /*────────────── ANIMATED PARTICLES ──────────────*/
  function setupParticles() {
    const container = document.getElementById("home-particles");
    if (!container) return;
    container.innerHTML = "";

    const count = window.innerWidth < 600 ? 18 : 34;
    const frag = document.createDocumentFragment();

    for (let i = 0; i < count; i++) {
      const p = document.createElement("span");
      p.className = "ph-particle";
      const size = 2 + Math.random() * 3;
      p.style.width = size + "px";
      p.style.height = size + "px";
      p.style.left = Math.random() * 100 + "%";
      p.style.top = 100 + Math.random() * 30 + "%";
      p.style.animationDuration = 14 + Math.random() * 22 + "s";
      p.style.animationDelay = -Math.random() * 30 + "s";
      p.style.opacity = "0";
      frag.appendChild(p);
    }

    container.appendChild(frag);
  }

  /*────────────── CURSOR GLOW ──────────────*/
  function setupCursorGlow() {
    if (window.matchMedia("(pointer: coarse)").matches) return;
    if (document.querySelector(".ph-cursor-glow")) return;

    const glow = document.createElement("div");
    glow.className = "ph-cursor-glow";
    glow.style.left = "-1000px";
    glow.style.top = "-1000px";
    document.body.appendChild(glow);

    let raf = null;
    let cx = -1000;
    let cy = -1000;

    document.addEventListener("mousemove", (e) => {
      cx = e.clientX;
      cy = e.clientY;
      if (!raf) {
        raf = requestAnimationFrame(() => {
          glow.style.left = cx + "px";
          glow.style.top = cy + "px";
          raf = null;
        });
      }
    });
  }

  /*────────────── LIVE ATHLETE CROSSFADE ──────────────*/
  const ATHLETE_INTERVAL = 8000;
  const ATHLETE_LABELS = {
    runner: "Running",
    jumprope: "Jump Rope",
    deadlift: "Deadlift",
    boxing: "Boxing",
    walking: "Walking",
  };

  function setupLiveAthlete() {
    const scene = document.getElementById("live-athlete");
    if (!scene) return;

    const imgs = Array.from(scene.querySelectorAll(".athlete-img"));
    if (imgs.length < 2) return;

    // Status pill (if not already in markup)
    let pill = scene.querySelector(".athlete-live-pill");
    if (!pill) {
      pill = document.createElement("span");
      pill.className = "athlete-live-pill";
      pill.innerHTML =
        '<span class="live-dot"></span><span class="athlete-live-label">Running</span>';
      scene.appendChild(pill);
    }

    const label = pill.querySelector(".athlete-live-label");
    let current = 0;

    // Initial state
    imgs.forEach((img, idx) => {
      img.classList.toggle("active", idx === 0);
    });
    if (label) {
      const key = imgs[0].dataset.athlete || "runner";
      label.textContent = ATHLETE_LABELS[key] || "Training";
    }

    // Slow Ken Burns zoom on the active image
    imgs[0].classList.add("zooming");

    setInterval(() => {
      const prev = imgs[current];
      const nextIdx = (current + 1) % imgs.length;
      const next = imgs[nextIdx];

      // Start next image
      next.classList.add("active");
      next.classList.add("zooming");

      // Fade out previous after slight overlap
      prev.classList.remove("active");
      prev.classList.remove("zooming");

      // Update label
      if (label) {
        const key = next.dataset.athlete || "runner";
        label.textContent = ATHLETE_LABELS[key] || "Training";
      }

      current = nextIdx;
    }, ATHLETE_INTERVAL);
  }

  /*────────────── PHONE MOUSE TILT ──────────────*/
  function setupPhoneTilt() {
    const scene = document.getElementById("phone-scene");
    if (!scene) return;
    if (window.matchMedia("(pointer: coarse)").matches) return;

    const phone = document.getElementById("phone-mockup");
    if (!phone) return;

    let raf = null;
    let targetRX = 0;
    let targetRY = 0;

    const onMove = (e) => {
      const rect = scene.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const px = (e.clientX - cx) / (rect.width / 2);
      const py = (e.clientY - cy) / (rect.height / 2);

      targetRY = px * 8;
      targetRX = -py * 6;

      if (!raf) {
        raf = requestAnimationFrame(() => {
          const current = getComputedStyle(phone).transform;
          phone.style.transform =
            current + " rotateX(" + targetRX.toFixed(2) + "deg) rotateY(" + targetRY.toFixed(2) + "deg)";
          raf = null;
        });
      }
    };

    const onLeave = () => {
      phone.style.transform = "";
    };

    scene.addEventListener("mousemove", onMove);
    scene.addEventListener("mouseleave", onLeave);
  }

  /*────────────── HERO PARALLAX ──────────────*/
  function setupHeroParallax() {
    const scene = document.getElementById("phone-scene");
    if (!scene) return;
    if (window.matchMedia("(pointer: coarse)").matches) return;

    const hero = document.querySelector(".hero-right");
    if (!hero) return;

    let raf = null;

    document.addEventListener("mousemove", (e) => {
      const x = (window.innerWidth / 2 - e.clientX) / 60;
      const y = (window.innerHeight / 2 - e.clientY) / 60;

      if (!raf) {
        raf = requestAnimationFrame(() => {
          scene.style.transform = "translate3d(" + x + "px," + y + "px,0)";
          raf = null;
        });
      }
    });
  }

  /*────────────── FEATURE CARD HOVER GLOW ──────────────*/
  function setupFeatureCards() {
    document.querySelectorAll(".feature-card").forEach((card) => {
      card.addEventListener("mousemove", (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        card.style.setProperty("--mx", x + "px");
        card.style.setProperty("--my", y + "px");
      });
    });
  }

  /*────────────── PHONE CLOCK ──────────────*/
  function setupPhoneTime() {
    const el = document.getElementById("phone-time");
    if (!el) return;

    const update = () => {
      const now = new Date();
      let h = now.getHours();
      const m = now.getMinutes().toString().padStart(2, "0");
      const ap = h >= 12 ? "PM" : "AM";
      h = h % 12;
      if (h === 0) h = 12;
      el.textContent = h + ":" + m + " " + ap;
    };

    update();
    setInterval(update, 30000);
  }

  /*────────────── MINI GRAPHS ──────────────*/
  function setupMiniGraphs() {
    drawGraph("graph-recovery", {
      color: "124,92,255",
      fill: true,
      points: 26,
      variance: 0.32,
    });
    drawGraph("graph-calories", {
      color: "111,168,255",
      fill: true,
      points: 26,
      variance: 0.4,
      inverted: true,
    });
  }

  function drawGraph(id, opts) {
    const wrap = document.getElementById(id);
    if (!wrap) return;
    const canvas = wrap.querySelector("canvas");
    if (!canvas) return;

    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth || 120;
    const h = canvas.clientHeight || 60;
    canvas.width = w * dpr;
    canvas.height = h * dpr;

    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);

    const pts = [];
    for (let i = 0; i < opts.points; i++) {
      const base = 0.55 + Math.random() * 0.2;
      const wave = Math.sin(i / 3) * opts.variance;
      const noise = (Math.random() - 0.5) * 0.12;
      pts.push(base + wave + noise);
    }

    const stroke = "rgba(" + opts.color + ",.85)";
    const fillTop = "rgba(" + opts.color + ",.22)";
    const fillBot = "rgba(" + opts.color + ",0)";

    ctx.clearRect(0, 0, w, h);

    // Fill
    ctx.beginPath();
    ctx.moveTo(0, h);
    pts.forEach((p, i) => {
      const x = (i / (opts.points - 1)) * w;
      const y = h - p * h;
      if (i === 0) ctx.lineTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.lineTo(w, h);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, fillTop);
    grad.addColorStop(1, fillBot);
    ctx.fillStyle = grad;
    ctx.fill();

    // Stroke
    ctx.beginPath();
    pts.forEach((p, i) => {
      const x = (i / (opts.points - 1)) * w;
      const y = h - p * h;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 1.6;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.stroke();

    // End dot
    const lastX = w;
    const lastY = h - pts[pts.length - 1] * h;
    ctx.beginPath();
    ctx.arc(lastX, lastY, 2.6, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(" + opts.color + ",1)";
    ctx.shadowColor = "rgba(" + opts.color + ",.7)";
    ctx.shadowBlur = 6;
    ctx.fill();
    ctx.shadowBlur = 0;
  }

  /*────────────── HEART RATE PULSE ──────────────*/
  function setupHeartRatePulse() {
    const hrEl = document.getElementById("hr-bpm");
    if (!hrEl) return;

    const pulse = () => {
      hrEl.classList.add("hr-pulse");
      void hrEl.offsetWidth; // restart animation
      hrEl.classList.remove("hr-pulse");
    };

    // Pulse roughly every 4 seconds to simulate live HR
    setInterval(pulse, 4000);
  }

  /*────────────── FLOATING WIDGETS ──────────────*/
  function injectFloatingWidgets() {
    const scene = document.getElementById("phone-scene");
    if (!scene) return;
    if (scene.querySelector(".float-widget")) return;

    // Readiness ring widget (top-left of phone)
    const ringEl = document.createElement("div");
    ringEl.className = "float-widget-ring";
    ringEl.style.left = "-7%";
    ringEl.style.top = "16%";
    ringEl.innerHTML =
      '<svg viewBox="0 0 40 40" aria-hidden="true">' +
      '<defs><linearGradient id="fwGradient" x1="0" y1="0" x2="1" y2="1">' +
      '<stop offset="0%" stop-color="#7C5CFF"/><stop offset="100%" stop-color="#6FA8FF"/>' +
      "</linearGradient></defs>" +
      '<circle class="ring-bg" cx="20" cy="20" r="16"></circle>' +
      '<circle class="ring-fg" cx="20" cy="20" r="16" stroke-dasharray="100.53" stroke-dashoffset="8"></circle>' +
      "</svg>";
    scene.appendChild(ringEl);

    // Recovery widget (top-right)
    const widget1 = document.createElement("div");
    widget1.className = "float-widget";
    widget1.style.right = "-6%";
    widget1.style.top = "8%";
    widget1.style.animationDelay = "0.8s";
    widget1.innerHTML =
      '<span class="fw-icon"><i data-lucide="activity"></i></span>' +
      '<span><small>Recovery</small><strong>92%</strong></span>';
    scene.appendChild(widget1);

    // Calories widget (bottom-left)
    const widget2 = document.createElement("div");
    widget2.className = "float-widget";
    widget2.style.left = "-2%";
    widget2.style.bottom = "2%";
    widget2.style.animationDelay = "1.6s";
    widget2.innerHTML =
      '<span class="fw-icon"><i data-lucide="flame"></i></span>' +
      '<span><small>Calories</small><strong>1,847</strong></span>';
    scene.appendChild(widget2);

    // Heart rate widget (right, below phone)
    const widget3 = document.createElement("div");
    widget3.className = "float-widget";
    widget3.style.right = "-2%";
    widget3.style.bottom = "18%";
    widget3.style.animationDelay = "2.4s";
    widget3.innerHTML =
      '<span class="fw-icon"><i data-lucide="heart-pulse"></i></span>' +
      '<span><small>Heart Rate</small><strong>72 bpm</strong></span>';
    scene.appendChild(widget3);

    // Generate the new icons
    if (window.lucide) {
      try { lucide.createIcons(); } catch (e) { /* non-fatal */ }
    }
  }

  /*────────────── OBSERVE HOME TAB (re-init on show) ──────────────*/
  function safeObserveHomeTab() {
    const homeTab = document.getElementById("tab-home");
    if (!homeTab) return;
    if (!("MutationObserver" in window)) return;

    const obs = new MutationObserver(() => {
      if (homeTab.classList.contains("active")) {
        // Re-trigger lucide render in case the tab was hidden during init
        if (window.lucide) {
          try { lucide.createIcons(); } catch (e) { /* non-fatal */ }
        }
        // Redraw graphs in case canvas was reset while hidden
        setupMiniGraphs();
        // Reset scroll reveal state so hidden sections animate on view
        document.querySelectorAll(".premium-home [data-animate]").forEach((el) => {
          const rect = el.getBoundingClientRect();
          if (rect.top < window.innerHeight && rect.bottom > 0) {
            el.classList.add("visible");
          }
        });
      }
    });

    obs.observe(homeTab, { attributes: true, attributeFilter: ["class"] });
    return obs;
  }
})();