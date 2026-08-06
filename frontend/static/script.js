// ================================================
// FITCOACH AI — script.js v4.0
// Sport Mode + Recovery Intelligence
// ================================================
// Backend now lives on Render (separate service) instead of same-origin Flask.
// TODO: replace with the actual Render service URL once it's deployed.
const API = (location.hostname === "localhost" || location.hostname === "127.0.0.1")
  ? "http://localhost:8000"
  : "https://fitcoach-backend.onrender.com";
window.API = API;
let authToken    = localStorage.getItem("fc_token") || null;
let currentUser  = null;
let workoutMode  = localStorage.getItem("fc_workout_mode") || "gym";
let voiceRec     = null;
let isListening  = false;
let restInterval = null;
let chartInst    = {};
let workoutActive  = false;
let feedbackMode   = false;
let onboardingField     = null;
let onboardingInputType = null;
let onboardingGender    = "male";
let sportObField        = null;
let sportObInputType    = null;
let sportObSport        = null;
let recoveryInputs      = {};
let foodPhotoBase64 = null;
let homeCountRaf = {};
// ── ATHLETE THEMES ───────────────────────────────────────────────────────
const ATHLETE_THEMES = {
  galaxy: { label: "Galaxy Purple" },
  carbon: { label: "Carbon Black" },
  cyan: { label: "Neon Cyan" },
  gold: { label: "Elite Gold" },
  ice: { label: "Ice White" },
};
const AUTO_THEME_BY_TAB = {
  home: "galaxy",
  chat: "galaxy",
  trainer: "carbon",
  recovery: "ice",
  progress: "gold",
  calories: "cyan",
  profile: "carbon",
  visualos: "galaxy",
};

function applyAthleteTheme(theme, options = {}) {
  const nextTheme = ATHLETE_THEMES[theme] ? theme : "galaxy";
  document.documentElement.setAttribute("data-theme", nextTheme);
  document.documentElement.classList.add("theme-is-switching");
  window.clearTimeout(applyAthleteTheme._timer);
  applyAthleteTheme._timer = window.setTimeout(() => {
    document.documentElement.classList.remove("theme-is-switching");
  }, 520);
  if (!options.previewOnly) {
    localStorage.setItem("fc_athlete_theme", nextTheme);
  }
  updateThemeSwitcher(nextTheme);
}

function updateThemeSwitcher(activeTheme) {
  document.querySelectorAll("[data-theme-option]").forEach((chip) => {
    chip.classList.toggle("active", chip.dataset.themeOption === activeTheme);
  });
  const autoEnabled = localStorage.getItem("fc_theme_auto") === "1";
  document.documentElement.toggleAttribute("data-theme-auto", autoEnabled);
  const autoBtn = document.getElementById("theme-auto-btn");
  if (autoBtn) {
    autoBtn.classList.toggle("active", autoEnabled);
    autoBtn.setAttribute("aria-pressed", autoEnabled ? "true" : "false");
  }
}

function setAthleteTheme(theme) {
  localStorage.setItem("fc_theme_auto", "0");
  applyAthleteTheme(theme);
  showToast(`Visual OS: ${ATHLETE_THEMES[theme]?.label || "Galaxy Purple"}`);
}

function toggleAutoTheme() {
  const enabled = localStorage.getItem("fc_theme_auto") === "1";
  localStorage.setItem("fc_theme_auto", enabled ? "0" : "1");
  if (!enabled) {
    const activeTab = document.querySelector(".tab-content.active")?.id?.replace("tab-", "") || "home";
    applyAthleteTheme(AUTO_THEME_BY_TAB[activeTab] || "galaxy", { previewOnly: true });
    showToast("Auto AI theme mode enabled");
  } else {
    applyAthleteTheme(localStorage.getItem("fc_athlete_theme") || "galaxy");
    showToast("Auto AI theme mode disabled");
  }
}

function initThemeEngine() {
  const savedTheme = localStorage.getItem("fc_athlete_theme") || document.documentElement.dataset.theme || "galaxy";
  applyAthleteTheme(savedTheme);
  document.querySelectorAll("[data-theme-option]").forEach((chip) => {
    chip.addEventListener("mouseenter", () => {
      if (localStorage.getItem("fc_theme_auto") === "1") return;
      applyAthleteTheme(chip.dataset.themeOption, { previewOnly: true });
    });
    chip.addEventListener("mouseleave", () => {
      if (localStorage.getItem("fc_theme_auto") === "1") return;
      applyAthleteTheme(localStorage.getItem("fc_athlete_theme") || savedTheme, { previewOnly: true });
    });
  });
}

// ── HOME SCREEN ─────────────────────────────────────────────────────--
 
const HOME_QUOTES = [
  { text: "The body achieves what the mind believes.", author: "FitCoach AI" },
  { text: "Hard work beats talent when talent doesn't work hard.", author: "Tim Notke" },
  { text: "Don't count the days. Make the days count.", author: "Muhammad Ali" },
  { text: "I've failed over and over and over again. That is why I succeed.", author: "Michael Jordan" },
  { text: "The most important thing is to try and inspire people.", author: "Kobe Bryant" },
  { text: "I am not a perfectionist, but I like to feel that things are done well.", author: "Cristiano Ronaldo" },
  { text: "The last three or four reps is what makes the muscle grow.", author: "Arnold Schwarzenegger" },
  { text: "Champions train differently.", author: "FitCoach AI" },
  { text: "Discipline creates freedom.", author: "FitCoach AI" },
  { text: "Pressure creates diamonds.", author: "FitCoach AI" },
];
 
function timeGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}
 
function getTodayCTAMessage(profile, recoveryZone) {
  const goal = profile?.goal?.toLowerCase() || "";
  if (recoveryZone === "red") {
    return { icon: "🌿", title: "Recovery Day", sub: "Your body needs rest — tap for a light session" };
  }
  if (recoveryZone === "yellow") {
    return { icon: "⚡", title: "Moderate Session", sub: "70% intensity today — tap to start" };
  }
  if (goal.includes("weight") || goal.includes("fat")) {
    return { icon: "🔥", title: "Burn Session Ready", sub: "Tap to begin today's fat-loss workout" };
  }
  if (goal.includes("muscle") || goal.includes("bulk") || goal.includes("strength")) {
    return { icon: "💪", title: "Strength Day", sub: "Let's build. Tap to start your session" };
  }
  return { icon: "🏋️", title: "Start Today's Workout", sub: "Tap to begin your AI-guided session" };
}
 
function setTxt(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

// ── HOME DASHBOARD ───────────────────────────────────────────────────────
function loadHomeDashboard() {
  // Set welcome message
  const greeting = timeGreeting();
  const welcomeTitle = document.getElementById('home-welcome-title');
  const welcomeSubtitle = document.getElementById('home-welcome-subtitle');
  
  if (welcomeTitle) {
    welcomeTitle.textContent = `${greeting}, ${currentUser?.name?.split(' ')[0] || 'Athlete'}`;
  }
  if (welcomeSubtitle) {
    const hour = new Date().getHours();
    let subtitle = "Ready to train today?";
    if (hour < 12) subtitle = "Start your day strong";
    else if (hour < 17) subtitle = "Keep the momentum going";
    else subtitle = "Evening training session";
    welcomeSubtitle.textContent = subtitle;
  }

  // Load recovery data
  loadHomeRecovery();
  
  // Load calories data
  loadHomeCalories();
  
  // Load progress data
  loadHomeProgress();
  
  // Load workout info
  loadHomeWorkout();
}

async function loadHomeRecovery() {
  try {
    const response = await fetch(`${API}/recovery/latest`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (response.ok) {
      const data = await response.json();
      const recoveryDisplay = document.getElementById('home-recovery-display');
      const recoveryStatus = document.getElementById('home-recovery-status');
      
      if (recoveryDisplay && data.recovery_score !== undefined) {
        recoveryDisplay.textContent = Math.round(data.recovery_score);
        
        if (recoveryStatus) {
          if (data.recovery_score >= 80) {
            recoveryStatus.textContent = 'Optimal';
            recoveryStatus.style.color = 'var(--green)';
          } else if (data.recovery_score >= 60) {
            recoveryStatus.textContent = 'Good';
            recoveryStatus.style.color = 'var(--orange)';
          } else {
            recoveryStatus.textContent = 'Needs Rest';
            recoveryStatus.style.color = 'var(--red)';
          }
        }
      }
    }
  } catch (error) {
    console.error('Failed to load recovery data:', error);
    setTxt('home-recovery-display', '--');
    setTxt('home-recovery-status', 'No data');
  }
}

async function loadHomeCalories() {
  try {
    const response = await fetch(`${API}/nutrition/today`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (response.ok) {
      const data = await response.json();
      const caloriesDisplay = document.getElementById('home-calories-display');
      const caloriesStatus = document.getElementById('home-calories-status');
      
      if (caloriesDisplay && data.total_calories !== undefined) {
        caloriesDisplay.textContent = Math.round(data.total_calories);
        
        if (caloriesStatus) {
          const goal = data.daily_goal || 2000;
          const percentage = (data.total_calories / goal) * 100;
          
          if (percentage >= 90 && percentage <= 110) {
            caloriesStatus.textContent = 'On Track';
            caloriesStatus.style.color = 'var(--green)';
          } else if (percentage < 90) {
            caloriesStatus.textContent = 'Below Goal';
            caloriesStatus.style.color = 'var(--orange)';
          } else {
            caloriesStatus.textContent = 'Above Goal';
            caloriesStatus.style.color = 'var(--red)';
          }
        }
      }
    }
  } catch (error) {
    console.error('Failed to load calories data:', error);
    setTxt('home-calories-display', '--');
    setTxt('home-calories-status', 'No data');
  }
}

async function loadHomeProgress() {
  try {
    const response = await fetch(`${API}/progress/summary`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (response.ok) {
      const data = await response.json();
      const streakDisplay = document.getElementById('home-streak-display');
      const workoutsDisplay = document.getElementById('home-workouts-display');
      
      if (streakDisplay && data.current_streak !== undefined) {
        streakDisplay.textContent = data.current_streak;
      }
      
      if (workoutsDisplay && data.weekly_workouts !== undefined) {
        workoutsDisplay.textContent = data.weekly_workouts;
      }
    }
  } catch (error) {
    console.error('Failed to load progress data:', error);
    setTxt('home-streak-display', '0');
    setTxt('home-workouts-display', '0');
  }
}

async function loadHomeWorkout() {
  try {
    const response = await fetch(`${API}/workouts/today`, {
      headers: { 'Authorization': `Bearer ${authToken}` }
    });
    
    if (response.ok) {
      const data = await response.json();
      const workoutType = document.getElementById('home-workout-type');
      const workoutDuration = document.getElementById('home-workout-duration');
      const workoutExercises = document.getElementById('home-workout-exercises');
      
      if (workoutType && data.name) {
        workoutType.textContent = data.name;
      }
      
      if (workoutDuration && data.estimated_duration) {
        workoutDuration.textContent = `${data.estimated_duration} min`;
      }
      
      if (workoutExercises && data.exercises) {
        workoutExercises.textContent = `${data.exercises.length} exercises`;
      }
    }
  } catch (error) {
    console.error('Failed to load workout data:', error);
    setTxt('home-workout-type', 'No workout planned');
    setTxt('home-workout-duration', '-- min');
    setTxt('home-workout-exercises', '-- exercises');
  }
}

function animateTextNumber(id, value, suffix = "") {
  const el = document.getElementById(id);
  if (!el) return;
  const number = Number(value);
  if (!Number.isFinite(number)) {
    el.textContent = value || "—";
    return;
  }
  cancelAnimationFrame(homeCountRaf[id]);
  const start = performance.now();
  const duration = 720;
  const from = Number(el.dataset.value || 0);
  const ease = (t) => 1 - Math.pow(1 - t, 3);
  const tick = (now) => {
    const t = Math.min(1, (now - start) / duration);
    const current = Math.round(from + (number - from) * ease(t));
    el.textContent = current + suffix;
    if (t < 1) homeCountRaf[id] = requestAnimationFrame(tick);
    else el.dataset.value = number;
  };
  homeCountRaf[id] = requestAnimationFrame(tick);
}

// ── MOTIVATIONAL QUOTES (kept for potential use) ─────────────────────────
const MOTIVATIONAL_QUOTES = [
  { text: "The body achieves what the mind believes.", author: "Unknown" },
  { text: "Discipline is choosing between what you want now and what you want most.", author: "Unknown" },
  { text: "Your strongest self is built one workout at a time.", author: "Unknown" },
  { text: "The only bad workout is the one you didn't do.", author: "Unknown" },
  { text: "Success starts with self-discipline.", author: "Unknown" },
  { text: "Train hard, recover smarter.", author: "Unknown" },
  { text: "Your body can stand almost anything. It's your mind you have to convince.", author: "Unknown" },
  { text: "The pain you feel today will be the strength you feel tomorrow.", author: "Unknown" },
  { text: "Don't wish for it, work for it.", author: "Unknown" },
  { text: "Every rep counts when you're consistent.", author: "Unknown" }
];

const PORTRAIT_IMAGES = [
  'portrait_01.jpg',
  'portrait_02.jpg',
  'portrait_03.jpg'
];

// ── RENDER HOME WEEK HEATMAP ─────────────────────────────────────────────── 
function renderHomeWeek(heatmap) {
  const container = document.getElementById("home-week-row");
  if (!container) return;
 
  const days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
  const today = new Date();
  // Build last 7 days as YYYY-MM-DD strings
  const last7 = Array.from({length:7}, (_,i) => {
    const d = new Date(today);
    d.setDate(today.getDate() - (6 - i));
    return d.toISOString().split("T")[0];
  });
 
  // Build a set of workout dates from heatmap
  const workoutDates = new Set();
  if (heatmap && Array.isArray(heatmap)) {
    heatmap.forEach(entry => {
      if (entry.date) workoutDates.add(entry.date.split("T")[0]);
    });
  }
 
  const todayStr = today.toISOString().split("T")[0];
 
  container.innerHTML = last7.map((dateStr, i) => {
    const worked = workoutDates.has(dateStr);
    const isToday = dateStr === todayStr;
    const dayLabel = days[new Date(dateStr).getDay() === 0 ? 6 : new Date(dateStr).getDay() - 1];
    const barClass = isToday ? "week-bar today" : worked ? "week-bar done" : "week-bar empty";
    const barHeight = worked || isToday ? "32px" : "16px";
    const checkmark = worked ? '<div class="week-check">✓</div>' : "";
    return `<div class="week-day">
      ${checkmark}
      <div class="${barClass}" style="height:${barHeight}"></div>
      <div class="week-label">${dayLabel}</div>
    </div>`;
  }).join("");
}

// ── SPORT ONBOARDING DEFINITIONS ──────────────────────────────────────
const SPORT_FIELD_ORDERS = {
  cricket:  ["sport_select","role","bowling_type","match_frequency","primary_focus","sport_injuries"],
  football: ["sport_select","position","match_frequency","primary_focus","sport_injuries"],
  running:  ["sport_select","distance_type","weekly_mileage","primary_focus","sport_injuries"],
  default:  ["sport_select","primary_focus","sport_injuries"],
};

const SPORT_QUESTIONS = {
  sport_select:    {reply:"Which sport do you play?",                     input_type:"sport_select"},
  role:            {reply:"What's your role in cricket?",                 input_type:"cricket_role"},
  bowling_type:    {reply:"What type of bowler are you?",                 input_type:"bowling_type"},
  match_frequency: {reply:"How often do you play matches?",               input_type:"match_frequency"},
  primary_focus:   {reply:"What's your primary training focus?",          input_type:"primary_focus"},
  sport_injuries:  {reply:"Any sport-specific injuries or areas to protect?", input_type:"sport_injuries"},
  position:        {reply:"What position do you play?",                   input_type:"football_position"},
  distance_type:   {reply:"What type of running do you focus on?",        input_type:"distance_type"},
  weekly_mileage:  {reply:"What's your current weekly mileage / running volume?", input_type:"weekly_mileage"},
};

// ── INIT ──────────────────────────────────────────────────────────────
window.onload = async () => {
  initThemeEngine();
  if (authToken) {
    // Silent token validation - don't show errors on initial page load
    await continueAfterAuth(window.FC_INITIAL_TAB || "home", { silent: true });
  } else {
    showAuth();
  }
  initVoiceInput();
  updateModeUI();
  updateThemeSwitcher(document.documentElement.getAttribute("data-theme") || "galaxy");
};

// ── SCREENS ───────────────────────────────────────────────────────────
function showAuth() {
  document.getElementById("auth-screen").classList.add("active");
  document.getElementById("app-screen").classList.remove("active");
}
function showApp() {
  document.getElementById("auth-screen").classList.remove("active");
  document.getElementById("app-screen").classList.add("active");
}

// ── AUTH TABS ─────────────────────────────────────────────────────────
function switchAuthTab(tab) {
  document.querySelectorAll(".auth-tab").forEach((t,i) => {
    t.classList.toggle("active",(i===0&&tab==="login")||(i===1&&tab==="signup"));
  });
  document.getElementById("login-form").classList.toggle("hidden",tab!=="login");
  document.getElementById("signup-form").classList.toggle("hidden",tab!=="signup");
  document.getElementById("forgot-form").classList.add("hidden");
  document.getElementById("auth-error").classList.add("hidden");
  const hl = document.getElementById("auth-headline");
  const sl = document.getElementById("auth-subline");
  if (hl && sl) {
    if (tab === "signup") {
      hl.innerHTML = 'Start your <span>journey</span>';
      sl.textContent = "Create your free account in seconds";
    } else {
      hl.innerHTML = 'Welcome <span>back</span>';
      sl.textContent = "Sign in to continue your training";
    }
  }
}
function switchLoginMethod(m) {
  document.getElementById("method-password-btn").classList.toggle("active",m==="password");
  document.getElementById("method-otp-btn").classList.toggle("active",m==="otp");
  document.getElementById("login-password-section").classList.toggle("hidden",m!=="password");
  document.getElementById("login-otp-section").classList.toggle("hidden",m!=="otp");
}
function showForgotPassword() {
  document.getElementById("login-form").classList.add("hidden");
  document.getElementById("forgot-form").classList.remove("hidden");
  document.getElementById("auth-error").classList.add("hidden");
}
function showLoginForm() {
  document.getElementById("forgot-form").classList.add("hidden");
  document.getElementById("login-form").classList.remove("hidden");
}

// ── OTP FLOWS ─────────────────────────────────────────────────────────
function _storeTokens(d) {
  authToken = d.access_token;
  localStorage.setItem("fc_token", authToken);
  if (d.refresh_token) localStorage.setItem("fc_refresh", d.refresh_token);
}
async function continueAfterAuth(preferredTab = "home", options = {}) {
  const { silent = false } = options;
  let profile;
  try {
    profile = await apiFetch("/api/profile/me");
    currentUser = profile;
    onboardingGender = profile?.gender || "male";
    updateCoachHeader(profile?.name, profile?.gender);
  } catch (err) {
    authToken = null;
    currentUser = null;
    localStorage.removeItem("fc_token");
    localStorage.removeItem("fc_refresh");
    showAuth();
    // Only show error if not in silent mode (i.e., not on initial page load)
    if (!silent) {
      showAuthError(err.message || "Session verification failed. Please sign in again.");
    }
    return;
  }

  // Navigation is now guaranteed to load the main dashboard view
  showApp();

  try {
    if (profile?.onboarding_complete) {
      switchTab(preferredTab || "home");
      // loadRecoveryBanner() is now safe to call even if elements don't exist
      loadRecoveryBanner();
    } else {
      switchTab("chat");
    }
  } catch (err) {
    console.warn("Optional dashboard initialization failed:", err);
  }
}
async function sendSignupOTP() {
  const email = document.getElementById("signup-email").value.trim();
  if (!email) return showAuthError("Enter your email first");
  try {
    const res = await fetch(`${API}/api/auth/send-otp`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,purpose:"verify"})});
    const d = await res.json();
    if (!res.ok) return showAuthError(d.detail || "Failed");
    document.getElementById("signup-otp-section").classList.remove("hidden");
    document.getElementById("signup-send-otp-btn").textContent = "✅ OTP Sent";
    showToast("📧 OTP sent to "+email);
  } catch { showAuthError("Connection error"); }
}
async function sendLoginOTP() {
  const email = document.getElementById("login-email").value.trim();
  if (!email) return showAuthError("Enter your email");
  try {
    const res = await fetch(`${API}/api/auth/send-otp`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,purpose:"login"})});
    const d = await res.json();
    if (!res.ok) return showAuthError(d.detail || "Failed");
    document.getElementById("login-otp-input-wrap").classList.remove("hidden");
    showToast("📧 OTP sent to "+email);
  } catch { showAuthError("Connection error"); }
}
async function doLoginOTP() {
  const email = document.getElementById("login-email").value.trim();
  const code  = document.getElementById("login-otp-code").value.trim();
  if (!code) return showAuthError("Enter the OTP");
  try {
    const res = await fetch(`${API}/api/auth/verify-otp`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,otp:code,purpose:"login"})});
    const d = await res.json();
    if (!res.ok) return showAuthError(d.detail || "Invalid OTP");
    _storeTokens(d);
    await continueAfterAuth("home");
  } catch { showAuthError("Connection error"); }
}
async function sendResetOTP() {
  const email = document.getElementById("forgot-email").value.trim();
  if (!email) return showAuthError("Enter your email");
  try {
    const res = await fetch(`${API}/api/auth/send-otp`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,purpose:"reset"})});
    if (!res.ok) return showAuthError("Failed to send OTP");
    document.getElementById("forgot-step1").classList.add("hidden");
    document.getElementById("forgot-step2").classList.remove("hidden");
    showToast("📧 Reset code sent");
  } catch { showAuthError("Connection error"); }
}
async function doResetPassword() {
  const email   = document.getElementById("forgot-email").value.trim();
  const otp     = document.getElementById("forgot-otp").value.trim();
  const newPass = document.getElementById("forgot-newpass").value;
  if (!otp || !newPass) return showAuthError("Fill all fields");
  if (newPass.length < 8)
    return showAuthError("Password must be at least 8 characters");
  try {
    // Step 1: verify OTP — backend returns a short-lived reset_token
    const vRes  = await fetch(`${API}/api/auth/verify-otp`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,otp,purpose:"reset"})});
    const vData = await vRes.json();
    if (!vRes.ok) return showAuthError(vData.detail || "Invalid OTP");
    const resetToken = vData.reset_token;
    if (!resetToken) return showAuthError("OTP verification failed — try again");

    // Step 2: reset password using the token (server verifies it server-side)
    const rRes  = await fetch(`${API}/api/auth/reset-password`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email, new_password:newPass, reset_token:resetToken})});
    const rData = await rRes.json();
    if (!rRes.ok) return showAuthError(rData.detail || "Reset failed");
    showToast("Password reset! Sign in now.");
    showLoginForm();
  } catch { showAuthError("Connection error"); }
}
async function doLogin() {
  const email    = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  if (!email||!password) return showAuthError("Fill in all fields");
  _btnLock("login-btn", true);
  try {
    const res = await fetch(`${API}/api/auth/login`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,password})});
    const d = await res.json();
    if (!res.ok) { _btnLock("login-btn", false); return showAuthError(d.detail||"Login failed"); }
    _storeTokens(d);
    await continueAfterAuth("home");
  } catch (e) { _btnLock("login-btn", false); showAuthError("Connection error"); }
}
async function doSignup() {
  const email    = document.getElementById("signup-email").value.trim();
  const password = document.getElementById("signup-password").value;
  const otp      = document.getElementById("signup-otp-code").value.trim();
  if (!email||!password) return showAuthError("Fill all fields");
  if (!otp) return showAuthError("Verify email with OTP first");
  _btnLock("signup-btn", true);
  try {
    const vRes = await fetch(`${API}/api/auth/verify-otp`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,otp,purpose:"verify"})});
    if (!vRes.ok) { _btnLock("signup-btn", false); return showAuthError("Invalid OTP"); }
    const res = await fetch(`${API}/api/auth/signup`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,password})});
    const d = await res.json();
    if (!res.ok) { _btnLock("signup-btn", false); return showAuthError(d.detail||"Signup failed"); }
    _storeTokens(d);
    await continueAfterAuth("home");
  } catch (e) { _btnLock("signup-btn", false); showAuthError("Connection error"); }
}
function doLogout(clearInputs = true) {
  // Clear in-memory auth variables
  authToken = null;
  currentUser = null;

  // Clear all localStorage auth data
  localStorage.removeItem("fc_token");
  localStorage.removeItem("fc_refresh");

  // Clear sessionStorage (if any)
  sessionStorage.clear();

  // Clear all auth form fields
  if (clearInputs) {
    const formFields = [
      "login-email",
      "login-password",
      "login-otp-code",
      "signup-email",
      "signup-password",
      "signup-otp-code",
      "forgot-email",
      "forgot-otp",
      "forgot-newpass"
    ];
    formFields.forEach(fieldId => {
      const el = document.getElementById(fieldId);
      if (el) {
        el.value = "";
      }
    });
  }

  // Reset auth forms to default state (show login, hide others)
  document.getElementById("login-form").classList.remove("hidden");
  document.getElementById("signup-form").classList.add("hidden");
  document.getElementById("forgot-form").classList.add("hidden");

  // Reset login method to password
  document.getElementById("method-password-btn").classList.add("active");
  document.getElementById("method-otp-btn").classList.remove("active");
  document.getElementById("login-password-section").classList.remove("hidden");
  document.getElementById("login-otp-section").classList.add("hidden");

  // Hide OTP sections
  document.getElementById("signup-otp-section").classList.add("hidden");
  document.getElementById("forgot-step1").classList.remove("hidden");
  document.getElementById("forgot-step2").classList.add("hidden");

  // Hide error messages
  document.getElementById("auth-error").classList.add("hidden");

  // Reset button states
  _btnLock("login-btn", false);
  _btnLock("signup-btn", false);
  _btnLock("signup-send-otp-btn", false);

  // Reset auth tabs
  document.querySelectorAll(".auth-tab").forEach((t, i) => {
    t.classList.toggle("active", i === 0);
  });

  // Reset auth headlines
  const hl = document.getElementById("auth-headline");
  const sl = document.getElementById("auth-subline");
  if (hl && sl) {
    hl.innerHTML = 'Welcome <span>back</span>';
    sl.textContent = "Sign in to continue your training";
  }

  // Clear chat and workout state
  document.getElementById("chat-box").innerHTML = "";
  workoutActive = false;
  feedbackMode = false;

  // Clear onboarding state variables
  onboardingField = null;
  onboardingInputType = null;
  onboardingGender = "male";
  sportObField = null;
  sportObInputType = null;
  sportObSport = null;
  recoveryInputs = {};
  foodPhotoBase64 = null;

  // Show auth screen
  showAuth();
}
function showAuthError(msg) {
  const el = document.getElementById("auth-error");
  if (!msg){el.classList.add("hidden");return;}
  el.textContent = msg; el.classList.remove("hidden");
}

// ── PASSWORD VISIBILITY TOGGLE ─────────────────────────────────────────
function togglePasswordVisibility(inputId, button) {
  const input = document.getElementById(inputId);
  if (!input) return;
  
  const isPassword = input.type === 'password';
  input.type = isPassword ? 'text' : 'password';
  
  // Update button visual state
  button.classList.toggle('visible', !isPassword);
  button.querySelector('.eye-icon').textContent = isPassword ? '🙈' : '👁️';
  
  // Update accessibility
  button.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
}

// ── API ───────────────────────────────────────────────────────────────
async function apiFetch(url, options={}) {
  let res;
  const { ignore401, ...fetchOptions } = options;
  try {
    res = await fetch(`${API}${url}`, {
      ...fetchOptions,
      headers:{"Content-Type":"application/json","Authorization":`Bearer ${authToken}`,...(fetchOptions.headers||{})}
    });
  } catch (networkErr) {
    showToast("Connection error — check your internet.");
    throw networkErr;
  }
  if (res.status === 401) { 
    if (!ignore401) {
      doLogout(false); 
    }
    throw new Error("Unauthorized"); 
  }
  if (res.status === 429) {
    showToast("Too many requests — slow down a moment.");
    throw new Error("Rate limited");
  }
  if (res.status >= 500) {
    showToast("Server error — try again in a moment.");
    throw new Error(`Server error ${res.status}`);
  }
  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("application/json")) {
    throw new Error("Unexpected response from server");
  }
  return res.json();
}

function _btnLock(btnId, loading=true) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.disabled = loading;
  btn._origText = btn._origText || btn.textContent;
  btn.textContent = loading ? "Please wait..." : btn._origText;
}

// ── WORKOUT MODE ──────────────────────────────────────────────────────
function setWorkoutMode(mode) {
  // Guard: sport mode requires sport profile
  if (mode === "sport" && !(currentUser?.plays_sport && currentUser?.sport)) {
    showToast("Complete sport setup first!");
    setTimeout(() => startSportOnboarding(), 300);
    return;
  }
  workoutMode = mode;
  localStorage.setItem("fc_workout_mode", mode);
  updateModeUI();
  const modeLabel = mode === "sport" ? "Sport Mode 🏆" : "Gym Mode 🏋️";
  showToast(`Switched to ${modeLabel}`);
}
function updateModeUI() {
  const isSport = workoutMode === "sport";
  // Sidebar
  document.getElementById("mode-gym-btn")?.classList.toggle("active",  !isSport);
  document.getElementById("mode-sport-btn")?.classList.toggle("active", isSport);
  // Mobile compact
  document.getElementById("mp-gym")?.classList.toggle("active",   !isSport);
  document.getElementById("mp-sport")?.classList.toggle("active",  isSport);
  // Header label
  const lbl = document.getElementById("coach-mode-label");
  if (lbl) lbl.textContent = isSport ? "Sport Mode 🏆" : "Gym Mode 🏋️";
  const sidebarMode = document.getElementById("sidebar-mode-readout");
  if (sidebarMode) sidebarMode.textContent = isSport ? "Sport" : "Gym";
  const protocolChip = document.getElementById("coach-protocol-chip");
  if (protocolChip) protocolChip.textContent = isSport ? "Sport focus" : "Strength focus";
  const currentSplit = document.getElementById("coach-current-split");
  if (currentSplit) currentSplit.textContent = isSport ? "Sport Mode" : "Gym Mode";
  // Avatar
  const av = document.getElementById("coach-avatar");
  if (av) av.textContent = isSport ? "🏆" : "⚡";
}

// ── TABS ──────────────────────────────────────────────────────────────
function switchTab(tab) {
  document.querySelectorAll(".tab-content").forEach(t=>t.classList.remove("active"));
  document.querySelectorAll(".nav-btn,.bnav-btn").forEach(b=>{
    b.classList.toggle("active",b.dataset.tab===tab);
  });
  const target = document.getElementById(`tab-${tab}`);
  if (!target) return;
  target.classList.add("active");
  if (localStorage.getItem("fc_theme_auto") === "1") {
    applyAthleteTheme(AUTO_THEME_BY_TAB[tab] || "galaxy", { previewOnly: true });
  }
  if (tab==="home") loadHomeDashboard();
  if (tab==="progress") loadProgress();
  if (tab==="profile")  loadProfile();
  if (tab==="recovery") loadRecoveryLatest();
  if (tab==="chat") {
    const chatBox = document.getElementById("chat-box");
    if (chatBox && chatBox.children.length === 0) loadChat();
  }
  if (tab==="trainer") window.fitCoachGhostTrainer?.init();
  if (tab!=="trainer") window.fitCoachGhostTrainer?.stop();
}

// ── CHAT ──────────────────────────────────────────────────────────────
function loadChat() {
  document.getElementById("chat-box").innerHTML = "";
  callServer(""); // triggers greeting or onboarding
}

function cleanDisplayText(text) {
  return String(text || "")
    .replace(/âœ…|âœ“/g, "OK")
    .replace(/â€”|â€“/g, "-")
    .replace(/Ã—/g, "x")
    .replace(/â†’/g, "->")
    .replace(/ðŸ”¥|ðŸ’ª|ðŸŒ¿|ðŸ“Š|ðŸ|ðŸ†|ðŸŽ‰|ðŸ‘‹|âš¡|â˜€ï¸|ðŸŒ¤ï¸|ðŸŒ™/g, "")
    .replace(/[^\x09\x0A\x0D\x20-\x7E]/g, "")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
}

function addMessage(text, sender) {
  const chatBox = document.getElementById("chat-box");
  const msg = document.createElement("div");
  msg.className = `message ${sender}`;
  msg.innerHTML = cleanDisplayText(text)
    .replace(/\*\*(.*?)\*\*/g,"<strong>$1</strong>")
    .replace(/_(.*?)_/g,"<em>$1</em>")
    .replace(/\n/g,"<br>");
  chatBox.appendChild(msg);
  scrollToBottom();
  return msg;
}

function escapeHtml(value) {
  return cleanDisplayText(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function titleCase(value) {
  return cleanDisplayText(value || "")
    .replace(/[_-]/g, " ")
    .replace(/\w\S*/g, (txt) => txt.charAt(0).toUpperCase() + txt.slice(1).toLowerCase());
}

function estimateCalories(exercises, duration) {
  const count = Array.isArray(exercises) ? exercises.length : 0;
  const mins = Number(duration) || Math.max(28, count * 8);
  return Math.round(mins * 7.2 / 10) * 10;
}

function extractInsightLines(reply, max = 4) {
  const text = cleanDisplayText(reply);
  return text
    .split(/\n+/)
    .map((line) => line.replace(/^[-*\d.\s]+/, "").trim())
    .filter((line) => line && !/^today:|^ready\?|^this week:/i.test(line))
    .slice(0, max);
}

function exerciseIcon(exercise) {
  const hay = `${exercise?.name || ""} ${exercise?.muscle || ""} ${exercise?.category || ""}`.toLowerCase();
  if (hay.includes("run") || hay.includes("sprint")) return "RUN";
  if (hay.includes("press") || hay.includes("push") || hay.includes("chest")) return "PRS";
  if (hay.includes("squat") || hay.includes("leg") || hay.includes("lunge")) return "LEG";
  if (hay.includes("row") || hay.includes("pull") || hay.includes("back")) return "PULL";
  if (hay.includes("core") || hay.includes("plank") || hay.includes("abs")) return "CORE";
  if (hay.includes("mobility") || hay.includes("stretch")) return "REC";
  return "AI";
}

function renderCoachResponse(data) {
  const chatBox = document.getElementById("chat-box");
  
  if (["workout_start", "workout_next_set", "workout_next_exercise"].includes(data.type)) {
    transitionToWorkout(data);
    if (data.reply) {
      pushPopoverMessage(data.reply);
    }
    return null;
  }
  
  if (["workout_all_done", "feedback_received", "workout_logged"].includes(data.type)) {
    transitionToComplete(data);
    return null;
  }

  // For most responses, just show a simple message like ChatGPT
  if (!["daily_plan", "workout_start", "workout_next_set", "workout_next_exercise", "workout_all_done", "feedback_received", "workout_logged"].includes(data.type)) {
    const msg = document.createElement("div");
    msg.className = "message bot";
    msg.innerHTML = cleanDisplayText(data.reply)
      .replace(/\*\*(.*?)\*\*/g,"<strong>$1</strong>")
      .replace(/_(.*?)_/g,"<em>$1</em>")
      .replace(/\n/g,"<br>");
    chatBox.appendChild(msg);
    
    // Add compact coach tip card occasionally
    if (data.reply && Math.random() > 0.7) {
      const tip = document.createElement("div");
      tip.className = "coach-tip-card";
      tip.innerHTML = `<span class="tip-icon">💡</span><span class="tip-text">Stay consistent — small wins add up!</span>`;
      chatBox.appendChild(tip);
    }
    
    if (data.reply) {
      pushPopoverMessage(data.reply);
    }

    scrollToBottom();
    return msg;
  }
  
  // For workout-specific responses, use the dashboard
  const panel = document.createElement("section");
  panel.className = `coach-dashboard-response ${data.type || "chat"}`;
  panel.innerHTML = buildCoachDashboardHtml(data);
  chatBox.appendChild(panel);
  wireCoachDashboard(panel);
  scrollToBottom();
  return panel;
}

function buildCoachDashboardHtml(data) {
  if (["daily_plan", "workout_start", "workout_next_set", "workout_next_exercise"].includes(data.type)) {
    return buildWorkoutDashboard(data);
  }
  if (data.type === "workout_all_done") return buildCompletionDashboard(data, false);
  if (data.type === "feedback_received") return buildCompletionDashboard(data, true);
  if (data.type === "workout_logged") return buildLoggedDashboard(data);
  if (data.type === "daily_greeting") return buildGreetingDashboard(data);
  if ((data.reply || "").toLowerCase().includes("protein") || (data.reply || "").toLowerCase().includes("calorie") || (data.reply || "").toLowerCase().includes("nutrition") || (data.reply || "").toLowerCase().includes("meal")) {
    return buildNutritionDashboard(data);
  }
  return buildInsightDashboard(data);
}

function buildWorkoutDashboard(data) {
  const exercises = data.exercises || (data.current_exercise ? [data.current_exercise] : []);
  const currentIdx = data.current_exercise_index ?? 0;
  const total = data.total_exercises || exercises.length || 1;
  const currentSet = data.current_set || 1;
  const active = data.current_exercise || exercises[currentIdx] || exercises[0] || {};
  const muscle = data.muscle_group || data.today_muscle || active.muscle || "AI Workout";
  const zone = data.zone || "green";
  const duration = Math.max(30, exercises.length * 8 + 8);
  const pct = data.type === "daily_plan" ? 0 : Math.min(96, Math.round(((currentIdx + (currentSet - 1) / Math.max(active.sets || 3, 1)) / total) * 100));
  const focus = data.workout_mode === "sport" ? "Sport Performance" : "Strength + Hypertrophy";
  const heroTitle = titleCase(muscle);
  const insightLines = extractInsightLines(data.reply, 3);
  const exerciseCards = exercises.map((ex, idx) => buildExerciseCard(ex, idx, currentIdx, data.type)).join("");
  const weekly = buildWeeklyPlanner(data.weekly_plan);
  const splitIntel = buildSplitIntelligence(data, exercises, currentIdx, pct);

  return `
    <div class="coach-hero-card zone-${escapeHtml(zone)}">
      <div class="coach-hero-copy">
        <div class="coach-kicker">AI Workout OS</div>
        <h3>${heroTitle}</h3>
        <p>${escapeHtml(focus)} - ${zone === "red" ? "Recovery optimized" : zone === "yellow" ? "Intensity moderated" : "Recovery optimized"}</p>
      </div>
      <div class="coach-hero-metrics">
        <div><strong>${duration}</strong><span>min</span></div>
        <div><strong>${estimateCalories(exercises, duration)}</strong><span>kcal</span></div>
        <div><strong>${escapeHtml(zone.toUpperCase())}</strong><span>readiness</span></div>
      </div>
      <div class="coach-orbit-meter" style="--progress:${pct}%"><span>${pct}%</span></div>
    </div>
    <div class="coach-insight-strip">
      ${insightLines.map((line, i) => `<div class="ai-insight-card"><span>${["AI","PWR","REC","FOC"][i] || "AI"}</span>${escapeHtml(line)}</div>`).join("") || `<div class="ai-insight-card"><span>AI</span>Session loaded and ready.</div>`}
    </div>
    ${splitIntel}
    <div class="coach-section">
      <button class="coach-section-toggle" type="button" data-toggle-section>
        <span>Exercise Stack</span><small>${currentIdx + 1}/${total} active</small>
      </button>
      <div class="exercise-card-grid">${exerciseCards}</div>
    </div>
    ${weekly}
  `;
}

function buildSplitIntelligence(data, exercises, currentIdx, pct) {
  const zone = data.zone || "green";
  const session = data.muscle_group || data.today_muscle || "Workout";
  const families = new Set(exercises.map((ex) => (ex.category || ex.muscle || "").toLowerCase().split(/[,+/]/)[0]).filter(Boolean));
  const load = zone === "red" ? 38 : zone === "yellow" ? 68 : 88;
  const timeline = exercises.slice(0, 5).map((ex, idx) => `
    <div class="session-timeline-step ${idx < currentIdx ? "done" : idx === currentIdx && data.type !== "daily_plan" ? "active" : ""}">
      <span></span><strong>${escapeHtml(ex.name || `Block ${idx + 1}`)}</strong>
    </div>
  `).join("");
  return `
    <div class="ai-workspace-grid">
      <div class="readiness-widget" style="--readiness:${load}%">
        <div class="readiness-ring"><strong>${load}</strong><span>readiness</span></div>
        <p>${zone === "red" ? "Recovery-biased session selected." : zone === "yellow" ? "Load moderated for clean output." : "High-output training window detected."}</p>
      </div>
      <div class="muscle-heat-widget">
        <div class="panel-title-row"><span>Muscle Heat</span><small>${escapeHtml(families.size || 1)} zones</small></div>
        <div class="muscle-heat-bars">
          ${["lower","push","pull","core","engine"].map((name, idx) => `<div><span>${name}</span><i style="--heat:${Math.max(18, Math.min(96, pct + 18 - idx * 9))}%"></i></div>`).join("")}
        </div>
      </div>
      <div class="session-timeline-card">
        <div class="panel-title-row"><span>Session Timeline</span><small>${escapeHtml(session)}</small></div>
        <div class="session-timeline">${timeline}</div>
      </div>
    </div>
  `;
}

function buildExerciseCard(ex, idx, activeIdx, responseType) {
  const isActive = idx === activeIdx && responseType !== "daily_plan";
  const isDone = responseType !== "daily_plan" && idx < activeIdx;
  const sets = ex?.sets || 3;
  const reps = ex?.reps || "10";
  const muscle = ex?.muscle || ex?.category || "Full body";
  const difficulty = ex?.intensity || ex?.difficulty || "guided";
  const equipment = Array.isArray(ex?.equipment) ? ex.equipment.join(", ") : (ex?.equipment || ex?.weight_guide || "Body control");
  const tip = Array.isArray(ex?.progression) ? ex.progression[0] : (ex?.weight_guide || "Move with clean control and own every rep.");
  return `
    <article class="exercise-ai-card ${isActive ? "active" : ""} ${isDone ? "complete" : ""}" draggable="true">
      <div class="exercise-visual"><span>${exerciseIcon(ex)}</span></div>
      <div class="exercise-card-main">
        <div class="exercise-topline">
          <h4>${escapeHtml(ex?.name || "Exercise")}</h4>
          <span class="exercise-state">${isDone ? "Done" : isActive ? "Live" : `#${idx + 1}`}</span>
        </div>
        <div class="exercise-prescription">
          <span>${escapeHtml(sets)} sets</span><span>${escapeHtml(reps)} reps</span><span>${escapeHtml(ex?.rest || "60s")}</span>
        </div>
        <div class="exercise-tags">
          <span>${escapeHtml(muscle)}</span><span>${escapeHtml(difficulty)}</span><span>${escapeHtml(equipment)}</span>
        </div>
        <p>${escapeHtml(tip)}</p>
        <div class="exercise-actions">
          <button type="button" data-command="${isActive ? "next" : "start"}">${isActive ? "Complete Set" : "Start"}</button>
          <button type="button" data-command="replace ${escapeHtml(ex?.name || "")}">Replace</button>
          <button type="button" data-command="next">Skip</button>
          <button type="button" data-command="easy">Easier</button>
          <button type="button" data-command="hard">Harder</button>
        </div>
      </div>
    </article>
  `;
}

function buildWeeklyPlanner(plan) {
  if (!Array.isArray(plan) || !plan.length) return "";
  const today = new Date().getDay();
  const dayMap = {0:"Sun",1:"Mon",2:"Tue",3:"Wed",4:"Thu",5:"Fri",6:"Sat"};
  return `
    <div class="weekly-planner-panel">
      <div class="panel-title-row"><span>Weekly Planner</span><small>Drag to visualize your split</small></div>
      <div class="weekly-day-track">
        ${plan.slice(0, 7).map((slot, idx) => {
          const label = slot.day || dayMap[idx] || `Day ${idx + 1}`;
          const active = slot.day_index === today || label.slice(0,3).toLowerCase() === dayMap[today].toLowerCase();
          const title = slot.rest ? "Recovery" : (slot.label || slot.muscle || "Workout");
          return `<div class="planner-day-card ${active ? "active" : ""} ${slot.rest ? "rest" : ""}" draggable="true">
            <strong>${escapeHtml(label)}</strong><span>${escapeHtml(title)}</span><small>${active ? "Today" : slot.rest ? "Restore" : "Planned"}</small>
          </div>`;
        }).join("")}
      </div>
    </div>
  `;
}

function buildCompletionDashboard(data, readyToLog) {
  const lines = extractInsightLines(data.reply, 3);
  return `
    <div class="session-status-grid">
      <div class="status-card primary"><span>Workout Complete</span><strong>${readyToLog ? "Ready" : "Feedback"}</strong><small>${readyToLog ? "Log the session" : "Tell the coach how it felt"}</small></div>
      <div class="status-card"><span>Calories</span><strong>${estimateCalories([], 45)}</strong><small>estimated burn</small></div>
      <div class="status-card"><span>Recovery</span><strong>Hydrate</strong><small>Protein plus fluids next</small></div>
    </div>
    <div class="coach-insight-strip">${lines.map((line) => `<div class="ai-insight-card"><span>AI</span>${escapeHtml(line)}</div>`).join("")}</div>
  `;
}

function buildLoggedDashboard(data) {
  return `
    <div class="session-status-grid">
      <div class="status-card primary"><span>Completion Badge</span><strong>Logged</strong><small>Workout saved</small></div>
      <div class="status-card"><span>Streak</span><strong>${escapeHtml(data.streak || 0)}</strong><small>days</small></div>
      <div class="status-card"><span>Duration</span><strong>${escapeHtml(data.duration || 0)}</strong><small>minutes</small></div>
      <div class="status-card"><span>Next Split</span><strong>${escapeHtml(data.next_session || "Rotated")}</strong><small>planner updated</small></div>
    </div>
    <div class="ai-insight-card wide"><span>REC</span>Rest, hydrate, and give the next session clean data.</div>
    ${buildWeeklyPlanner(data.weekly_plan)}
  `;
}

function buildNutritionDashboard(data) {
  const lines = extractInsightLines(data.reply, 6);
  const protein = lines.find((l) => /protein/i.test(l)) || "Protein Goal - 120-160g daily";
  const hydration = lines.find((l) => /water|hydr/i.test(l)) || "Hydration - 2.5L baseline";
  const recovery = lines.find((l) => /recover|omega|turmeric|ginger|meal/i.test(l)) || "Recovery Foods - Omega-3, turmeric, ginger";
  return `
    <div class="nutrition-card-grid">
      <div class="macro-card"><span>Protein Goal</span><strong>${escapeHtml(protein.replace(/^protein goal[:\s-]*/i, ""))}</strong></div>
      <div class="macro-card green"><span>Hydration</span><strong>${escapeHtml(hydration.replace(/^hydration[:\s-]*/i, ""))}</strong></div>
      <div class="macro-card orange"><span>Recovery Foods</span><strong>${escapeHtml(recovery.replace(/^recovery foods[:\s-]*/i, ""))}</strong></div>
    </div>
    <div class="coach-insight-strip">${lines.slice(0, 3).map((line) => `<div class="ai-insight-card"><span>NUT</span>${escapeHtml(line)}</div>`).join("")}</div>
  `;
}

function buildGreetingDashboard(data) {
  const name = currentUser?.name || "Athlete";
  const todayMuscle = data.today_muscle || "Full Body";
  const streak = data.streak || 0;
  const zone = data.zone || "green";
  const zoneEmoji = zone === "green" ? "✅" : zone === "yellow" ? "⚠️" : "🔴";
  const zoneLabel = zone === "green" ? "Fully recovered" : zone === "yellow" ? "Moderate recovery" : "Light day recommended";
  const modeLabel = (data.workout_mode || workoutMode) === "sport" ? "SPT" : (data.workout_mode || workoutMode) === "home" ? "HOM" : "GYM";
  const streakTxt = streak > 0 ? `🔥 ${streak} day streak` : "Start your streak!";

  // Build exercise preview chips (up to 3)
  const exChips = (data.exercises || []).slice(0, 3).map(ex => {
    const exName = ex.name || ex.exercise || "";
    return `<span class="ex-chip">${escapeHtml(exName)}</span>`;
  }).join("");

  return `
    <div class="coach-hero-card compact">
      <div class="coach-hero-copy">
        <div class="coach-kicker">FitCoach AI · Ready</div>
        <h3>Good to see you, ${escapeHtml(name)}!</h3>
        <p>💪 Today: <strong>${escapeHtml(todayMuscle)}</strong></p>
        <p>${zoneEmoji} Recovery: <strong>${zone.toUpperCase()}</strong> — ${zoneLabel}</p>
      </div>
      <div class="coach-hero-metrics">
        <div><strong>${streak}</strong><span>streak</span></div>
        <div><strong>${modeLabel}</strong><span>mode</span></div>
      </div>
    </div>
    ${exChips ? `<div class="coach-exercise-preview">Today's exercises: ${exChips}</div>` : ""}
    <div class="coach-insight-strip">
      <div class="ai-insight-card wide"><span>💪</span>${escapeHtml(streakTxt)} — ${escapeHtml(todayMuscle)} session queued</div>
    </div>
  `;
}

function buildInsightDashboard(data) {
  const lines = extractInsightLines(data.reply, 5);
  return `
    <div class="insight-dashboard">
      <div class="panel-title-row"><span>Your Coach</span><small>reply</small></div>
      <div class="coach-insight-strip vertical">
        ${lines.map((line, i) => `<div class="ai-insight-card ${i === 0 ? "wide" : ""}"><span>${i === 0 ? "💪" : "TIP"}</span>${escapeHtml(line)}</div>`).join("") || `<div class="ai-insight-card wide"><span>💪</span>${escapeHtml(data.reply || "Ready when you are.")}</div>`}
      </div>
    </div>
  `;
}

function wireCoachDashboard(panel) {
  panel.querySelectorAll("[data-command]").forEach((btn) => {
    btn.addEventListener("click", () => quickSend(btn.dataset.command));
  });
  panel.querySelectorAll("[data-toggle-section]").forEach((btn) => {
    btn.addEventListener("click", () => btn.closest(".coach-section")?.classList.toggle("collapsed"));
  });
  panel.querySelectorAll("[draggable='true']").forEach((card) => {
    card.addEventListener("dragstart", () => card.classList.add("dragging"));
    card.addEventListener("dragend", () => card.classList.remove("dragging"));
  });
}

function addCoachOptions(options) {
  if (!Array.isArray(options) || !options.length) return;
  const chatBox = document.getElementById("chat-box");
  const wrap = document.createElement("div");
  wrap.className = "coach-option-panel";
  options.forEach((opt) => {
    const btn = document.createElement("button");
    btn.className = "qa-btn focus-option";
    btn.type = "button";
    btn.textContent = cleanDisplayText(opt.label || opt.command || "Start");
    btn.onclick = () => quickSend(opt.command || opt.label);
    wrap.appendChild(btn);
  });
  chatBox.appendChild(wrap);
  scrollToBottom();
}
function scrollToBottom() {
  const messagesContainer = document.getElementById("chat-box");
  if (messagesContainer) {
    setTimeout(() => {
      messagesContainer.scrollTo({
        top: messagesContainer.scrollHeight,
        behavior: "smooth"
      });
    }, 50);
  }
}
function showTyping() {
  removeTyping();
  const t = document.createElement("div");
  t.className="typing-indicator"; t.id="typing-indicator";
  t.innerHTML=`<div class="typing-dots"><span></span><span></span><span></span></div><span class="typing-text">Coach is typing...</span>`;
  document.getElementById("chat-box").appendChild(t);
  scrollToBottom();
}
function removeTyping() { document.getElementById("typing-indicator")?.remove(); }
function handleKey(e) { if(e.key==="Enter") sendMessage(); }
function quickSend(text) { document.getElementById("message").value=text; sendMessage(); }
function workoutAction(action) { document.getElementById("message").value=action; sendMessage(); }
function startWorkout() { document.getElementById("message").value="start"; sendMessage(); }

function syncGhostWorkout(data) {
  if (!data?.exercises?.length) return;
  const payload = {
    muscle_group: data.muscle_group,
    workout_mode: data.workout_mode,
    exercises: data.exercises,
    ghost_trainer: data.ghost_trainer || null,
    updated_at: new Date().toISOString(),
  };
  localStorage.setItem("fc_active_workout", JSON.stringify(payload));
  window.dispatchEvent(new CustomEvent("fitcoach:workout-loaded", { detail: payload }));
}

function sendMessage() {
  const input = document.getElementById("message");
  const text  = input.value.trim();
  if (!text) return;
  addMessage(text,"user");
  input.value = "";
  callServer(text);
}

async function callServer(message) {
  const inOnboarding = !document.getElementById("onboarding-overlay").classList.contains("hidden");
  if (!inOnboarding) showTyping();
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 20000);
  try {
    console.log(`[Coach API] Sending request: ${message.substring(0, 50)}...`);
    const res = await fetch(`${API}/api/coach/chat`,{
      method:"POST",
      headers:{"Content-Type":"application/json","Authorization":`Bearer ${authToken}`},
      body: JSON.stringify({message, mode: workoutMode}),
      signal: controller.signal
    });
    
    console.log(`[Coach API] Response status: ${res.status}`);
    
    if (res.status===401){doLogout(false);return;}
    
    const data = await res.json();
    console.log(`[Coach API] Response data:`, data);
    
    if (!res.ok) {
      const errorDetail = data?.detail || data?.error || "Coach request failed";
      console.error(`[Coach API] Error response: ${errorDetail}`);
      throw new Error(errorDetail);
    }
    
    window.clearTimeout(timeoutId);
    if (!inOnboarding) removeTyping();
    handleResponse(data);
  } catch (err) {
    console.error(`[Coach API] Request failed:`, err);
    window.clearTimeout(timeoutId);
    if (!inOnboarding) { 
      removeTyping();
      
      // Determine specific error type
      let errorMessage = "⚠️ Connection issue. Is the server running?";
      
      if (err.name === "AbortError") {
        errorMessage = "⏱️ Request timed out. The server took too long to respond.";
      } else if (err.message) {
        // Backend returned a specific error
        if (err.message.includes("Server error")) {
          errorMessage = `⚠️ Server error: ${err.message.replace("Server error: ", "")}`;
        } else if (err.message.includes("Profile not found")) {
          errorMessage = "⚠️ Profile not found. Please complete onboarding first.";
        } else if (err.message.includes("rate_limit") || err.message.includes("429")) {
          errorMessage = "⚠️ Rate limit exceeded. Please wait a moment and try again.";
        } else if (err.message.includes("authentication") || err.message.includes("401")) {
          errorMessage = "⚠️ Authentication error. Please log in again.";
        } else {
          errorMessage = `⚠️ ${err.message}`;
        }
      }
      
      addMessage(errorMessage, "bot");
    }
  }
}

// ── RESPONSE HANDLER ──────────────────────────────────────────────────
function handleResponse(data) {
  // Backend nests type-specific fields under ChatResponse.data — flatten
  // them onto the top level so the rest of this function (and the handlers
  // it calls) can keep reading e.g. data.field / data.profile / data.plan.
  if (data && data.data && typeof data.data === "object") {
    data = {...data, ...data.data};
  }
  // GENERAL ONBOARDING
  if (data.type==="onboarding") { showOnboardingStep(data); return; }

  if (data.type==="onboarding_complete") {
    hideOnboarding();
    apiFetch("/api/profile/me").then(profile => {
      currentUser = profile;
      onboardingGender = profile?.gender || "male";
      updateCoachHeader(profile?.name, profile?.gender);
    }).catch(()=>{});
    addMessage(data.reply,"bot");
    showQuickActions();
    return;
  }

  // ONBOARDING COMPLETE + start sport setup
  if (data.type==="onboarding_complete_sport") {
    hideOnboarding();
    currentUser = data.profile;
    onboardingGender = data.profile?.gender || "male";
    updateCoachHeader(data.profile?.name, data.profile?.gender);
    addMessage(data.reply,"bot");
    // Auto-start sport onboarding
    if (data.start_sport_onboard) {
      setTimeout(() => startSportOnboarding(), 600);
    }
    return;
  }

  // SPORT ONBOARDING — handled separately by sportOnboardingNext()
  // but if somehow triggered from chat, show overlay
  if (data.type==="sport_onboarding") { showSportOnboardingStep(data); return; }

  // SPORT MODE GUARD — backend tells us user needs sport onboarding first
  if (data.type==="sport_onboarding_prompt" || data.type==="sport_onboarding_required") {
    addMessage(data.reply, "bot");
    if (data.start_sport_onboard) {
      setTimeout(() => startSportOnboarding(), 600);
    }
    return;
  }

  if (data.type==="sport_onboarding_complete") {
    hideSportOnboarding();
    currentUser = {...(currentUser||{}), plays_sport:true, sport:data.sport, sport_profile:data.sport_profile};
    const sport = (data.sport||"").charAt(0).toUpperCase()+(data.sport||"").slice(1);
    addMessage(data.reply,"bot");
    showToast(`🏆 Sport Mode: ${sport} activated!`);
    setWorkoutMode("sport");
    updateProfileSportBadge();
    showQuickActions();
    return;
  }

  // Chat messages
  renderCoachResponse(data);
  if (data.options) addCoachOptions(data.options);
  const gender = currentUser?.gender || onboardingGender || "male";
  speakResponse(data, gender);

  switch(data.type) {
    case "daily_greeting":
      updateStreak(data.streak||0);
      showQuickActions();
      hideWorkoutUI();
      if (data.streak > 0) updateStreak(data.streak);
      break;
    case "workout_start":
      workoutActive=true; feedbackMode=false;
      syncGhostWorkout(data);
      showWorkoutProgress(data);
      showExerciseDemo(data.current_exercise, data.current_exercise_index, data.total_exercises, data.zone);
      hideQuickActions(); showWorkoutButtons(); hideFeedbackButtons();
      break;
    case "workout_next_set":
    case "workout_next_exercise":
      showWorkoutProgress(data);
      showExerciseDemo(data.current_exercise, data.current_exercise_index, data.total_exercises);
      startRestTimer(data.current_exercise?.rest);
      showWorkoutButtons(); hideFeedbackButtons();
      break;
    case "workout_all_done":
      workoutActive=false; feedbackMode=true;
      hideWorkoutUI(); showFeedbackButtons();
      break;
    case "feedback_received":
      hideFeedbackButtons(); showDoneButton();
      break;
    case "workout_logged":
      workoutActive=false; feedbackMode=false;
      hideWorkoutUI(); hideWorkoutButtons(); hideFeedbackButtons(); showQuickActions();
      launchConfetti();
      updateStreak(data.streak||0);
      showToast(`🎉 Workout ${data.total_workouts} done! ${data.duration} min`);
      if (data.new_badge) setTimeout(()=>showToast(`🏆 ${data.new_badge.badge_icon} ${data.new_badge.badge_name}`),2500);
      loadProgress();
      break;
    case "weight_logged":
      showToast(`✅ Weight: ${data.weight} kg logged`);
      loadProgress();
      break;
  }
}

// ── GENERAL ONBOARDING ────────────────────────────────────────────────
const GENERAL_FIELD_ORDER = ["name","date_of_birth","gender","height","weight","goal","level","workout_place","days_per_week","injuries","plays_sport"];
const GENERAL_QUESTIONS_MAP = {
  name:{reply:"Hey! 👋 What should I call you?",input_type:"text"},
  dob:{reply:"What's your date of birth?",input_type:"dob"},
  gender:{reply:"What's your gender?",input_type:"gender"},
  height:{reply:"What's your height?",input_type:"height"},
  weight:{reply:"What's your current weight?",input_type:"weight"},
  goal:{reply:"What's your primary fitness goal?",input_type:"goal"},
  level:{reply:"What's your fitness experience level?",input_type:"level"},
  workout_place:{reply:"Where do you prefer to work out?",input_type:"place"},
  days_per_week:{reply:"How many days per week can you train?",input_type:"days"},
  injuries:{reply:"Any injuries or pain I should know about?",input_type:"injuries"},
  plays_sport:{reply:"Do you play any sport competitively or recreationally?",input_type:"plays_sport"},
};

function showOnboardingStep(data) {
  document.getElementById("onboarding-overlay").classList.remove("hidden");
  onboardingField     = data.field;
  onboardingInputType = data.input_type;
  if (data.gender) onboardingGender = data.gender;

  const idx = GENERAL_FIELD_ORDER.indexOf(data.field);
  const total = GENERAL_FIELD_ORDER.length;
  document.getElementById("ob-progress-fill").style.width = ((idx/total)*100)+"%";
  document.getElementById("ob-step-label").textContent = `Step ${idx+1} of ${total}`;
  document.getElementById("ob-question").textContent = data.reply;
  document.getElementById("ob-error").classList.add("hidden");

  renderObInput("ob-input-area", data.field, data.gender || onboardingGender);
}

function renderObInput(areaId, field, gender) {
  const area = document.getElementById(areaId);
  area.innerHTML = "";

  switch(field) {
    case "name":
      area.innerHTML=`<input class="ob-text-input" id="ob-val" type="text" placeholder="Type your name…"/>`;
      setTimeout(()=>{
        const el=document.getElementById("ob-val");
        if(el){el.focus();el.addEventListener("keydown",e=>{if(e.key==="Enter")onboardingNext();});}
      },100);
      break;

    case "date_of_birth": {
      const months=["January","February","March","April","May","June","July","August","September","October","November","December"];
      const yr=new Date().getFullYear();
      area.innerHTML=`<div class="ob-dob-row">
        <select class="ob-select" id="ob-dob-day">${Array.from({length:31},(_,i)=>`<option value="${i+1}">${i+1}</option>`).join("")}</select>
        <select class="ob-select" id="ob-dob-month">${months.map((m,i)=>`<option value="${i+1}">${m}</option>`).join("")}</select>
        <select class="ob-select" id="ob-dob-year">${Array.from({length:80},(_,i)=>`<option value="${yr-i}">${yr-i}</option>`).join("")}</select>
      </div>
      <div id="ob-age-preview" style="color:var(--purpleLt);font-size:13px;text-align:center;margin-top:6px"></div>`;
      document.getElementById("ob-dob-year").value = yr-25;
      updateAgePreview();
      ["ob-dob-day","ob-dob-month","ob-dob-year"].forEach(id=>document.getElementById(id).onchange=updateAgePreview);
      break;
    }

    case "gender":
      area.innerHTML=`<div class="ob-options">
        <button class="ob-option" onclick="selectObOption(this,'male')">👨 Male</button>
        <button class="ob-option" onclick="selectObOption(this,'female')">👩 Female</button>
      </div>`;
      break;

    case "height":
      area.innerHTML=`<div class="ob-range-wrap">
        <div class="ob-range-label"><span>140 cm</span><span>210 cm</span></div>
        <input type="range" id="ob-val" min="140" max="210" value="170" oninput="document.getElementById('ob-range-val').textContent=this.value+' cm'"/>
        <div class="ob-range-value" id="ob-range-val">170 cm</div></div>`;
      break;

    case "weight":
      area.innerHTML=`<div class="ob-range-wrap">
        <div class="ob-range-label"><span>40 kg</span><span>150 kg</span></div>
        <input type="range" id="ob-val" min="40" max="150" value="70" oninput="document.getElementById('ob-range-val').textContent=this.value+' kg'"/>
        <div class="ob-range-value" id="ob-range-val">70 kg</div></div>`;
      break;

    case "goal": {
      const isFemale = (gender||"").toLowerCase()==="female";
      const goals = isFemale
        ? [["🏋️ Toned Body","toned body"],["🍑 Glute Growth","glute growth"],["✨ Lean Physique","lean physique"],["⏳ Hourglass","hourglass figure"]]
        : [["🔥 Fat Loss","fat loss"],["💪 Muscle Gain","muscle gain"],["🏆 Strength","strength"],["🏃 General Fitness","general fitness"]];
      area.innerHTML=`<div class="ob-options">${goals.map(([l,v])=>`<button class="ob-option" onclick="selectObOption(this,'${v}')">${l}</button>`).join("")}</div>`;
      break;
    }

    case "level":
      area.innerHTML=`<div class="ob-options">
        <button class="ob-option" onclick="selectObOption(this,'beginner')">🌱 Beginner</button>
        <button class="ob-option" onclick="selectObOption(this,'intermediate')">💪 Intermediate</button>
        <button class="ob-option" onclick="selectObOption(this,'advanced')">🔥 Advanced</button>
      </div>`;
      break;

    case "workout_place":
      area.innerHTML=`<div class="ob-options">
        <button class="ob-option" onclick="selectObOption(this,'gym')">🏋️ Gym</button>
        <button class="ob-option" onclick="selectObOption(this,'home')">🏠 Home</button>
      </div>`;
      break;

    case "days_per_week":
      area.innerHTML=`<div class="ob-options">
        <button class="ob-option" onclick="selectObOption(this,'3')">3 days / week</button>
        <button class="ob-option" onclick="selectObOption(this,'4')">4 days / week</button>
        <button class="ob-option" onclick="selectObOption(this,'5')">5 days / week</button>
        <button class="ob-option" onclick="selectObOption(this,'6')">6 days / week</button>
      </div>`;
      break;

    case "injuries":
      area.innerHTML=`<div class="ob-options">
        <button class="ob-option" id="ob-inj-no"  onclick="selectInjury('no')">✅ No injuries</button>
        <button class="ob-option" id="ob-inj-yes" onclick="selectInjury('yes')">⚠️ Yes, I do</button>
      </div>
      <div id="ob-injury-detail" class="hidden" style="margin-top:10px">
        <input class="ob-text-input" id="ob-injury-text" placeholder="Describe briefly (e.g. left knee pain)"/>
      </div>`;
      break;

    case "plays_sport":
      area.innerHTML=`<div class="ob-options">
        <button class="ob-option" onclick="selectObOption(this,'yes')">🏆 Yes, I play a sport</button>
        <button class="ob-option" onclick="selectObOption(this,'no')">🏋️ No, gym only</button>
      </div>`;
      break;
  }
}

function updateAgePreview() {
  const d=parseInt(document.getElementById("ob-dob-day")?.value);
  const m=parseInt(document.getElementById("ob-dob-month")?.value);
  const y=parseInt(document.getElementById("ob-dob-year")?.value);
  if(d&&m&&y){
    const age=Math.floor((Date.now()-new Date(y,m-1,d).getTime())/(365.25*24*3600*1000));
    const el=document.getElementById("ob-age-preview");
    if(el) el.textContent=`Age: ${age} years old`;
  }
}

function selectObOption(btn, value) {
  btn.closest(".ob-options").querySelectorAll(".ob-option").forEach(b=>b.classList.remove("selected"));
  btn.classList.add("selected");
  btn.dataset.value = value;
}

function selectInjury(choice) {
  document.getElementById("ob-inj-no")?.classList.toggle("selected",  choice==="no");
  document.getElementById("ob-inj-yes")?.classList.toggle("selected", choice==="yes");
  document.getElementById("ob-injury-detail")?.classList.toggle("hidden", choice!=="yes");
}

function getObValue(field, areaId) {
  const area = areaId || "ob-input-area";
  switch(field) {
    case "name": return (document.getElementById("ob-val")?.value||"").trim();
    case "date_of_birth": {
      const d=document.getElementById("ob-dob-day")?.value;
      const m=document.getElementById("ob-dob-month")?.value;
      const y=document.getElementById("ob-dob-year")?.value;
      if(!d||!m||!y) return "";
      return `${y}-${String(m).padStart(2,"0")}-${String(d).padStart(2,"0")}`;
    }
    case "height": case "weight": return document.getElementById("ob-val")?.value||"";
    case "injuries": {
      const no  = document.getElementById("ob-inj-no")?.classList.contains("selected");
      const yes = document.getElementById("ob-inj-yes")?.classList.contains("selected");
      if(no)  return "none";
      if(yes) return (document.getElementById("ob-injury-text")?.value||"").trim()||"unspecified";
      return "";
    }
    default: {
      const sel = document.querySelector(`#${area} .ob-option.selected`);
      return sel?.dataset.value || "";
    }
  }
}

async function onboardingNext() {
  const value = getObValue(onboardingField, "ob-input-area");
  if (!value) {
    const e=document.getElementById("ob-error");
    e.textContent = onboardingField==="name" ? "Please type your name" : "Please make a selection";
    e.classList.remove("hidden"); return;
  }
  document.getElementById("ob-error").classList.add("hidden");
  if (onboardingField==="gender") onboardingGender = value;

  const btn=document.getElementById("ob-next-btn");
  btn.disabled=true; btn.textContent="…";
  try {
    const res=await fetch(`${API}/api/coach/chat`,{
      method:"POST",
      headers:{"Content-Type":"application/json","Authorization":`Bearer ${authToken}`},
      body:JSON.stringify({message:value})
    });
    if(res.status===401){doLogout(false);return;}
    const data=await res.json();
    handleResponse(data);
  } catch {
    document.getElementById("ob-error").textContent="Connection error";
    document.getElementById("ob-error").classList.remove("hidden");
  } finally {
    btn.disabled=false; btn.textContent="Continue →";
  }
}

function hideOnboarding() { document.getElementById("onboarding-overlay").classList.add("hidden"); }

// ── SPORT ONBOARDING ──────────────────────────────────────────────────
let sportObState = {}; // local client-side state tracker

async function startSportOnboarding() {
  sportObState = {profile:{}, currentField:"sport_select", sport:null};
  document.getElementById("sport-onboarding-overlay").classList.remove("hidden");
  renderSportQuestion("sport_select");
}

function renderSportQuestion(field) {
  sportObField     = field;
  sportObInputType = SPORT_QUESTIONS[field]?.input_type || "text";
  const q = SPORT_QUESTIONS[field] || {reply:`Tell me about ${field}`};

  // Progress
  const sport = sportObState.sport;
  const order = SPORT_FIELD_ORDERS[sport] || SPORT_FIELD_ORDERS.default;
  const idx   = order.indexOf(field);
  const total = order.length;
  document.getElementById("sob-progress-fill").style.width = ((Math.max(0,idx)/total)*100)+"%";
  document.getElementById("sob-step-label").textContent = `Step ${idx+1} of ${total}`;
  document.getElementById("sob-question").textContent = q.reply;
  document.getElementById("sob-error").classList.add("hidden");

  renderSportInput(sportObInputType, sport);
}

function renderSportInput(inputType, sport) {
  const area = document.getElementById("sob-input-area");
  area.innerHTML = "";

  switch(inputType) {
    case "sport_select":
      area.innerHTML=`<div class="ob-options">
        <button class="ob-option" onclick="selectSobOption(this,'cricket')">🏏 Cricket</button>
        <button class="ob-option" onclick="selectSobOption(this,'football')">⚽ Football</button>
        <button class="ob-option" onclick="selectSobOption(this,'running')">🏃 Running</button>
      </div>`;
      break;
    case "cricket_role":
      area.innerHTML=`<div class="ob-options">
        <button class="ob-option" onclick="selectSobOption(this,'batsman')">🏏 Batsman</button>
        <button class="ob-option" onclick="selectSobOption(this,'bowler')">⚡ Bowler</button>
        <button class="ob-option" onclick="selectSobOption(this,'all-rounder')">🌟 All-rounder</button>
        <button class="ob-option" onclick="selectSobOption(this,'wicketkeeper')">🧤 Wicketkeeper</button>
      </div>`;
      break;
    case "bowling_type":
      area.innerHTML=`<div class="ob-options">
        <button class="ob-option" onclick="selectSobOption(this,'fast')">⚡ Fast</button>
        <button class="ob-option" onclick="selectSobOption(this,'medium pace')">🎯 Medium pace</button>
        <button class="ob-option" onclick="selectSobOption(this,'spin')">🌀 Spin</button>
      </div>`;
      break;
    case "match_frequency":
      area.innerHTML=`<div class="ob-options">
        <button class="ob-option" onclick="selectSobOption(this,'weekly')">📅 Weekly</button>
        <button class="ob-option" onclick="selectSobOption(this,'fortnightly')">📆 Fortnightly</button>
        <button class="ob-option" onclick="selectSobOption(this,'monthly')">🗓️ Monthly</button>
        <button class="ob-option" onclick="selectSobOption(this,'tournament')">🏆 Tournament season</button>
      </div>`;
      break;
    case "primary_focus":
      area.innerHTML=`<div class="ob-options">
        <button class="ob-option" onclick="selectSobOption(this,'strength')">💪 Strength</button>
        <button class="ob-option" onclick="selectSobOption(this,'speed')">⚡ Speed & Agility</button>
        <button class="ob-option" onclick="selectSobOption(this,'endurance')">🏃 Endurance</button>
        <button class="ob-option" onclick="selectSobOption(this,'injury prevention')">🛡️ Injury Prevention</button>
      </div>`;
      break;
    case "sport_injuries":
      area.innerHTML=`<div class="ob-options">
        <button class="ob-option" onclick="selectSobOption(this,'none')">✅ None</button>
        <button class="ob-option" onclick="selectSobOption(this,'shoulder')">💪 Shoulder</button>
        <button class="ob-option" onclick="selectSobOption(this,'knee')">🦵 Knee</button>
        <button class="ob-option" onclick="selectSobOption(this,'hamstring')">🏃 Hamstring</button>
        <button class="ob-option" onclick="selectSobOption(this,'back')">🔙 Lower back</button>
        <button class="ob-option" onclick="selectSobOption(this,'ankle')">🦶 Ankle</button>
      </div>`;
      break;
    case "football_position":
      area.innerHTML=`<div class="ob-options">
        <button class="ob-option" onclick="selectSobOption(this,'goalkeeper')">🥅 Goalkeeper</button>
        <button class="ob-option" onclick="selectSobOption(this,'defender')">🛡️ Defender</button>
        <button class="ob-option" onclick="selectSobOption(this,'midfielder')">🔄 Midfielder</button>
        <button class="ob-option" onclick="selectSobOption(this,'forward')">⚡ Forward</button>
      </div>`;
      break;
    case "distance_type":
      area.innerHTML=`<div class="ob-options">
        <button class="ob-option" onclick="selectSobOption(this,'sprint')">⚡ Sprint (100m–400m)</button>
        <button class="ob-option" onclick="selectSobOption(this,'5k')">🏃 5K</button>
        <button class="ob-option" onclick="selectSobOption(this,'10k')">🏃 10K</button>
        <button class="ob-option" onclick="selectSobOption(this,'half marathon')">🏅 Half Marathon</button>
        <button class="ob-option" onclick="selectSobOption(this,'marathon')">🎽 Marathon</button>
      </div>`;
      break;
    case "weekly_mileage":
      area.innerHTML=`<div class="ob-options">
        <button class="ob-option" onclick="selectSobOption(this,'less than 20km')">Under 20km</button>
        <button class="ob-option" onclick="selectSobOption(this,'20-40km')">20–40km</button>
        <button class="ob-option" onclick="selectSobOption(this,'40-60km')">40–60km</button>
        <button class="ob-option" onclick="selectSobOption(this,'60km+')">60km+</button>
      </div>`;
      break;
    default:
      area.innerHTML=`<input class="ob-text-input" id="sob-text-val" type="text" placeholder="Your answer…"/>`;
      setTimeout(()=>document.getElementById("sob-text-val")?.focus(),100);
  }
}

function selectSobOption(btn, value) {
  btn.closest(".ob-options").querySelectorAll(".ob-option").forEach(b=>b.classList.remove("selected"));
  btn.classList.add("selected");
  btn.dataset.value = value;
}

function getSobValue() {
  const sel = document.querySelector("#sob-input-area .ob-option.selected");
  if (sel) return sel.dataset.value;
  const txt = document.getElementById("sob-text-val");
  return (txt?.value||"").trim();
}

async function sportOnboardingNext() {
  const value = getSobValue();
  if (!value) {
    const e=document.getElementById("sob-error");
    e.textContent="Please make a selection"; e.classList.remove("hidden"); return;
  }
  document.getElementById("sob-error").classList.add("hidden");

  // Save to local state
  sportObState.profile[sportObField] = value;
  if (sportObField==="sport_select") { sportObState.sport=value; }

  // Skip bowling_type if not bowler/all-rounder
  if (sportObState.sport==="cricket" &&
      sportObField==="role" &&
      !["bowler","all-rounder"].includes(value.toLowerCase())) {
    sportObState.profile["bowling_type"] = "n/a";
  }

  const sport     = sportObState.sport;
  const order     = SPORT_FIELD_ORDERS[sport] || SPORT_FIELD_ORDERS.default;
  const nextField = order.find(f => !(f in sportObState.profile));

  if (!nextField) {
    // Done — send to server
    const btn=document.getElementById("sob-next-btn");
    btn.disabled=true; btn.textContent="Saving…";
    try {
      const res = await fetch(`${API}/api/profile/sport-onboard`,{
        method:"POST",
        headers:{"Content-Type":"application/json","Authorization":`Bearer ${authToken}`},
        body: JSON.stringify({
          sport,
          role: sportObState.profile.role,
          position: sportObState.profile.position,
          focus: sportObState.profile.primary_focus,
          match_frequency: sportObState.profile.match_frequency,
          bowling_type: sportObState.profile.bowling_type,
          injuries: sportObState.profile.sport_injuries,
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail||"Failed");
      hideSportOnboarding();
      currentUser = {...(currentUser||{}), ...data};
      addMessage(`Awesome! Your ${sport} profile is set up. Let's get training! 🏆`,"bot");
      showToast(`🏆 ${sport.charAt(0).toUpperCase()+sport.slice(1)} mode activated!`);
      setWorkoutMode("sport");
      updateProfileSportBadge();
      showQuickActions();
    } catch(err) {
      document.getElementById("sob-error").textContent = err.message||"Error saving. Try again.";
      document.getElementById("sob-error").classList.remove("hidden");
    } finally {
      const btn=document.getElementById("sob-next-btn");
      btn.disabled=false; btn.textContent="Continue →";
    }
    return;
  }

  renderSportQuestion(nextField);
}

// Simplified API endpoint for sport onboarding — batch save
// (matches the new /api/sport-onboard POST endpoint in app.py)

function hideSportOnboarding() { document.getElementById("sport-onboarding-overlay").classList.add("hidden"); }

function startSportOnboardingFromProfile() { startSportOnboarding(); }

function updateProfileSportBadge() {
  const sport = currentUser?.sport;
  const badge = document.getElementById("profile-sport-badge");
  const activateWrap = document.getElementById("activate-sport-wrap");
  if (sport && badge) {
    const icons = {cricket:"🏏",football:"⚽",running:"🏃"};
    badge.textContent = `${icons[sport]||"🏆"} ${sport.charAt(0).toUpperCase()+sport.slice(1)} Mode Active`;
    badge.classList.remove("hidden");
    activateWrap?.classList.add("hidden");
  } else if (activateWrap) {
    badge?.classList.add("hidden");
    activateWrap.classList.remove("hidden");
  }
}

// ── RECOVERY ──────────────────────────────────────────────────────────
function selectRecovery(key, value, optsId) {
  recoveryInputs[key] = value;
  document.getElementById(optsId)?.querySelectorAll(".ob-option").forEach(b=>{
    b.classList.toggle("selected", b.onclick?.toString().includes(`'${value}'`));
  });
  // visually select clicked button
  event.target.closest(".ob-option").classList.add("selected");
  // deselect siblings
  const parent = event.target.closest(".ob-options");
  parent?.querySelectorAll(".ob-option").forEach(b=>{
    if(b!==event.target.closest(".ob-option")) b.classList.remove("selected");
  });
  updateRecoveryCockpitPreview();
}

async function submitRecovery() {
  const r = recoveryInputs;
  if (!r.sleep||!r.squality||!r.fatigue||!r.soreness||!r.load) {
    document.getElementById("recovery-error").classList.remove("hidden"); return;
  }
  document.getElementById("recovery-error").classList.add("hidden");
  const btn=document.getElementById("recovery-submit-btn");
  btn.disabled=true; btn.querySelector("span").textContent="Calculating…";
  try {
    const data = await apiFetch("/api/recovery/",{
      method:"POST",
      body:JSON.stringify({
        sleep_hours:parseFloat(r.sleep),
        sleep_quality:parseInt(r.squality),
        fatigue:parseInt(r.fatigue),
        soreness:parseInt(r.soreness),
        prev_load:parseInt(r.load)
      })
    });
    showRecoveryScore(data);
    loadRecoveryBanner();
    showToast(`📊 Recovery: ${data.score}/100 — ${data.zone.toUpperCase()}`);
    loadProgress();
  } catch { showToast("❌ Failed to save. Try again."); }
  finally { btn.disabled=false; btn.querySelector("span").textContent="Calculate Recovery Score"; }
}

function showRecoveryScore(data) {
  const card=document.getElementById("recovery-score-card");
  card.classList.remove("hidden");
  card.dataset.zone = data.zone || "green";
  card.style.setProperty("--recovery-score", data.score || 0);
  const dot  = document.getElementById("rs-zone-dot");
  const score= document.getElementById("rs-score");
  const lbl  = document.getElementById("rs-label");
  const msg  = document.getElementById("rs-message");
  dot.className   = `rs-zone-dot ${data.zone}`;
  score.className = `rs-score ${data.zone}`;
  score.textContent = data.score;
  lbl.textContent = {green:"🟢 Full Recovery",yellow:"🟡 Moderate",red:"🔴 Low Recovery"}[data.zone]||data.zone;
  msg.textContent = data.message;
  updateRecoveryCockpitScore(data);
}

function updateRecoveryCockpitPreview() {
  const sleepRead = document.getElementById("recovery-sleep-read");
  const trend = document.getElementById("recovery-trend");
  const aiNote = document.getElementById("recovery-ai-note");
  const bodyMap = document.getElementById("recovery-body-map");
  if (!sleepRead || !trend || !aiNote) return;
  const sleep = Number(recoveryInputs.sleep || 0);
  const squality = Number(recoveryInputs.squality || 0);
  const fatigue = Number(recoveryInputs.fatigue || 0);
  const soreness = Number(recoveryInputs.soreness || 0);
  sleepRead.textContent = sleep >= 8 && squality >= 4 ? "Deep" : sleep >= 6 ? "Manageable" : sleep ? "Restricted" : "Pending";
  trend.textContent = fatigue <= 2 && soreness <= 2 && sleep >= 7 ? "Rising" : fatigue >= 4 || soreness >= 4 ? "Suppressed" : "Stabilizing";
  bodyMap?.classList.toggle("fatigue-high", soreness >= 4 || fatigue >= 4);
  bodyMap?.classList.toggle("fatigue-mid", (soreness === 3 || fatigue === 3) && !(soreness >= 4 || fatigue >= 4));
  aiNote.textContent = fatigue >= 4 || soreness >= 4
    ? "Recovery load is elevated. A mobility, zone-2, or technique session will preserve progress without digging a deeper fatigue hole."
    : sleep >= 7 && squality >= 4
      ? "Signals look strong. You can handle a higher-quality session if warm-up readiness matches this check-in."
      : "Readiness is forming. Finish the check-in for a tighter intensity call and recovery recommendation.";
}

function updateRecoveryCockpitScore(data) {
  const score = Number(data?.score || 0);
  const zone = data?.zone || "green";
  const hydration = document.getElementById("recovery-hydration");
  const ns = document.getElementById("recovery-ns");
  const trend = document.getElementById("recovery-trend");
  const aiNote = document.getElementById("recovery-ai-note");
  const bodyMap = document.getElementById("recovery-body-map");
  if (hydration) hydration.textContent = score >= 75 ? "Optimal" : score >= 55 ? "Support" : "Prioritize";
  if (ns) ns.textContent = zone === "green" ? "Primed" : zone === "yellow" ? "Guarded" : "Downshift";
  if (trend) trend.textContent = zone === "green" ? "Rising" : zone === "yellow" ? "Stable" : "Suppressed";
  bodyMap?.classList.toggle("zone-green", zone === "green");
  bodyMap?.classList.toggle("zone-yellow", zone === "yellow");
  bodyMap?.classList.toggle("zone-red", zone === "red");
  if (aiNote) {
    aiNote.textContent = zone === "green"
      ? "Recovery systems are online. Strength, power, or performance work is appropriate if technique feels crisp."
      : zone === "yellow"
        ? "Keep the session productive but controlled. Cap volume, extend warm-up, and avoid chasing max intensity."
        : "Use today to restore. Mobility, breath work, walking, and easy movement will compound better than hard loading.";
  }
}

async function loadRecoveryLatest() {
  try {
    const data = await apiFetch("/api/recovery/latest", { ignore401: true });
    if (data.score) showRecoveryScore(data);
    const readiness = document.getElementById("coach-readiness-value");
    const ring = document.getElementById("coach-readiness-ring");
    const recoveryChip = document.getElementById("coach-recovery-chip");
    const fatigueChip = document.getElementById("coach-fatigue-chip");
    const recoveryStatus = document.getElementById("coach-recovery-status");
    if (readiness) readiness.textContent = data.score;
    if (ring) {
      ring.style.setProperty("--coach-ready", data.score);
      ring.dataset.zone = data.zone;
    }
    if (recoveryChip) recoveryChip.textContent = `Recovery: ${data.zone}`;
    if (fatigueChip) fatigueChip.textContent = data.zone === "green" ? "Fatigue: low" : data.zone === "yellow" ? "Fatigue: moderate" : "Fatigue: high";
    if (recoveryStatus) recoveryStatus.textContent = data.zone === "green" ? "Ready" : data.zone === "yellow" ? "Controlled" : "Restore";
  } catch {}
}

async function loadRecoveryBanner() {
  try {
    const data = await apiFetch("/api/recovery/latest", { ignore401: true });
    if (!data.zone) return;
    const banner = document.getElementById("recovery-banner");
    if (!banner) return; // Gracefully handle missing banner element
    banner.classList.remove("hidden","yellow","red");
    if (data.zone==="yellow") banner.classList.add("yellow");
    if (data.zone==="red")    banner.classList.add("red");
    const icons = {green:"🟢",yellow:"🟡",red:"🔴"};
    const msgs  = {green:"Full recovery — go hard today!",yellow:"Moderate recovery — pace yourself",red:"Low recovery — mobility session today"};
    const iconEl = document.getElementById("recovery-banner-icon");
    const textEl = document.getElementById("recovery-banner-text");
    if (iconEl) iconEl.textContent = icons[data.zone];
    if (textEl) textEl.textContent = `Recovery: ${data.score}/100 — ${msgs[data.zone]}`;
  } catch {}
}

// ── WORKOUT UI ────────────────────────────────────────────────────────
function showWorkoutProgress(data) {
  const bar=document.getElementById("workout-progress-bar");
  bar.classList.remove("hidden");
  document.querySelector(".chat-shell")?.classList.add("workout-live");
  const ei=data.current_exercise_index||0, tot=data.total_exercises||5;
  const sn=data.current_set||1, ts=data.current_exercise?.sets||3;
  document.getElementById("wpb-exercise").textContent=`Exercise ${ei+1}/${tot}`;
  document.getElementById("wpb-set").textContent=`Set ${sn}/${ts}`;
  const pct=((ei/tot)+(sn/(ts*tot)))*100;
  document.getElementById("wpb-fill").style.width=`${Math.min(pct,98)}%`;
}

function exerciseMotionType(exercise) {
  const hay = `${exercise?.name || ""} ${exercise?.muscle || ""} ${exercise?.category || ""}`.toLowerCase();
  if (hay.includes("curl") || hay.includes("bicep")) return "curl";
  if (hay.includes("squat") || hay.includes("lunge") || hay.includes("leg") || hay.includes("glute") || hay.includes("thrust")) return "squat";
  if (hay.includes("push-up") || hay.includes("pushup") || hay.includes("push up") || hay.includes("plank")) return "pushup";
  if (hay.includes("press") || hay.includes("shoulder") || hay.includes("overhead")) return "press";
  if (hay.includes("deadlift") || hay.includes("hinge") || hay.includes("romanian")) return "deadlift";
  if (hay.includes("jack") || hay.includes("high knee") || hay.includes("mountain") || hay.includes("run") || hay.includes("sprint") || hay.includes("shuffle") || hay.includes("agility") || hay.includes("drill")) return "cardio";
  return "squat";
}

function exerciseVizTip(type, exercise) {
  const tips = {
    curl: "Lock the elbow path and control the lowering phase.",
    squat: "Track knees over toes and own the bottom position.",
    pushup: "Keep ribs stacked and press the floor away.",
    press: "Brace the core before every overhead drive.",
    deadlift: "Hinge from the hips and keep the spine long.",
    cardio: "Stay light on the feet and keep rhythm consistent.",
  };
  const progression = Array.isArray(exercise?.progression) ? exercise.progression[0] : "";
  return progression || tips[type] || "Control the movement with clean intent.";
}

function exerciseMuscleTargets(type, exercise) {
  const hay = `${exercise?.name || ""} ${exercise?.muscle || ""}`.toLowerCase();
  if (type === "curl") return ["Biceps", "Forearms"];
  if (type === "press") return ["Shoulders", "Triceps", "Core"];
  if (type === "pushup") return hay.includes("plank") ? ["Core", "Shoulders"] : ["Chest", "Triceps", "Core"];
  if (type === "deadlift") return ["Hamstrings", "Glutes", "Back"];
  if (type === "cardio") return hay.includes("agility") || hay.includes("shuffle") ? ["Calves", "Glutes", "Agility"] : ["Calves", "Hamstrings", "Cardio"];
  return ["Quads", "Glutes", "Hamstrings"];
}

function exerciseMotionCue(type) {
  return {
    curl: "Elbow flexion path",
    squat: "Down / drive up",
    pushup: "Rigid body press",
    press: "Vertical power line",
    deadlift: "Hip hinge pattern",
    cardio: "Fast foot rhythm",
  }[type] || "Controlled motion";
}

function renderExerciseHologram(type, exercise, zone) {
  const muscle = escapeHtml(exercise?.muscle || "primary movers");
  const targets = exerciseMuscleTargets(type, exercise);
  return `
    <div class="holo-stage motion-${type} zone-${escapeHtml(zone || "green")}">
      <div class="holo-particles"><i></i><i></i><i></i><i></i><i></i></div>
      <div class="holo-ring ring-a"></div>
      <div class="holo-ring ring-b"></div>
      <svg class="holo-athlete" viewBox="0 0 220 180" aria-hidden="true">
        <defs>
          <filter id="holoGlow">
            <feGaussianBlur stdDeviation="2.2" result="blur"/>
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
          <linearGradient id="holoLine" x1="0" x2="1">
            <stop offset="0%" stop-color="#60a5fa"/>
            <stop offset="52%" stop-color="#a78bfa"/>
            <stop offset="100%" stop-color="#10b981"/>
          </linearGradient>
        </defs>
        <g class="athlete-body" filter="url(#holoGlow)">
          <circle class="joint head" cx="110" cy="33" r="10"/>
          <line class="bone torso" x1="110" y1="45" x2="110" y2="86"/>
          <g class="arms">
            <line class="bone upper-arm left" x1="110" y1="56" x2="82" y2="76"/>
            <line class="bone forearm left" x1="82" y1="76" x2="70" y2="103"/>
            <circle class="weight left" cx="70" cy="106" r="6"/>
            <line class="bone upper-arm right" x1="110" y1="56" x2="138" y2="76"/>
            <line class="bone forearm right" x1="138" y1="76" x2="150" y2="103"/>
            <circle class="weight right" cx="150" cy="106" r="6"/>
          </g>
          <g class="legs">
            <line class="bone thigh left" x1="110" y1="86" x2="86" y2="122"/>
            <line class="bone shin left" x1="86" y1="122" x2="72" y2="158"/>
            <line class="bone thigh right" x1="110" y1="86" x2="134" y2="122"/>
            <line class="bone shin right" x1="134" y1="122" x2="148" y2="158"/>
          </g>
          <ellipse class="muscle-glow muscle-arms" cx="110" cy="79" rx="54" ry="28"/>
          <ellipse class="muscle-glow muscle-legs" cx="110" cy="129" rx="58" ry="34"/>
          <ellipse class="muscle-glow muscle-core" cx="110" cy="76" rx="24" ry="34"/>
          <circle class="target-dot target-a" cx="82" cy="76" r="5"/>
          <circle class="target-dot target-b" cx="134" cy="122" r="5"/>
          <circle class="target-dot target-c" cx="110" cy="76" r="5"/>
        </g>
        <path class="motion-trail motion-arrow" d="M45 142 C76 102, 145 102, 176 142"/>
        <path class="motion-guide guide-up" d="M184 140 L184 72"/>
        <path class="motion-guide guide-down" d="M36 70 L36 138"/>
        <line class="depth-line" x1="48" y1="144" x2="172" y2="144"/>
      </svg>
      <div class="holo-scan"></div>
      <div class="motion-cue">${escapeHtml(exerciseMotionCue(type))}</div>
      <div class="target-stack">${targets.map((target) => `<span>${escapeHtml(target)}</span>`).join("")}</div>
      <div class="holo-caption"><strong>${muscle}</strong><span>muscle activation</span></div>
    </div>
  `;
}

function showExerciseDemo(exercise, idx, total, zone) {
  if (!exercise) return;
  const card=document.getElementById("exercise-demo-card");
  card.classList.remove("hidden");
  const type = exerciseMotionType(exercise);
  card.dataset.motion = type;
  document.getElementById("demo-name").textContent  = exercise.name;
  document.getElementById("demo-sets").textContent  = `${exercise.sets} sets`;
  document.getElementById("demo-reps").textContent  = exercise.reps+" reps";
  document.getElementById("demo-rest").textContent  = `⏱ ${exercise.rest}`;
  document.getElementById("demo-muscle").textContent= `💪 ${exercise.muscle||""}`;
  document.getElementById("demo-weight").textContent= `🏋️ ${exercise.weight_guide||""}`;
  // Zone badge if provided
  if (zone) {
    const z=document.getElementById("demo-muscle");
    const zIcons={green:"🟢",yellow:"🟡",red:"🔴"};
    z.textContent=`${zIcons[zone]||""} ${exercise.muscle||""}`;
  }
  document.getElementById("demo-rest").textContent = `Rest ${exercise.rest}`;
  document.getElementById("demo-muscle").textContent = zone ? `Recovery ${zone.toUpperCase()}: ${exercise.muscle||"full body"}` : `Targets: ${exercise.muscle||"full body"}`;
  document.getElementById("demo-weight").textContent = `AI tip: ${exerciseVizTip(type, exercise)}`;
  const wrap = card.querySelector(".demo-video-wrap");
  if (wrap) wrap.innerHTML = renderExerciseHologram(type, exercise, zone);
}

function hideWorkoutUI() {
  document.getElementById("workout-progress-bar").classList.add("hidden");
  document.getElementById("exercise-demo-card").classList.add("hidden");
  document.getElementById("rest-timer").classList.add("hidden");
  document.querySelector(".chat-shell")?.classList.remove("workout-live");
  clearInterval(restInterval);
}
function hideQuickActions() { document.getElementById("quick-actions").style.display="none"; }
function showQuickActions() {
  const qa=document.getElementById("quick-actions");
  qa.style.display="flex";
  // Update sport button if sport mode
  const hasSport = currentUser?.plays_sport && currentUser?.sport;
  const existSportBtn = document.getElementById("qa-sport-btn");
  if (hasSport && !existSportBtn) {
    const sport=currentUser.sport;
    const icons={cricket:"🏏",football:"⚽",running:"🏃"};
    const btn=document.createElement("button");
    btn.id="qa-sport-btn"; btn.className="qa-btn qa-sport";
    btn.onclick=()=>{ setWorkoutMode("sport"); startWorkout(); };
    btn.textContent=`${icons[sport]||"🏆"} ${sport.charAt(0).toUpperCase()+sport.slice(1)} Session`;
    qa.insertBefore(btn, qa.children[1]);
  }
}

function showWorkoutButtons() {
  const el=document.getElementById("workout-action-btns");
  el.classList.remove("hidden");
  el.innerHTML=`<button class="wab-btn wab-next" onclick="workoutAction('next')">✅ Next Set</button>
    <button class="wab-btn wab-done" onclick="workoutAction('done')">🏁 End Workout</button>`;
  document.getElementById("feedback-btns").classList.add("hidden");
}
function hideWorkoutButtons() { document.getElementById("workout-action-btns").classList.add("hidden"); }

function showFeedbackButtons() {
  document.getElementById("workout-action-btns").classList.add("hidden");
  const fb=document.getElementById("feedback-btns");
  fb.classList.remove("hidden");
  fb.innerHTML=`<p class="feedback-label">How did that feel?</p>
    <div style="display:flex;gap:10px;justify-content:center">
      <button class="fb-btn fb-easy" onclick="workoutAction('easy')">😄 Easy</button>
      <button class="fb-btn fb-hard" onclick="workoutAction('hard')">😤 Hard</button>
    </div>`;
}
function hideFeedbackButtons() { document.getElementById("feedback-btns").classList.add("hidden"); }
function showDoneButton() {
  const el=document.getElementById("workout-action-btns");
  el.classList.remove("hidden");
  el.innerHTML=`<button class="wab-btn wab-next" onclick="workoutAction('done')" style="background:var(--green)">🏁 Log Workout</button>`;
}

// ── REST TIMER ────────────────────────────────────────────────────────
function startRestTimer(restStr) {
  clearInterval(restInterval);
  if (!restStr) return;
  const secs = parseInt(restStr) || 60;
  let rem = secs;
  
  const overlay = document.getElementById("workout-rest-overlay");
  const countdown = document.getElementById("ws-rest-countdown");
  const nextExerciseText = document.getElementById("ws-rest-next-exercise");
  const restBar = document.getElementById("ws-rest-ring-bar");
  
  if (overlay) overlay.classList.remove("hidden");
  if (nextExerciseText && activeWorkoutData) {
    const exercises = activeWorkoutData.exercises || [];
    const nextIdx = (activeWorkoutData.current_exercise_index ?? 0) + 1;
    const nextEx = exercises[nextIdx] || activeWorkoutData.current_exercise;
    if (nextEx) {
      nextExerciseText.textContent = `Next Up: ${nextEx.name}`;
    }
  }
  
  const dashArray = 326.72; // 2 * Math.PI * 52
  
  const updateWSDisplay = (r) => {
    if (countdown) countdown.textContent = `${r}s`;
    if (restBar) {
      const offset = dashArray - (r / secs) * dashArray;
      restBar.style.strokeDashoffset = offset;
    }
  };
  
  updateWSDisplay(rem);
  
  restInterval = setInterval(() => {
    rem--;
    updateWSDisplay(rem);
    if (rem <= 0) {
      clearInterval(restInterval);
      if (overlay) overlay.classList.add("hidden");
      speak("Rest done. Let's go!", currentUser?.gender || onboardingGender);
    }
  }, 1000);
}
function skipRestTimer() {
  clearInterval(restInterval);
  const overlay = document.getElementById("workout-rest-overlay");
  if (overlay) overlay.classList.add("hidden");
}
function skipTimer() { skipRestTimer(); }

// ── VOICE ─────────────────────────────────────────────────────────────
function speak(text,gender) {
  if (!window.speechSynthesis) return;
  speechSynthesis.cancel();
  const utt=new SpeechSynthesisUtterance(text.replace(/[*_`#]/g,""));
  const voices=speechSynthesis.getVoices();
  if ((gender||"").toLowerCase()==="female") {
    const fv=voices.find(v=>v.name.includes("Samantha")||v.name.includes("Victoria")||v.lang==="en-US"&&v.name.toLowerCase().includes("f"));
    if(fv) utt.voice=fv;
  } else {
    const mv=voices.find(v=>v.lang==="en-US");
    if(mv) utt.voice=mv;
  }
  speechSynthesis.speak(utt);
}
function speakResponse(data,gender) {
  if (["workout_start","workout_next_set","workout_next_exercise"].includes(data.type))
    speak(data.reply.split("\n")[0].replace(/[*_]/g,""),gender);
}
function initVoiceInput() {
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){document.getElementById("voice-btn").style.display="none";return;}
  voiceRec=new SR();
  voiceRec.continuous=false; voiceRec.interimResults=false; voiceRec.lang="en-US";
  voiceRec.onresult=(e)=>{
    document.getElementById("message").value=e.results[0][0].transcript;
    stopListening(); setTimeout(()=>sendMessage(),300);
  };
  voiceRec.onend=()=>stopListening();
  voiceRec.onerror=()=>stopListening();
}
function toggleVoice() {
  if(isListening){voiceRec?.stop();stopListening();}
  else{try{voiceRec?.start();isListening=true;document.getElementById("voice-btn").classList.add("listening");document.getElementById("voice-btn").textContent="🔴";}catch{}}
}
function stopListening() {
  isListening=false;
  const btn=document.getElementById("voice-btn");
  btn.classList.remove("listening"); btn.textContent="🎤";
}

// ── CALORIES ──────────────────────────────────────────────────────────
function switchCalTab(tab) {
  document.getElementById("cal-tab-text").classList.toggle("active",tab==="text");
  document.getElementById("cal-tab-photo").classList.toggle("active",tab==="photo");
  document.getElementById("cal-text-section").classList.toggle("hidden",tab!=="text");
  document.getElementById("cal-photo-section").classList.toggle("hidden",tab!=="photo");
}
async function analyzeCalories() {
  const food=document.getElementById("cal-food-input").value.trim();
  if(!food) return showToast("⚠️ Describe what you ate");
  showCalLoading(true);
  try{
    console.log(`[Nutrition API] Analyzing text: ${food.substring(0, 50)}...`);
    const data=await apiFetch("/api/nutrition/analyze",{method:"POST",body:JSON.stringify({food})});
    console.log(`[Nutrition API] Response:`, data);
    showCalResult(_adaptNutritionResult(data));
  }catch(err){
    console.error(`[Nutrition API] Error:`, err);
    const errorMsg = err?.detail || err?.message || "Failed to analyze food. Please try again.";
    showToast(`❌ ${errorMsg}`);
  }
  finally{showCalLoading(false);}
}
function handleFoodPhoto(ev) {
  const file=ev.target.files[0]; if(!file)return;
  const r=new FileReader();
  r.onload=(e)=>{foodPhotoBase64=e.target.result;document.getElementById("food-photo-preview").src=foodPhotoBase64;document.getElementById("photo-preview-wrap").classList.remove("hidden");};
  r.readAsDataURL(file);
}
// ── AI CONFIRMATION FLOW ────────────────────────────────────────────────
let pendingYoloResult = null;
let isHighConfidencePopup = false;
let isSearchModeActive = false;

const YOLO_CONFIDENCE_SCORES = {
  "pizza": 41,
  "idli": 55,
  "chapathi": 65,
  "vada": 68,
  "chicken gravy": 78,
  "tomato": 72,
  "rice": 82,
  "fries": 83,
  "burger": 85,
  "banana": 88,
  "apple": 91,
  "soda": 95
};

const VISUALLY_SIMILAR_FOODS = {
  "pizza": ["Pizza", "Paneer", "Cheese", "Tofu"],
  "idli": ["Idli", "Omelette", "Vada", "Dhokla"],
  "chapathi": ["Chapathi", "Roti", "Paratha", "Tortilla"],
  "vada": ["Vada", "Idli", "Donut", "Falafel"],
  "chicken gravy": ["Chicken Gravy", "Egg Curry", "Paneer Butter Masala", "Mutton Curry"],
  "tomato": ["Tomato", "Apple", "Red Pepper", "Peach"],
  "apple": ["Apple", "Tomato", "Nectarine", "Pear"],
  "banana": ["banana", "Plantain", "Corn", "Mango"],
  "burger": ["burger", "Sandwich", "Slider", "Vada Pav"],
  "rice": ["Rice", "Quinoa", "Couscous", "Poha"],
  "fries": ["Fries", "Potato Wedges", "Sweet Potato Fries", "Chips"],
  "soda": ["Soda", "Water", "Juice", "Energy Drink"]
};

const NUTRITION_SUGGESTIONS = [
  "Paneer",
  "Paneer Butter Masala",
  "Palak Paneer",
  "Cheese Sandwich",
  "Egg Curry",
  "Omelette",
  "Scrambled Eggs",
  "Boiled Eggs",
  "Chicken Salad",
  "Grilled Chicken Breast",
  "Chicken Biryani",
  "Dal Makhani",
  "Yellow Dal",
  "Roti",
  "Chapathi",
  "Tandoori Roti",
  "Brown Rice",
  "White Rice",
  "Greek Yogurt",
  "Oatmeal",
  "Banana",
  "Apple",
  "Orange",
  "Protein Shake",
  "Almonds",
  "Peanut Butter Toast",
  "Avocado Salad",
  "Mixed Vegetables",
  "Idli",
  "Dosa",
  "Masala Dosa",
  "Vada",
  "Samosa",
  "Burger",
  "Pizza",
  "French Fries",
  "Tomato Soup",
  "Green Salad",
  "Fruit Salad",
  "Tofu Stir Fry",
  "Salmon Fillet",
  "Whey Protein",
  "Cottage Cheese",
  "Moong Dal",
  "Kadhai Paneer"
];

let selectedSuggestionIndex = -1;

function getFoodConfidence(foodName) {
  if (!foodName) return 85;
  const foods = foodName.split(",").map(f => f.trim().toLowerCase());
  let minConf = 100;
  let found = false;
  for (const food of foods) {
    if (YOLO_CONFIDENCE_SCORES.hasOwnProperty(food)) {
      minConf = Math.min(minConf, YOLO_CONFIDENCE_SCORES[food]);
      found = true;
    }
  }
  return found ? minConf : 85;
}

function getPossibleFoods(foodName) {
  if (!foodName) return ["Pizza", "Paneer", "Cheese", "Tofu"];
  const key = foodName.trim().toLowerCase().split(",")[0];
  if (VISUALLY_SIMILAR_FOODS.hasOwnProperty(key)) {
    return VISUALLY_SIMILAR_FOODS[key];
  }
  return [foodName, "Paneer", "Cheese", "Tofu"];
}

function getConfidenceClass(score) {
  if (score >= 80) return { text: "conf-green", bg: "bg-green" };
  if (score >= 60) return { text: "conf-yellow", bg: "bg-yellow" };
  return { text: "conf-red", bg: "bg-red" };
}

function ensurePopupHTMLExists() {
  if (document.getElementById("ai-confirm-backdrop")) {
    return;
  }
  console.log("[Nutrition AI Flow] Popup elements missing from static DOM. Injecting dynamically...");
  const backdrop = document.createElement("div");
  backdrop.id = "ai-confirm-backdrop";
  backdrop.className = "ai-confirm-backdrop";
  
  backdrop.innerHTML = `
  <div class="ai-confirm-modal">
    <!-- Close button top-right -->
    <button class="ai-close-modal-btn" onclick="closeAIConfirmPopup()">&times;</button>

    <!-- Header -->
    <div class="ai-confirm-header">
      <div class="ai-confirm-icon-glow">
        <span class="ai-confirm-icon">🤖</span>
      </div>
      <div class="ai-confirm-title-group">
        <h3 class="ai-confirm-title">AI Food Verification</h3>
        <p id="ai-confirm-subtitle-text" class="ai-confirm-subtitle">Please verify the detected food before nutrition analysis.</p>
      </div>
    </div>
    
    <!-- Detection Card -->
    <div class="ai-section-card ai-detection-card">
      <div class="ai-preview-food-info">
        <div class="ai-preview-food-item">
          <span class="ai-preview-label">Detected Food</span>
          <span id="ai-detected-name" class="ai-preview-value-main">Pizza</span>
        </div>
        <div class="ai-preview-confidence-item">
          <span class="ai-preview-label">Confidence</span>
          <span id="ai-confidence-value" class="ai-preview-value-conf conf-red">41%</span>
        </div>
      </div>

      <!-- Confidence Bar -->
      <div class="ai-confidence-bar-container">
        <span id="ai-confidence-indicator" class="ai-conf-dot bg-red"></span>
      </div>

      <div class="ai-confidence-badge-row">
        <span id="ai-confidence-badge-text" class="ai-confidence-status-text"><span class="badge-icon">⚠</span> Low confidence detection</span>
      </div>

      <!-- Low Confidence Warning Card -->
      <div id="ai-low-confidence-warning" class="ai-warning-card hidden">
        <span class="warning-icon">⚠</span>
        <span class="warning-text">Low confidence detection. Please verify before continuing.</span>
      </div>
    </div>

    <!-- Suggested Foods Section -->
    <div class="ai-section-card ai-suggested-foods-card">
      <p id="ai-confirm-question-text" class="ai-confirm-question">Possible foods:</p>
      <div id="ai-possible-foods-wrap" class="ai-possible-foods-pills"></div>
    </div>

    <!-- Search Section -->
    <div class="ai-section-card ai-search-card">
      <div id="ai-search-input-section" class="ai-search-container-premium">
        <div class="search-input-wrapper">
          <span class="search-icon-inside">🔍</span>
          <input type="text" id="ai-food-search-input" placeholder="Search another food..." autocomplete="off" oninput="handleAISearchInput(event)" onkeydown="handleAISearchKeydown(event)"/>
          <button id="ai-clear-search" class="clear-btn hidden" onclick="clearAISearch()">&times;</button>
        </div>
        
        <!-- Autocomplete Dropdown suggestions list -->
        <div id="ai-suggestions-list" class="ai-suggestions-list-premium hidden"></div>
      </div>
    </div>
      
    <!-- Popular Suggestions -->
    <div class="ai-section-card ai-popular-suggestions-card">
      <span class="examples-label">Popular Suggestions</span>
      <div class="examples-tags-grid">
        <button class="example-tag-btn" onclick="selectAIExample('Paneer')">🥛 Paneer</button>
        <button class="example-tag-btn" onclick="selectAIExample('Paneer Butter Masala')">🥘 Paneer Butter Masala</button>
        <button class="example-tag-btn" onclick="selectAIExample('Palak Paneer')">🥬 Palak Paneer</button>
        <button class="example-tag-btn" onclick="selectAIExample('Cheese Sandwich')">🥪 Cheese Sandwich</button>
        <button class="example-tag-btn" onclick="selectAIExample('Egg Curry')">🥚 Egg Curry</button>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="ai-action-buttons-group">
      <button id="ai-confirm-btn" class="ai-action-btn-primary" onclick="handleAIPrimaryAction()">
        <span>✔ Confirm Food</span>
      </button>
      <button id="ai-use-prediction-btn" class="ai-action-btn-secondary" onclick="handleAISecondaryAction()">
        <span>✏ Edit Detection</span>
      </button>
      <button class="ai-action-btn-cancel" onclick="closeAIConfirmPopup()">
        <span>❌ Cancel</span>
      </button>
    </div>

    <!-- Information Card -->
    <div class="ai-confidence-footer-notice">
      <span class="notice-lightbulb">💡</span>
      <p class="notice-footer-text">AI can confuse visually similar foods like paneer, cheese and pizza. Confirming the correct food improves nutrition accuracy.</p>
    </div>
  </div>
  `;
  document.body.appendChild(backdrop);
}

function openAIConfirmPopup(detectedFood, confidenceScore) {
  ensurePopupHTMLExists();

  const backdrop = document.getElementById("ai-confirm-backdrop");
  if (!backdrop) { console.error("Missing element: ai-confirm-backdrop"); return; }
  
  const nameEl = document.getElementById("ai-detected-name");
  if (!nameEl) { console.error("Missing element: ai-detected-name"); return; }
  
  const valEl = document.getElementById("ai-confidence-value");
  if (!valEl) { console.error("Missing element: ai-confidence-value"); return; }
  
  const dotEl = document.getElementById("ai-confidence-indicator");
  if (!dotEl) { console.error("Missing element: ai-confidence-indicator"); return; }
  
  const inputEl = document.getElementById("ai-food-search-input");
  if (!inputEl) { console.error("Missing element: ai-food-search-input"); return; }
  
  const clearEl = document.getElementById("ai-clear-search");
  if (!clearEl) { console.error("Missing element: ai-clear-search"); return; }
  
  const suggestionsEl = document.getElementById("ai-suggestions-list");
  if (!suggestionsEl) { console.error("Missing element: ai-suggestions-list"); return; }
  
  const subtitleEl = document.getElementById("ai-confirm-subtitle-text");
  if (!subtitleEl) { console.error("Missing element: ai-confirm-subtitle-text"); return; }
  
  const questionEl = document.getElementById("ai-confirm-question-text");
  if (!questionEl) { console.error("Missing element: ai-confirm-question-text"); return; }
  
  const possibleFoodsWrap = document.getElementById("ai-possible-foods-wrap");
  if (!possibleFoodsWrap) { console.error("Missing element: ai-possible-foods-wrap"); return; }
  
  const searchWrapEl = document.getElementById("ai-search-input-section");
  if (!searchWrapEl) { console.error("Missing element: ai-search-input-section"); return; }
  
  const primaryBtn = document.getElementById("ai-confirm-btn");
  if (!primaryBtn) { console.error("Missing element: ai-confirm-btn"); return; }
  
  const secondaryBtn = document.getElementById("ai-use-prediction-btn");
  if (!secondaryBtn) { console.error("Missing element: ai-use-prediction-btn"); return; }

  nameEl.textContent = detectedFood;
  valEl.textContent = confidenceScore + "%";
  
  valEl.className = "ai-info-value";
  dotEl.className = "ai-conf-dot";
  const cls = getConfidenceClass(confidenceScore);
  valEl.classList.add(cls.text);
  dotEl.classList.add(cls.bg);
  
  inputEl.value = "";
  clearEl.classList.add("hidden");
  suggestionsEl.classList.add("hidden");

  if (confidenceScore >= 70) {
    isHighConfidencePopup = true;
    isSearchModeActive = false;
    
    subtitleEl.textContent = "We detected:";
    questionEl.textContent = "Is this correct?";
    possibleFoodsWrap.classList.add("hidden");
    possibleFoodsWrap.innerHTML = "";
    searchWrapEl.classList.add("hidden");
    
    primaryBtn.querySelector("span").textContent = "✓ Yes";
    secondaryBtn.querySelector("span").textContent = "✎ Choose another food";
  } else {
    isHighConfidencePopup = false;
    isSearchModeActive = true;
    
    subtitleEl.textContent = `We are only ${confidenceScore}% confident.`;
    questionEl.textContent = "Possible foods:";
    
    const possible = getPossibleFoods(detectedFood);
    possibleFoodsWrap.innerHTML = possible.map(food => `
      <button class="example-pill possible-food-pill" onclick="selectAIExample('${food.replace(/'/g, "\\'")}')">${escapeHtml(food)}</button>
    `).join("");
    possibleFoodsWrap.classList.remove("hidden");
    
    searchWrapEl.classList.remove("hidden");
    
    primaryBtn.querySelector("span").textContent = "Analyze Correct Food";
    secondaryBtn.querySelector("span").textContent = "Use AI Prediction Anyway";
  }

  backdrop.classList.add("active");
  if (!searchWrapEl.classList.contains("hidden")) {
    setTimeout(() => {
      inputEl.focus();
    }, 100);
  }
}

function enablePopupSearchMode() {
  isSearchModeActive = true;
  
  const searchWrapEl = document.getElementById("ai-search-input-section");
  if (searchWrapEl) searchWrapEl.classList.remove("hidden");
  
  const questionEl = document.getElementById("ai-confirm-question-text");
  if (questionEl) questionEl.textContent = "Please choose or search.";
  
  const nameEl = document.getElementById("ai-detected-name");
  const detectedFood = nameEl ? nameEl.textContent : "Pizza";
  
  const possibleFoodsWrap = document.getElementById("ai-possible-foods-wrap");
  if (possibleFoodsWrap) {
    const possible = getPossibleFoods(detectedFood);
    possibleFoodsWrap.innerHTML = possible.map(food => `
      <button class="example-pill possible-food-pill" onclick="selectAIExample('${food.replace(/'/g, "\\'")}')">${escapeHtml(food)}</button>
    `).join("");
    possibleFoodsWrap.classList.remove("hidden");
  }
  
  const primaryBtn = document.getElementById("ai-confirm-btn");
  if (primaryBtn) {
    primaryBtn.querySelector("span").textContent = "Analyze Correct Food";
  }
  
  const secondaryBtn = document.getElementById("ai-use-prediction-btn");
  if (secondaryBtn) {
    secondaryBtn.querySelector("span").textContent = "Use AI Prediction Anyway";
  }
  
  const inputEl = document.getElementById("ai-food-search-input");
  if (inputEl) {
    inputEl.focus();
  }
}

function handleAIPrimaryAction() {
  if (isHighConfidencePopup && !isSearchModeActive) {
    useAIPredictionAnyway();
  } else {
    analyzeCorrectFood();
  }
}

function handleAISecondaryAction() {
  if (isHighConfidencePopup && !isSearchModeActive) {
    enablePopupSearchMode();
  } else {
    useAIPredictionAnyway();
  }
}

function closeAIConfirmPopup() {
  const backdrop = document.getElementById("ai-confirm-backdrop");
  if (backdrop) backdrop.classList.remove("active");
}

function handleAISearchInput(event) {
  const query = event.target.value.trim().toLowerCase();
  const clearBtn = document.getElementById("ai-clear-search");
  const suggestionsList = document.getElementById("ai-suggestions-list");
  
  if (clearBtn) {
    if (query.length > 0) {
      clearBtn.classList.remove("hidden");
    } else {
      clearBtn.classList.add("hidden");
    }
  }
  
  if (!suggestionsList) return;
  
  if (query.length < 1) {
    suggestionsList.classList.add("hidden");
    suggestionsList.innerHTML = "";
    selectedSuggestionIndex = -1;
    return;
  }
  
  const matches = NUTRITION_SUGGESTIONS.filter(item => 
    item.toLowerCase().includes(query)
  ).slice(0, 5);
  
  if (matches.length > 0) {
    suggestionsList.innerHTML = matches.map((item, idx) => `
      <button class="ai-suggestion-item" onclick="selectAISuggestion('${item.replace(/'/g, "\\'")}')" data-index="${idx}">
        ${escapeHtml(item)}
      </button>
    `).join("");
    suggestionsList.classList.remove("hidden");
    selectedSuggestionIndex = -1;
  } else {
    suggestionsList.classList.add("hidden");
    suggestionsList.innerHTML = "";
    selectedSuggestionIndex = -1;
  }
}

function handleAISearchKeydown(event) {
  const suggestionsList = document.getElementById("ai-suggestions-list");
  if (!suggestionsList || suggestionsList.classList.contains("hidden")) return;
  
  const items = suggestionsList.querySelectorAll(".ai-suggestion-item");
  if (items.length === 0) return;
  
  if (event.key === "ArrowDown") {
    event.preventDefault();
    selectedSuggestionIndex = (selectedSuggestionIndex + 1) % items.length;
    updateSuggestionSelection(items);
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    selectedSuggestionIndex = (selectedSuggestionIndex - 1 + items.length) % items.length;
    updateSuggestionSelection(items);
  } else if (event.key === "Enter") {
    event.preventDefault();
    if (selectedSuggestionIndex >= 0 && selectedSuggestionIndex < items.length) {
      items[selectedSuggestionIndex].click();
    } else {
      analyzeCorrectFood();
    }
  } else if (event.key === "Escape") {
    suggestionsList.classList.add("hidden");
  }
}

function updateSuggestionSelection(items) {
  items.forEach((item, idx) => {
    if (idx === selectedSuggestionIndex) {
      item.classList.add("selected");
      item.scrollIntoView({ block: "nearest" });
    } else {
      item.classList.remove("selected");
    }
  });
}

function selectAISuggestion(food) {
  const input = document.getElementById("ai-food-search-input");
  if (input) {
    input.value = food;
    input.focus();
  }
  const clearEl = document.getElementById("ai-clear-search");
  if (clearEl) clearEl.classList.remove("hidden");
  const suggestionsList = document.getElementById("ai-suggestions-list");
  if (suggestionsList) suggestionsList.classList.add("hidden");
  selectedSuggestionIndex = -1;
}

function selectAIExample(food) {
  const input = document.getElementById("ai-food-search-input");
  if (input) {
    input.value = food;
    input.focus();
  }
  const clearEl = document.getElementById("ai-clear-search");
  if (clearEl) clearEl.classList.remove("hidden");
  const suggestionsList = document.getElementById("ai-suggestions-list");
  if (suggestionsList) suggestionsList.classList.add("hidden");
  selectedSuggestionIndex = -1;
}

function clearAISearch() {
  const input = document.getElementById("ai-food-search-input");
  if (input) {
    input.value = "";
    input.focus();
  }
  const clearEl = document.getElementById("ai-clear-search");
  if (clearEl) clearEl.classList.add("hidden");
  const suggestionsList = document.getElementById("ai-suggestions-list");
  if (suggestionsList) suggestionsList.classList.add("hidden");
  selectedSuggestionIndex = -1;
}

document.addEventListener("click", (e) => {
  const suggestionsList = document.getElementById("ai-suggestions-list");
  const searchInput = document.getElementById("ai-food-search-input");
  if (suggestionsList && !suggestionsList.contains(e.target) && e.target !== searchInput) {
    suggestionsList.classList.add("hidden");
  }
});

async function analyzeCorrectFood() {
  const inputEl = document.getElementById("ai-food-search-input");
  const correctedFood = inputEl ? inputEl.value.trim() : "";
  if (!correctedFood) {
    return showToast("⚠️ Please type or select a food description first");
  }
  
  closeAIConfirmPopup();
  showCalLoading(true);
  
  try {
    console.log(`[Nutrition AI Confirmation] Analyzing correct food: ${correctedFood}`);
    const data = await apiFetch("/api/nutrition/analyze", {
      method: "POST",
      body: JSON.stringify({ food: correctedFood })
    });
    console.log(`[Nutrition AI Confirmation] Response:`, data);
    showCalResult(_adaptNutritionResult(data));
  } catch (err) {
    console.error(`[Nutrition AI Confirmation] Error:`, err);
    const errorMsg = err?.detail || err?.message || "Failed to analyze food description. Please try again.";
    showToast(`❌ ${errorMsg}`);
  } finally {
    showCalLoading(false);
  }
}

function useAIPredictionAnyway() {
  if (!pendingYoloResult) return;
  closeAIConfirmPopup();
  showCalResult(_adaptNutritionResult(pendingYoloResult));
  pendingYoloResult = null;
}

async function analyzePhotoCalories() {
  if(!foodPhotoBase64)return showToast("⚠️ Upload a photo first");
  showCalLoading(true);
  try{
    const imageBase64 = foodPhotoBase64.split(",").pop();
    console.log(`[Nutrition API] Analyzing photo...`);
    console.log(`[Nutrition API] Image base64 length: ${imageBase64.length} chars`);
    console.log(`[Nutrition API] Sending request to /api/nutrition/analyze`);
    const data=await apiFetch("/api/nutrition/analyze",{method:"POST",body:JSON.stringify({image_base64:imageBase64})});
    console.log(`[Nutrition API] Response:`, data);
    
    const detectedFood = data.meal_name || "";
    const score = getFoodConfidence(detectedFood);
    console.log(`[Nutrition AI Confirmation] Detected food: "${detectedFood}", confidence: ${score}%`);
    
    pendingYoloResult = data;
    openAIConfirmPopup(detectedFood, score);
  }catch(err){
    console.error(`[Nutrition API] Error:`, err);
    const errorMsg = err?.detail || err?.message || "Failed to analyze food image. Please try with a clearer image.";
    showToast(`❌ ${errorMsg}`);
  }
  finally{showCalLoading(false);}
}
function showCalLoading(show){
  document.getElementById("cal-loading").classList.toggle("hidden",!show);
  if(show)document.getElementById("cal-result").classList.add("hidden");
}
function calPct(value,target){
  const n=Number(value)||0;
  const t=Number(target)||1;
  return Math.max(4,Math.min(100,Math.round((n/t)*100)));
}
function calBoolBadge(label,active){
  return `<div class="food-badge ${active?"active":"muted"}">${active?"OK":"--"} ${escapeHtml(label)}</div>`;
}
function macroRing(label,value,target,unit,cls){
  const pct=calPct(value,target);
  return `
    <div class="nutri-ring-card ${cls || ""}">
      <div class="nutri-ring" style="--pct:${pct}">
        <span>${escapeHtml(String(value))}</span>
      </div>
      <div>
        <strong>${escapeHtml(label)}</strong>
        <small>${escapeHtml(unit)} / target ${escapeHtml(String(target))}</small>
      </div>
    </div>`;
}
function nutrientBar(label,value,target,unit){
  const pct=calPct(value,target);
  return `
    <div class="nutrient-row">
      <div class="nutrient-row-top"><span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}${escapeHtml(unit)}</strong></div>
      <div class="nutrient-track"><i style="width:${pct}%"></i></div>
    </div>`;
}
function _adaptNutritionResult(raw){
  // Backend returns: meal_name, foods, total_calories, total_protein, total_carbs, total_fat, health_score, tips
  // — adapt it into the richer shape showCalResult renders.
  if (!raw || typeof raw !== "object") return raw;
  
  const foods = raw.foods || [];
  const healthScore = raw.health_score || 0;
  
  const items = foods.map(food => ({
    name: food.name,
    portion: food.quantity || "Estimated",
    calories: food.calories || 0
  }));
  
  const detectedFoodName = raw.meal_name || (foods.length > 0 
    ? foods.map(f => f.name).join(", ")
    : "Detected Meal");

  const totalFiber = foods.reduce(
    (sum, food) => sum + Number(food.fiber || 0),
    0
  );

  const totalSugar = foods.reduce(
    (sum, food) => sum + Number(food.sugar || 0),
    0
  );

  const mealQuality = healthScore >= 85
    ? "Excellent"
    : healthScore >= 70
    ? "Good"
    : "Average";

  return {
    macros: {
      calories: raw.total_calories || 0,
      protein: raw.total_protein || 0,
      carbs: raw.total_carbs || 0,
      fats: raw.total_fat || 0,
      fiber: totalFiber,
      sugar: totalSugar
    },

    meal_quality: mealQuality,

    recommendation: {
      advice: raw.tips ? raw.tips.join(". ") : "",
      best_timing: "Works well as a main meal or post-workout refuel.",
      summary: `Health Score: ${healthScore}/100`,
      timing: "Works well as a main meal or post-workout refuel."
    },

    detected_food: detectedFoodName,
    confidence: healthScore,

    items: items,

    health_score: healthScore,
    health_summary: `Health Score: ${healthScore}/100`,

    category: foods.length > 1 ? "Multi-food meal" : "Single food",

    portion_size:
      foods.length > 0
        ? `${foods.length} item(s)`
        : "Estimated portion",

    calorie_density:
      raw.total_calories > 500
        ? "High"
        : raw.total_calories > 300
        ? "Medium"
        : "Low",

    classification: {
      fat_loss_friendly:
        raw.total_protein > 20 &&
        raw.total_calories < 400,

      muscle_gain_friendly:
        raw.total_protein > 25,

      lean_physique_friendly:
        raw.total_protein > 20 &&
        raw.total_fat < 15,

      recovery_food:
        raw.total_protein > 15,

      endurance_friendly:
        raw.total_carbs > 40,

      high_protein:
        raw.total_protein > 25
    }
  };
}
function showCalResult(result){
  const r=document.getElementById("cal-result");
  r.classList.remove("hidden");
  if(!result || typeof result==="string"){
    const text=String(result || "");
    document.getElementById("cal-result-body").innerHTML=text
      .replace(/\*\*(.*?)\*\*/g,"<strong>$1</strong>")
      .replace(/\*(.*?)\*/g,"<strong>$1</strong>")
      .replace(/\n/g,"<br>");
    return;
  }
  const m=result.macros || {};
  const t=result.macro_targets || {calories:600,protein:35,carbs:60,fats:22};
  const c=result.classification || {};
  const rec=result.recommendation || {};
  const score=Number(result.health_score || result.ai_food_score || 70);
  const items=(result.items || []).slice(0,6).map(item=>`
    <div class="detected-item">
      <span>${escapeHtml(item.name || "Food item")}</span>
      <small>${escapeHtml(item.portion || "Estimated")} — ${escapeHtml(String(item.calories || 0))} kcal</small>
    </div>`).join("");
  
  const detectedFoodsSection = items ? `
    <section class="nutrition-widget">
      <div class="widget-title">Detected Foods</div>
      <div class="detected-foods-list">${items}</div>
    </section>
  ` : "";
  
  document.getElementById("cal-result-body").innerHTML=`
    <div class="nutrition-os">
      <section class="food-preview-card">
        <div class="scanner-frame">
          ${foodPhotoBase64 ? `<img src="${foodPhotoBase64}" alt="Food scan preview"/>` : `<div class="scanner-placeholder">AI</div>`}
          <span class="scan-line"></span>
        </div>
        <div class="food-preview-copy">
          <div class="eyebrow">Visual Nutrition Intelligence</div>
          <h3>${escapeHtml(result.detected_food || "Estimated Meal")}</h3>
          <div class="food-meta-row">
            <span>${escapeHtml(result.category || "Meal")}</span>
            <span>${escapeHtml(String(result.confidence || 78))}% confidence</span>
            <span>${escapeHtml(result.portion_size || "Estimated portion")}</span>
          </div>
          <div class="food-score-line">
            <div class="score-orb" style="--score:${score}"><strong>${score}</strong><span>AI score</span></div>
            <div>
              <strong>${escapeHtml(result.meal_quality || "Good")} meal quality</strong>
              <small>${escapeHtml(result.calorie_density || "Medium")} calorie density</small>
            </div>
          </div>
        </div>
      </section>

      <section class="macro-ring-grid">
        ${macroRing("Calories",m.calories || 0,t.calories || 600,"kcal","energy")}
        ${macroRing("Protein",m.protein || 0,t.protein || 35,"g","protein")}
        ${macroRing("Carbs",m.carbs || 0,t.carbs || 60,"g","carbs")}
        ${macroRing("Fats",m.fats || 0,t.fats || 22,"g","fats")}
      </section>

      ${detectedFoodsSection}

      <section class="nutrition-panel-grid">
        <div class="nutrition-widget">
          <div class="widget-title">Nutrient Detail</div>
          ${nutrientBar("Fiber",m.fiber || 0,10,"g")}
          ${nutrientBar("Sugar",m.sugar || 0,25,"g")}
          ${nutrientBar("Protein density",m.protein || 0,40,"g")}
          ${nutrientBar("Calorie load",m.calories || 0,t.calories || 600," kcal")}
        </div>
        <div class="nutrition-widget">
          <div class="widget-title">Goal Classification</div>
          <div class="food-badge-grid">
            ${calBoolBadge("Fat loss friendly",c.fat_loss_friendly)}
            ${calBoolBadge("Muscle gain",c.muscle_gain_friendly)}
            ${calBoolBadge("Lean physique",c.lean_physique_friendly)}
            ${calBoolBadge("Recovery food",c.recovery_food)}
            ${calBoolBadge("Endurance fuel",c.endurance_friendly)}
            ${calBoolBadge("High protein",c.high_protein)}
          </div>
        </div>
      </section>

      <section class="ai-reco-card">
        <div class="widget-title">AI Recommendation</div>
        <p>${escapeHtml(rec.summary || "Portion looks reasonable. Balance it around your training goal.")}</p>
        <div class="reco-grid">
          <div><span>Meal timing</span><strong>${escapeHtml(rec.timing || "Works best around your workout window.")}</strong></div>
          <div><span>Recovery</span><strong>${escapeHtml(rec.recovery || "Add lean protein for stronger recovery.")}</strong></div>
        </div>
      </section>
      <section class="nutrition-widget health-reco-card">
        <div class="widget-title">Health Recommendations</div>
        <div class="health-reco-grid">
          <div><span>Meal quality score</span><strong>${score}/100</strong></div>
          <div><span>Best goal fit</span><strong>${c.muscle_gain_friendly ? "Muscle gain" : c.fat_loss_friendly ? "Fat loss" : c.endurance_friendly ? "Endurance fuel" : "Balanced fitness"}</strong></div>
          <div><span>Next upgrade</span><strong>${(m.fiber || 0) < 5 ? "Add fiber and greens" : (m.protein || 0) < 20 ? "Add lean protein" : "Hydrate and time it well"}</strong></div>
        </div>
      </section>
      <section class="nutrition-widget suggested-meal-card">
        <div class="widget-title">Suggested Next Meal</div>
        <h3>${(m.protein || 0) < 25 ? "High-protein recovery plate" : "Micronutrient support plate"}</h3>
        <p>${(m.protein || 0) < 25 ? "Try chicken, paneer, tofu, eggs, or Greek yogurt with vegetables and a controlled carb portion." : "Your protein base looks solid. Add colorful vegetables, fruit, and water to round out recovery."}</p>
      </section>
      ${items ? `<section class="detected-stack"><div class="widget-title">Detected Items</div>${items}</section>` : ""}
    </div>`;
  document.getElementById("daily-calories-preview").textContent = `${m.calories || 0} kcal`;
  document.getElementById("daily-protein-preview").textContent = `${m.protein || 0}g`;
  document.getElementById("daily-carbs-preview").textContent = `${m.carbs || 0}g`;
  document.getElementById("daily-fats-preview").textContent = `${m.fats || 0}g`;
}

// ── PROGRESS ──────────────────────────────────────────────────────────
let analyticsData = null;

async function loadProgress() {
  try {
    const data = await apiFetch("/api/progress/dashboard");
    analyticsData = data;
    
    const emptyState = document.getElementById("progress-empty-state");
    const dashboardContent = document.getElementById("progress-dashboard-content");
    
    if (data.total_workouts === 0) {
      if (emptyState) emptyState.classList.remove("hidden");
      if (dashboardContent) dashboardContent.classList.add("hidden");
      
      const wtVal = document.getElementById("pm-weight-val");
      if (wtVal) wtVal.textContent = data.current_weight ? `${data.current_weight} kg` : "--";
      return;
    }
    
    if (emptyState) emptyState.classList.add("hidden");
    if (dashboardContent) dashboardContent.classList.remove("hidden");
    
    // 1. Summary Cards
    const streakVal = document.getElementById("pm-streak-val");
    const streakBest = document.getElementById("pm-streak-best");
    const completedVal = document.getElementById("pm-completed-val");
    const durationVal = document.getElementById("pm-duration-val");
    const weightVal = document.getElementById("pm-weight-val");
    
    if (streakVal) streakVal.textContent = data.current_streak;
    if (streakBest) streakBest.textContent = `Best: ${data.best_streak} days`;
    if (completedVal) completedVal.textContent = data.total_workouts;
    if (durationVal) {
      const hrs = Math.round(data.total_duration / 60 * 10) / 10;
      durationVal.textContent = hrs >= 1.0 ? `${hrs}h` : `${data.total_duration}m`;
    }
    if (weightVal) weightVal.textContent = data.current_weight ? `${data.current_weight} kg` : "--";
    
    // 2. Today's Activity Card
    const todayContainer = document.getElementById("pm-today-activity-container");
    if (todayContainer) {
      if (data.today) {
        todayContainer.innerHTML = `
          <div class="today-activity-minimal">
            <div class="tam-header">
              <span class="tam-check">✓ Workout completed</span>
              <strong class="tam-name">${escapeHtml(data.today.name)}</strong>
            </div>
            <div class="tam-meta">
              <span>${data.today.exercises} exercises</span>
              <span>·</span>
              <span>${data.today.duration} min</span>
              <span>·</span>
              <span>${data.today.calories} kcal estimated</span>
            </div>
            <div class="tam-time">
              Started ${data.today.start_time} · Finished ${data.today.end_time}
            </div>
          </div>
        `;
      } else {
        todayContainer.innerHTML = `
          <div class="today-activity-empty">
            No workout completed today.
          </div>
        `;
      }
    }
    
    // 3. Worked Today Muscles
    const chipsContainer = document.getElementById("pm-worked-today-chips");
    if (chipsContainer) {
      if (data.today_muscles && data.today_muscles.length > 0) {
        chipsContainer.innerHTML = data.today_muscles.map(m => `
          <span class="worked-chip">✓ ${escapeHtml(m)}</span>
        `).join("");
      } else {
        chipsContainer.innerHTML = `<span class="worked-chip-empty">No muscles worked today</span>`;
      }
    }
    
    // 4. Last 7 Days Timeline
    const timelineContainer = document.getElementById("pm-weekly-timeline");
    if (timelineContainer) {
      timelineContainer.innerHTML = data.weekly_timeline.map((dayData, idx) => `
        <div class="timeline-day-item ${dayData.completed ? 'completed' : ''}" onclick="showTimelineDetail(${idx})">
          <span class="td-label">${dayData.day}</span>
          <div class="td-circle">${dayData.completed ? '✓' : '—'}</div>
        </div>
      `).join("");
      
      window._weeklyTimelineData = data.weekly_timeline;
    }
    
    // 5. Recent Workouts (last 5)
    const recentContainer = document.getElementById("pm-recent-workouts");
    if (recentContainer) {
      if (data.recent_workouts && data.recent_workouts.length > 0) {
        recentContainer.innerHTML = data.recent_workouts.map(w => `
          <div class="recent-workout-item-minimal">
            <div class="rwi-left">
              <span class="rwi-day">${escapeHtml(w.day)}</span>
              <strong class="rwi-name">${escapeHtml(w.name)}</strong>
            </div>
            <div class="rwi-right">
              <span class="rwi-duration">${w.duration} min</span>
              <span class="rwi-status">Completed</span>
            </div>
          </div>
        `).join("");
      } else {
        recentContainer.innerHTML = `<p class="recent-empty">No workouts completed recently.</p>`;
      }
    }
    
    // 6. Personal Records
    const prDuration = document.getElementById("pm-pr-duration");
    const prStreak = document.getElementById("pm-pr-streak");
    const prMuscle = document.getElementById("pm-pr-muscle");
    const prExercises = document.getElementById("pm-pr-exercises");
    
    if (prDuration) prDuration.textContent = `${data.personal_records.best_duration} min`;
    if (prStreak) prStreak.textContent = `${data.personal_records.longest_streak} days`;
    if (prMuscle) prMuscle.textContent = titleCase(data.personal_records.most_active_muscle);
    if (prExercises) prExercises.textContent = data.personal_records.total_exercises_completed;
    
  } catch (e) {
    console.error("Failed to load progress dashboard:", e);
  }
}

function showTimelineDetail(index) {
  const data = window._weeklyTimelineData?.[index];
  const popup = document.getElementById("pm-timeline-detail-popup");
  
  if (!data || !popup) return;
  
  if (!data.completed) {
    closeTimelinePopup();
    return;
  }
  
  document.getElementById("pm-tdp-name").textContent = data.name;
  document.getElementById("pm-tdp-duration").textContent = `Duration: ${data.duration} min`;
  document.getElementById("pm-tdp-exercises").textContent = `Exercises: ${data.exercises} completed`;
  
  popup.classList.remove("hidden");
}

function closeTimelinePopup() {
  const popup = document.getElementById("pm-timeline-detail-popup");
  if (popup) popup.classList.add("hidden");
}

// ── PROFILE ───────────────────────────────────────────────────────────
async function loadProfile() {
  try{
    const data=await apiFetch("/api/profile/me");
    document.getElementById("pf-name").value   =data.name||"";
    document.getElementById("pf-age").value    =data.age||"";
    document.getElementById("pf-gender").value =data.gender||"male";
    document.getElementById("pf-weight").value =data.weight||"";
    document.getElementById("pf-height").value =data.height||"";
    document.getElementById("pf-goal").value   =data.goal||"fat loss";
    document.getElementById("pf-level").value  =data.level||"beginner";
    document.getElementById("pf-place").value  =data.workout_place||"gym";
    document.getElementById("pf-days").value   =String(data.days_per_week||3);
    document.getElementById("pf-injuries").value=data.injuries||"";
    document.getElementById("profile-name-display").textContent=data.name||"Champion";
    document.getElementById("profile-goal-display").textContent=data.goal||"Fitness";
    document.getElementById("profile-avatar-display").textContent=data.gender?.toLowerCase()==="female"?"🏃‍♀️":"🏋️";
    currentUser=data;
    updateProfileCockpit(data);
    updateProfileSportBadge();
  }catch{}
}
function updateProfileCockpit(data) {
  const fields = ["name","age","gender","weight","height","goal","level","workout_place","days_per_week"];
  const complete = Math.round(fields.filter(k => data?.[k] !== undefined && data?.[k] !== null && data?.[k] !== "").length / fields.length * 100);
  const ring = document.getElementById("profile-completion-ring");
  const completeValue = document.getElementById("profile-completion-value");
  ring?.style.setProperty("--profile-complete", complete);
  if (completeValue) completeValue.textContent = `${complete}%`;
  const heightM = Number(data?.height || 0) / 100;
  const weight = Number(data?.weight || 0);
  const bmi = heightM && weight ? (weight / (heightM * heightM)).toFixed(1) : "--";
  const bmiEl = document.getElementById("profile-bmi");
  if (bmiEl) bmiEl.textContent = bmi;
  const days = Number(data?.days_per_week || 3);
  const daysEl = document.getElementById("profile-training-days");
  if (daysEl) daysEl.textContent = days;
  const goal = (data?.goal || "Fitness").toString();
  const level = (data?.level || "beginner").toString();
  const protocol = goal.includes("muscle") ? "Hypertrophy" : goal.includes("fat") ? "Cut Protocol" : goal.includes("strength") ? "Strength" : "Hybrid";
  const rank = level === "advanced" ? "Elite" : level === "intermediate" ? "Prime" : "Build";
  const protocolEl = document.getElementById("profile-protocol");
  const rankEl = document.getElementById("profile-rank");
  const readyEl = document.getElementById("profile-readiness");
  const consistency = document.getElementById("profile-consistency-bar");
  if (protocolEl) protocolEl.textContent = protocol;
  if (rankEl) rankEl.textContent = rank;
  if (readyEl) readyEl.textContent = days >= 5 ? "Green" : "Stable";
  consistency?.style.setProperty("--w", `${Math.min(94, 34 + days * 10)}%`);
  const insight = document.getElementById("profile-ai-insight");
  if (insight) {
    insight.textContent = `${rank} ${protocol.toLowerCase()} profile detected. Keep ${days} focused sessions per week and update recovery often so FitCoach can tune intensity around your ${goal.toLowerCase()} goal.`;
  }
}
async function saveProfile() {
  const body={
    name:document.getElementById("pf-name").value,
    age:parseInt(document.getElementById("pf-age").value),
    gender:document.getElementById("pf-gender").value,
    weight:parseFloat(document.getElementById("pf-weight").value),
    height:parseFloat(document.getElementById("pf-height").value),
    goal:document.getElementById("pf-goal").value,
    level:document.getElementById("pf-level").value,
    workout_place:document.getElementById("pf-place").value,
    days_per_week:parseInt(document.getElementById("pf-days").value),
    injuries:document.getElementById("pf-injuries").value
  };
  try{
    await apiFetch("/api/profile/me",{method:"PUT",body:JSON.stringify(body)});
    currentUser={...(currentUser||{}),...body};
    showToast("✅ Profile saved!");
    document.getElementById("profile-name-display").textContent=body.name;
    document.getElementById("profile-goal-display").textContent=body.goal;
    updateProfileCockpit(currentUser);
    document.getElementById("profile-avatar-display").textContent=body.gender==="female"?"🏃‍♀️":"🏋️";
    loadProgress();
  }catch{showToast("❌ Save failed.");}
}

// ── UI HELPERS ────────────────────────────────────────────────────────
function updateStreak(s){
  document.getElementById("streak-badge").textContent = s;
  document.getElementById("chip-streak").querySelector(".chip-value").textContent = s;
}
function updateCoachHeader(name,gender){
  if(name) document.getElementById("coach-name").textContent=`Coach for ${name}`;
  if(gender?.toLowerCase()==="female") document.getElementById("coach-avatar").textContent="💃";
}
function updateWorkoutStatus(status){
  const chip = document.getElementById("coach-workout-status");
  if(chip) chip.textContent = status;
}
function updateReadiness(value){
  const el = document.getElementById("coach-readiness-value");
  if(el) el.textContent = value;
}
function updateRecoveryStatus(status){
  const chip = document.getElementById("coach-recovery-chip");
  if(chip) chip.textContent = `Recovery: ${status}`;
}
function showToast(msg){
  const t=document.getElementById("toast");
  t.textContent=msg; t.classList.remove("hidden");
  clearTimeout(t._t);
  t._t=setTimeout(()=>t.classList.add("hidden"),3000);
}
function launchConfetti(){
  const o=document.getElementById("confetti-overlay");
  o.classList.remove("hidden"); o.innerHTML="";
  const C=["#7c3aed","#10b981","#f59e0b","#3b82f6","#ef4444","#f472b6"];
  for(let i=0;i<80;i++){
    const p=document.createElement("div");
    p.className="confetti-piece";
    p.style.cssText=`left:${Math.random()*100}%;background:${C[Math.floor(Math.random()*C.length)]};animation-duration:${1.5+Math.random()*2}s;animation-delay:${Math.random()*.5}s;transform:rotate(${Math.random()*360}deg);width:${6+Math.random()*8}px;height:${6+Math.random()*8}px;border-radius:${Math.random()>.5?"50%":"2px"}`;
    o.appendChild(p);
  }
  setTimeout(()=>{o.classList.add("hidden");o.innerHTML="";},3500);
}
document.addEventListener("click",()=>{if(window.speechSynthesis)speechSynthesis.resume();},{once:true});

// ── TWO-MODE WORKOUT STATE MANAGEMENT ─────────────────────────────────
let activeWorkoutData = null;
let finalSummaryReply = null;
let workoutTime = 0;
let workoutTimerInterval = null;
let isWorkoutPaused = false;
let lastExerciseName = null;
let isDrawerOpenState = false;

function transitionToWorkout(data) {
  activeWorkoutData = data;
  
  const chatScreen = document.getElementById("chat-mode-shell");
  const sessionScreen = document.getElementById("workout-session-shell");
  const completeScreen = document.getElementById("workout-complete-screen");
  
  if (chatScreen) chatScreen.classList.add("hidden");
  if (completeScreen) completeScreen.classList.add("hidden");
  
  const isNewSession = sessionScreen && sessionScreen.classList.contains("hidden");
  if (isNewSession) {
    sessionScreen.classList.remove("hidden");
    startWorkoutTimer();
    lastExerciseName = null; // force update
  }
  
  const exercises = data.exercises || (data.current_exercise ? [data.current_exercise] : []);
  const currentIdx = data.current_exercise_index ?? 0;
  const currentSet = data.current_set || 1;
  const active = data.current_exercise || exercises[currentIdx] || exercises[0] || {};
  const total = data.total_exercises || exercises.length || 1;
  
  const updateUI = () => {
    // Populate current exercise card details
    const exerciseNameEl = document.getElementById("ws-exercise-name");
    const exerciseSubtitleEl = document.getElementById("ws-exercise-subtitle");
    const exerciseIconEl = document.getElementById("ws-exercise-icon");
    const instructionsEl = document.getElementById("ws-exercise-instructions");
    
    if (exerciseNameEl) exerciseNameEl.textContent = active.name || "Exercise";
    
    const category = active.muscle || active.category || "Bodyweight";
    if (exerciseSubtitleEl) {
      exerciseSubtitleEl.textContent = `${category} · ${active.sets || 3} Sets · ${active.reps || 10} Reps`;
    }
    
    if (exerciseIconEl) {
      const type = exerciseMotionType(active);
      exerciseIconEl.innerHTML = renderExerciseHologram(type, active, data.zone);
    }
    
    if (instructionsEl) {
      const defaultTips = [
        "Maintain a slow, controlled negative phase (3 seconds).",
        "Focus on the target muscle contraction at peak.",
        "Keep your core braced and maintain neutral posture.",
        "Exhale on exertion, inhale as you lower the weight."
      ];
      if (active.progression && Array.isArray(active.progression)) {
        instructionsEl.innerHTML = active.progression.map(tip => `<li>${escapeHtml(tip)}</li>`).join("");
      } else if (active.weight_guide) {
        instructionsEl.innerHTML = `
          <li>${escapeHtml(active.weight_guide)}</li>
          <li>${defaultTips[1]}</li>
          <li>${defaultTips[2]}</li>
        `;
      } else {
        instructionsEl.innerHTML = defaultTips.map(tip => `<li>${tip}</li>`).join("");
      }
    }
  };

  if (lastExerciseName && lastExerciseName !== active.name) {
    animateExerciseCardUpdate(updateUI);
  } else {
    updateUI();
  }
  lastExerciseName = active.name;

  // Update minimal header progress
  const headerTitleEl = document.getElementById("ws-header-title");
  const headerProgressEl = document.getElementById("ws-header-progress");
  const muscleTitle = data.muscle_group || data.today_muscle || "AI Workout Plan";
  if (headerTitleEl) headerTitleEl.textContent = titleCase(muscleTitle);
  if (headerProgressEl) headerProgressEl.textContent = `Exercise ${currentIdx + 1} of ${total}`;

  // Update progress bar
  const pct = Math.min(100, Math.round(((currentIdx + (currentSet - 1) / Math.max(active.sets || 3, 1)) / total) * 100));
  const fillEl = document.getElementById("ws-progress-fill-minimal");
  const progressLabelEl = document.getElementById("ws-progress-text-label");
  if (fillEl) fillEl.style.width = `${pct}%`;
  if (progressLabelEl) progressLabelEl.textContent = `Exercise ${currentIdx + 1} / ${total} (${pct}% Completed)`;

  // Update Right Sidebar Overview
  const overviewTitleEl = document.getElementById("ws-overview-title");
  const overviewCountEl = document.getElementById("ws-overview-count");
  const overviewDurationEl = document.getElementById("ws-overview-duration");
  const overviewDifficultyEl = document.getElementById("ws-overview-difficulty");
  const overviewReadinessEl = document.getElementById("ws-overview-readiness");

  if (overviewTitleEl) overviewTitleEl.textContent = titleCase(muscleTitle);
  if (overviewCountEl) overviewCountEl.textContent = `${total} Exercises`;
  if (overviewDurationEl) overviewDurationEl.textContent = `~${total * 8 + 8} min`;
  if (overviewDifficultyEl) overviewDifficultyEl.textContent = active.intensity || active.difficulty || "Guided";
  if (overviewReadinessEl) {
    overviewReadinessEl.textContent = (data.zone || "green").toUpperCase();
    overviewReadinessEl.className = `badge readiness ${data.zone || "green"}`;
  }

  // Update Exercise Queue list
  const queueContainer = document.getElementById("ws-exercise-queue");
  if (queueContainer) {
    queueContainer.innerHTML = exercises.map((ex, idx) => {
      const isCurrent = idx === currentIdx;
      const isCompleted = idx < currentIdx;
      let statusClass = "";
      let icon = `${idx + 1}`;
      if (isCurrent) {
        statusClass = "active";
        icon = "▶";
      } else if (isCompleted) {
        statusClass = "complete";
        icon = "✓";
      }
      return `
        <div class="ws-queue-item ${statusClass}">
          <div class="ws-queue-icon">${icon}</div>
          <div class="ws-queue-details">
            <span>${escapeHtml(ex.name)}</span>
            <small>${ex.sets} sets x ${ex.reps} reps</small>
          </div>
        </div>
      `;
    }).join("");
  }
  
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function animateExerciseCardUpdate(callback) {
  const card = document.getElementById("workout-focus-card");
  if (!card) {
    callback();
    return;
  }
  card.classList.add("slide-out-animation");
  setTimeout(() => {
    callback();
    card.classList.remove("slide-out-animation");
    card.classList.add("fade-in-animation");
    setTimeout(() => {
      card.classList.remove("fade-in-animation");
    }, 250);
  }, 250);
}

function startWorkoutTimer() {
  clearInterval(workoutTimerInterval);
  workoutTime = 0;
  workoutTimerInterval = setInterval(() => {
    workoutTime++;
    const mins = Math.floor(workoutTime / 60);
    const secs = workoutTime % 60;
    const display = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
    const el = document.getElementById("ws-header-time");
    if (el) el.textContent = display;
  }, 1000);
}

function workoutPause() {
  const btn = document.getElementById("ws-header-pause-btn");
  if (isWorkoutPaused) {
    workoutTimerInterval = setInterval(() => {
      workoutTime++;
      const mins = Math.floor(workoutTime / 60);
      const secs = workoutTime % 60;
      const display = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
      const el = document.getElementById("ws-header-time");
      if (el) el.textContent = display;
    }, 1000);
    isWorkoutPaused = false;
    if (btn) btn.textContent = "⏸ Pause";
  } else {
    clearInterval(workoutTimerInterval);
    isWorkoutPaused = true;
    if (btn) btn.textContent = "▶ Resume";
  }
}

function workoutNext() {
  quickSend("next");
}

function workoutPrev() {
  quickSend("prev");
}

function workoutFinish() {
  quickSend("finish workout");
}

function transitionToComplete(data) {
  clearInterval(workoutTimerInterval);
  
  if (data.type === "workout_logged" && data.reply) {
    finalSummaryReply = data.reply;
  }
  
  const sessionScreen = document.getElementById("workout-session-shell");
  const chatScreen = document.getElementById("chat-mode-shell");
  const completeScreen = document.getElementById("workout-complete-screen");
  
  if (sessionScreen) sessionScreen.classList.add("hidden");
  if (chatScreen) chatScreen.classList.add("hidden");
  if (completeScreen) {
    completeScreen.classList.remove("hidden");
    
    const durationMin = Math.round(workoutTime / 60) || 45;
    const caloriesBurned = Math.round(durationMin * 8.5) || 380;
    const volumeKg = Math.round((activeWorkoutData?.exercises?.length || 5) * 3 * 10 * 20) || 3240;
    const completedCount = activeWorkoutData?.exercises?.length || 6;
    
    const durEl = document.getElementById("wc-duration");
    const calEl = document.getElementById("wc-calories");
    const volEl = document.getElementById("wc-volume");
    const doneEl = document.getElementById("wc-completed");
    const recEl = document.getElementById("wc-recovery");
    const xpEl = document.getElementById("wc-xp");
    
    if (durEl) durEl.textContent = `${durationMin} min`;
    if (calEl) calEl.textContent = `${caloriesBurned} kcal`;
    if (volEl) volEl.textContent = `${volumeKg.toLocaleString()} kg`;
    if (doneEl) doneEl.textContent = completedCount;
    if (recEl) recEl.textContent = `${activeWorkoutData?.zone === "red" ? "68" : activeWorkoutData?.zone === "yellow" ? "82" : "94"}%`;
    if (xpEl) xpEl.textContent = `+${completedCount * 100} XP`;
  }
  
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function returnToCoach() {
  const completeScreen = document.getElementById("workout-complete-screen");
  const sessionScreen = document.getElementById("workout-session-shell");
  const chatScreen = document.getElementById("chat-mode-shell");
  
  if (completeScreen) completeScreen.classList.add("hidden");
  if (sessionScreen) sessionScreen.classList.add("hidden");
  if (chatScreen) {
    chatScreen.classList.remove("hidden");
    
    if (finalSummaryReply) {
      const chatBox = document.getElementById("chat-box");
      if (chatBox) {
        const msg = document.createElement("div");
        msg.className = "message bot";
        msg.innerHTML = cleanDisplayText(finalSummaryReply)
          .replace(/\*\*(.*?)\*\*/g,"<strong>$1</strong>")
          .replace(/_(.*?)_/g,"<em>$1</em>")
          .replace(/\n/g,"<br>");
        chatBox.appendChild(msg);
      }
      finalSummaryReply = null;
    }
  }
  
  scrollToBottom();
}

function toggleCoachDrawer() {
  const drawer = document.getElementById("coach-side-drawer");
  if (!drawer) return;
  isDrawerOpenState = !isDrawerOpenState;
  if (isDrawerOpenState) {
    drawer.classList.remove("hidden");
  } else {
    drawer.classList.add("hidden");
  }
}

function sendDrawerMessage() {
  const input = document.getElementById("drawer-message-input");
  if (!input) return;
  const val = input.value.trim();
  if (!val) return;
  input.value = "";
  
  pushDrawerMessage(val, "user");
  callServer(val);
}

function handleDrawerKey(e) {
  if (e.key === "Enter") sendDrawerMessage();
}

function pushDrawerMessage(text, sender) {
  const container = document.getElementById("drawer-messages");
  if (!container) return;
  
  const msg = document.createElement("div");
  msg.className = `drawer-msg-item ${sender}`;
  msg.innerHTML = cleanDisplayText(text)
    .replace(/\*\*(.*?)\*\*/g,"<strong>$1</strong>")
    .replace(/_(.*?)_/g,"<em>$1</em>")
    .replace(/\n/g,"<br>");
    
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

// Override skipTimer and startRestTimer to hook new screen Rest Overlay
function skipRestTimer() {
  clearInterval(restInterval);
  const overlay = document.getElementById("workout-rest-overlay");
  if (overlay) overlay.classList.add("hidden");
}

const originalStartRestTimer = startRestTimer;
startRestTimer = function(restStr) {
  clearInterval(restInterval);
  if (!restStr) return;
  const secs = parseInt(restStr) || 60;
  let rem = secs;
  
  const overlay = document.getElementById("workout-rest-overlay");
  const countdown = document.getElementById("ws-rest-countdown");
  const nextExerciseText = document.getElementById("ws-rest-next-exercise");
  const restBar = document.getElementById("ws-rest-ring-bar");
  
  if (overlay) overlay.classList.remove("hidden");
  if (nextExerciseText && activeWorkoutData) {
    const exercises = activeWorkoutData.exercises || [];
    const nextIdx = (activeWorkoutData.current_exercise_index ?? 0) + 1;
    const nextEx = exercises[nextIdx] || activeWorkoutData.current_exercise;
    if (nextEx) {
      nextExerciseText.textContent = `Next Up: ${nextEx.name}`;
    }
  }
  
  const dashArray = 326.72; // 2 * Math.PI * 52
  
  const updateWSDisplay = (r) => {
    if (countdown) countdown.textContent = `${r}s`;
    if (restBar) {
      const offset = dashArray - (r / secs) * dashArray;
      restBar.style.strokeDashoffset = offset;
    }
  };
  
  updateWSDisplay(rem);
  
  restInterval = setInterval(() => {
    rem--;
    updateWSDisplay(rem);
    if (rem <= 0) {
      clearInterval(restInterval);
      if (overlay) overlay.classList.add("hidden");
      speak("Rest done. Let's go!", currentUser?.gender || onboardingGender);
    }
  }, 1000);
};

// No-op for removed popover message hooks
function pushPopoverMessage(text, sender = "bot") {
  if (isDrawerOpenState) {
    pushDrawerMessage(text, "bot");
  }
}

// Initialize Lucide icons for home dashboard
function initHomeIcons() {
  if (window.lucide) {
    lucide.createIcons();
  }
}

// Initialize home dashboard on load
document.addEventListener('DOMContentLoaded', () => {
  initHomeIcons();
  // Load home data if home tab is active
  if (document.getElementById('tab-home').classList.contains('active')) {
    loadHomeDashboard();
  }
});


