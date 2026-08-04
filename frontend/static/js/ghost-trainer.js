// Load dependencies from global scope (loaded via script tags)
const { getPoseLandmarker, POSE_EDGES, LM } = window.GhostPose || {};
const { analyze, tick, scoreForm, TARGET_REPS, newRepState } = window.GhostFormAnalysis || {};

// Fallback constants if global exports not available
const LM_FALLBACK = {
  NOSE: 0,
  LEFT_SHOULDER: 11,
  RIGHT_SHOULDER: 12,
  LEFT_ELBOW: 13,
  RIGHT_ELBOW: 14,
  LEFT_WRIST: 15,
  RIGHT_WRIST: 16,
  LEFT_HIP: 23,
  RIGHT_HIP: 24,
  LEFT_KNEE: 25,
  RIGHT_KNEE: 26,
  LEFT_ANKLE: 27,
  RIGHT_ANKLE: 28,
};

const POSE_EDGES_FALLBACK = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [24, 26], [26, 28],
];

// Use actual exports or fallbacks
const LM_ACTUAL = LM || LM_FALLBACK;
const POSE_EDGES_ACTUAL = POSE_EDGES || POSE_EDGES_FALLBACK;
const TARGET_REPS_ACTUAL = TARGET_REPS || 12;
const newRepState_ACTUAL = newRepState || function() {
  return {
    reps: 0,
    phase: "up",
    stateName: "READY",
    pendingState: null,
    pendingStateTime: 0,
    lastRepTime: 0,
    lastAngle: null,
    angleTrend: 0,
    goodFrames: 0,
    totalFrames: 0,
    depthSamples: [],
    angleScores: [],
  };
};

// Exercise library will be loaded from API
let EXERCISE_LIBRARY = {};

// Form key mapping for pose detection - maps exercise names to form analysis keys
// Exercises not in this list are not supported for pose detection
const FORM_KEY_MAPPING = {
  "Bicep Curl": "biceps",
  "Hammer Curl": "biceps",
  "Tricep Pushdown": "pushup",
  "Squat": "squat",
  "Lunges": "squat",
  "Romanian Deadlift": "squat",
  "Push-up": "pushup",
  "Bench Press": "pushup",
  "Incline Press": "pushup",
  "Barbell Row": "biceps",
  "Lat Pulldown": "biceps",
  "Seated Row": "biceps",
  "Plank": "pushup",
  "Crunches": "pushup",
  "Russian Twist": "biceps",
  "Hip Thrust": "squat",
  "Glute Bridge": "squat",
  "Bulgarian Split Squat": "squat",
  "Shoulder Press": "pushup",
  "Lateral Raise": "biceps",
  "Front Raise": "biceps",
  "Burpees": "pushup",
  "Mountain Climbers": "pushup",
  "Thrusters": "squat"
};

// Check if an exercise is supported for pose detection
function isExerciseSupported(exerciseName) {
  return exerciseName in FORM_KEY_MAPPING;
}

// Icon mapping for exercises
const ICON_MAPPING = {
  "arms": "💪",
  "legs": "🦵",
  "chest": "🏋️",
  "back": "🏋️",
  "core": "🧘",
  "glutes": "🍑",
  "shoulders": "🏋️",
  "full_body": "🏃"
};

const CATEGORY_META = {
  arms: { name: "Arms", icon: "💪" },
  legs: { name: "Legs", icon: "🦵" },
  chest: { name: "Chest", icon: "🏋" },
  shoulders: { name: "Shoulders", icon: "🎯" },
  core: { name: "Core", icon: "🔥" },
  glutes: { name: "Glutes", icon: "🍑" },
  back: { name: "Back", icon: "🪽" },
  full_body: { name: "Full Body", icon: "🏃" }
};

const EXERCISE_BRIEFS = {
  squat: "Feet shoulder-width. Hips back, knees tracking, chest tall.",
  pushup: "Hands under shoulders. Lock the core. Keep elbows near 45 degrees from the torso.",
  biceps: "Pin the upper arm and curl without letting the shoulder swing forward.",
};

const SCORE_STATES = [
  { min: 82, key: "good", color: "rgb(16, 185, 129)", glow: "rgba(16, 185, 129, .42)" },
  { min: 62, key: "warn", color: "rgb(245, 158, 11)", glow: "rgba(245, 158, 11, .42)" },
  { min: 0, key: "poor", color: "rgb(239, 68, 68)", glow: "rgba(239, 68, 68, .42)" },
];

const state = {
  initialized: false,
  status: "idle", // "idle", "loading", "running"
  selectedCategory: null,
  selectedExercise: null,
  selectedExercises: [], // Set dynamically to [selectedExercise] on session start
  exercisesLoaded: false, // Track if exercises have been loaded from API
  
  currentExerciseIndex: 0,
  currentSet: 1,
  exercise: "squat",
  targetReps: TARGET_REPS_ACTUAL,
  reps: 0,
  acc: 100,
  displayAcc: 100,
  elapsed: 0,
  feedback: null,
  rafId: null,
  timerId: null,
  lastVideoTime: -1,
  repState: newRepState_ACTUAL(),
  previousAngles: null,
  stabilityScore: 100,
  completedPulse: false,
};

// Fetch exercises from the backend API
async function fetchExercisesFromAPI() {
  try {
    const token = localStorage.getItem('fc_token');
    if (!token) {
      console.error('No auth token found');
      return;
    }

    const response = await fetch(`${window.API || ""}/api/workouts/exercises`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch exercises: ${response.status}`);
    }

    const exercises = await response.json();
    
    // Group exercises by category
    EXERCISE_LIBRARY = {};
    exercises.forEach(ex => {
      if (!EXERCISE_LIBRARY[ex.category]) {
        EXERCISE_LIBRARY[ex.category] = [];
      }
      
      // Map API response to frontend format
      const difficulty = ex.tags && ex.tags.length > 0 ? ex.tags[0] : 'beginner';
      const formKey = FORM_KEY_MAPPING[ex.name] || 'pushup';
      const icon = ICON_MAPPING[ex.category] || '💪';
      
      EXERCISE_LIBRARY[ex.category].push({
        name: ex.name,
        muscle: ex.muscle || 'General',
        reps: parseInt(ex.reps) || 12,
        sets: ex.sets || 3,
        difficulty: difficulty.charAt(0).toUpperCase() + difficulty.slice(1),
        icon: icon,
        form_key: formKey
      });
    });

    state.exercisesLoaded = true;
    console.log('Exercises loaded from API:', Object.keys(EXERCISE_LIBRARY));
    
  } catch (error) {
    console.error('Error fetching exercises:', error);
    // Fallback to empty library - user will see no exercises
    EXERCISE_LIBRARY = {};
  }
}

const els = {};

function cacheEls() {
  els.video = document.getElementById("ghost-video");
  els.canvas = document.getElementById("ghost-canvas");
  els.overlay = document.getElementById("ghost-idle-overlay");
  
  els.reps = document.getElementById("ghost-reps");
  els.targetReps = document.getElementById("ghost-target-reps");
  els.accuracy = document.getElementById("ghost-accuracy");
  els.accuracyLabel = document.getElementById("ghost-accuracy-label");
  els.timer = document.getElementById("ghost-timer");
  els.brief = document.getElementById("ghost-brief");
  els.liveCue = document.getElementById("ghost-live-cue");
  
  els.selectionContainer = document.getElementById("ghost-selection-container");
  els.categoriesGrid = document.getElementById("ghost-categories-grid");
  els.exercisesSelection = document.getElementById("ghost-exercises-selection");
  els.exercisesList = document.getElementById("ghost-exercises-list");
  els.actionBar = document.getElementById("ghost-action-bar");
  
  els.startSessionBtn = document.getElementById("ghost-start-session-btn");
  els.selectedCategoryTitle = document.getElementById("ghost-selected-category-title");
  els.selectionText = document.getElementById("gab-selection-text");
  
  els.workoutContainer = document.getElementById("ghost-workout-container");
  els.workoutProgress = document.getElementById("ghost-workout-progress");
  els.workoutExerciseName = document.getElementById("ghost-workout-exercise-name");
  els.workoutSets = document.getElementById("ghost-workout-sets");
  
  els.nextBtn = document.getElementById("ghost-workout-next-btn");
  els.finishBtn = document.getElementById("ghost-workout-finish-btn");
}

async function init() {
  cacheEls();
  
  // Only check for video/canvas if starting camera session, not for initial UI rendering
  if (state.status === "running" && (!els.video || !els.canvas)) return;
  
  // Always re-render categories when switching to this tab
  if (!state.exercisesLoaded) {
    await fetchExercisesFromAPI();
  }

  // Set up event listeners only once
  if (!state.initialized) {
    // Set up categories clicks
    els.categoriesGrid?.addEventListener("click", (event) => {
      const card = event.target.closest(".category-card");
      if (!card) return;
      
      const category = card.dataset.category;
      
      // Toggle active selected class
      document.querySelectorAll(".category-card").forEach(c => {
        c.classList.toggle("selected", c === card);
      });
      
      state.selectedCategory = category;
      state.selectedExercise = null;
      
      els.exercisesSelection.classList.remove("hidden");
      const meta = CATEGORY_META[category] || { name: category.charAt(0).toUpperCase() + category.slice(1) };
      els.selectedCategoryTitle.textContent = meta.name.toUpperCase();
      
      renderExercisesList();
      updateActionBarStats();
    });

    // Exercise card clicks
    els.exercisesList?.addEventListener("click", (event) => {
      const card = event.target.closest(".exercise-card-item");
      if (!card) return;
      
      // Check if exercise is supported
      const isSupported = card.dataset.supported === "true";
      if (!isSupported) {
        // Show toast but don't select
        if (typeof window.showToast === "function") {
          window.showToast("⚠️ This exercise is coming soon - pose detection not yet available");
        }
        return;
      }
      
      const exName = card.dataset.name;
      const exList = EXERCISE_LIBRARY[state.selectedCategory] || [];
      const exItem = exList.find(item => item.name === exName);
      if (!exItem) return;
      
      // Select exactly one exercise card
      document.querySelectorAll(".exercise-card-item").forEach(c => {
        c.classList.toggle("selected", c === card);
      });
      
      state.selectedExercise = exItem;
      updateActionBarStats();
    });

    // Begin Session Button click
    els.startSessionBtn?.addEventListener("click", startSession);

    // Next & Finish Workout Buttons
    els.nextBtn?.addEventListener("click", nextExercise);
    els.finishBtn?.addEventListener("click", finishWorkout);

    state.initialized = true;
  } else {
    // If already initialized but switching back to idle, reset selection
    if (state.status === "idle") {
      cancelSelection();
    }
  }

  // Render muscle groups categories grid dynamically
  renderCategoriesGrid();
  render();
}

function renderCategoriesGrid() {
  if (!els.categoriesGrid) return;
  els.categoriesGrid.innerHTML = Object.keys(EXERCISE_LIBRARY).map(key => {
    const meta = CATEGORY_META[key] || { name: key.charAt(0).toUpperCase() + key.slice(1), icon: ICON_MAPPING[key] || '💪' };
    const count = EXERCISE_LIBRARY[key].length;
    const isSelected = state.selectedCategory === key;
    return `
      <div class="category-card ${isSelected ? 'selected' : ''}" data-category="${key}">
        <span class="category-icon">${meta.icon}</span>
        <strong class="category-name">${meta.name}</strong>
        <span class="category-count">${count} exercises</span>
      </div>
    `;
  }).join("");
}

function renderExercisesList() {
  if (!els.exercisesList) return;
  const exercises = EXERCISE_LIBRARY[state.selectedCategory] || [];
  
  if (exercises.length === 0) {
    els.exercisesList.innerHTML = '<p style="color: rgba(255,255,255,0.5); grid-column: 1/-1; text-align: center; padding: 20px;">No exercises found for this category.</p>';
    return;
  }
  
  els.exercisesList.innerHTML = exercises.map(ex => {
    const isSelected = state.selectedExercise && state.selectedExercise.name === ex.name;
    const difficulty = ex.difficulty || 'Beginner';
    const reps = ex.reps || 12;
    const muscle = ex.muscle || 'General';
    const isSupported = isExerciseSupported(ex.name);
    const disabledClass = isSupported ? '' : 'disabled';
    const statusBadge = isSupported ? '' : '<span class="eci-coming-soon">Coming Soon</span>';
    
    return `
      <div class="exercise-card-item ${isSelected ? 'selected' : ''} ${disabledClass}" data-name="${ex.name}" data-supported="${isSupported}">
        <div class="eci-header">
          <span class="eci-badge">${difficulty}</span>
          <span class="eci-reps">${reps} reps</span>
          ${statusBadge}
        </div>
        <strong class="eci-name">${ex.name}</strong>
        <span class="eci-muscle">${muscle}</span>
      </div>
    `;
  }).join("");
}

function updateActionBarStats() {
  if (state.selectedCategory) {
    els.actionBar?.classList.remove("hidden");
  } else {
    els.actionBar?.classList.add("hidden");
  }

  if (state.selectedExercise) {
    if (els.selectionText) els.selectionText.textContent = `Selected: ${state.selectedExercise.name}`;
    if (els.startSessionBtn) els.startSessionBtn.disabled = false;
  } else {
    if (els.selectionText) els.selectionText.textContent = "Selected: None";
    if (els.startSessionBtn) els.startSessionBtn.disabled = true;
  }
}

function cancelSelection() {
  state.selectedCategory = null;
  state.selectedExercise = null;
  state.selectedExercises = [];
  
  document.querySelectorAll(".category-card").forEach(c => {
    c.classList.remove("selected");
  });
  
  els.exercisesSelection?.classList.add("hidden");
  els.actionBar?.classList.add("hidden");
}

async function startSession() {
  if (!state.selectedExercise) return;
  
  state.selectedExercises = [state.selectedExercise];
  
  // Build and store workout session object
  const meta = CATEGORY_META[state.selectedCategory] || { name: state.selectedCategory };
  const session = {
    category: meta.name,
    exercises: state.selectedExercises.map(ex => ({ ...ex }))
  };
  localStorage.setItem("fc_ghost_session", JSON.stringify(session));
  
  els.selectionContainer?.classList.add("hidden");
  els.workoutContainer?.classList.remove("hidden");
  
  state.currentExerciseIndex = 0;
  state.currentSet = 1;
  state.elapsed = 0;
  
  loadCurrentWorkoutExercise();
  renderWorkoutQueue();
  await startCamera();
}

function loadCurrentWorkoutExercise() {
  const activeEx = state.selectedExercises[state.currentExerciseIndex];
  if (!activeEx) return;
  
  state.exercise = activeEx.form_key;
  state.targetReps = activeEx.reps;
  state.repState = newRepState_ACTUAL();
  state.reps = 0;
  state.acc = 100;
  state.displayAcc = 100;
  state.feedback = null;
  state.previousAngles = null;
  state.stabilityScore = 100;
  
  if (els.workoutProgress) {
    els.workoutProgress.textContent = `Exercise ${state.currentExerciseIndex + 1} / ${state.selectedExercises.length}`;
  }
  if (els.workoutExerciseName) {
    els.workoutExerciseName.textContent = activeEx.name;
  }
  if (els.workoutSets) {
    els.workoutSets.textContent = `${state.currentSet} of 3`;
  }
  
  if (els.reps) els.reps.textContent = "0";
  if (els.targetReps) els.targetReps.textContent = state.targetReps;
  if (els.accuracy) els.accuracy.textContent = "100%";
  if (els.accuracyLabel) els.accuracyLabel.textContent = "Textbook execution";
  if (els.brief) els.brief.textContent = EXERCISE_BRIEWS_FALLBACK(state.exercise);
  
  renderWorkoutQueue();
}

function renderWorkoutQueue() {
  const queueList = document.getElementById("ghost-queue-list");
  const progressText = document.getElementById("ghost-queue-progress-text");
  if (!queueList || !state.selectedExercises.length) return;
  
  const completedCount = state.currentExerciseIndex;
  if (progressText) {
    progressText.textContent = `${completedCount} / ${state.selectedExercises.length} Completed`;
  }
  
  queueList.innerHTML = state.selectedExercises.map((ex, idx) => {
    let iconClass = "dot";
    let iconText = "●";
    let statusClass = "upcoming";
    
    if (idx < state.currentExerciseIndex) {
      iconClass = "checkmark";
      iconText = "✔";
      statusClass = "completed";
    } else if (idx === state.currentExerciseIndex) {
      iconClass = "active-indicator";
      iconText = "●";
      statusClass = "active";
    }
    
    return `
      <div class="ghost-queue-item ${statusClass}">
        <span class="gqi-icon ${iconClass}">${iconText}</span>
        <span class="gqi-name">${ex.name}</span>
      </div>
    `;
  }).join("");
}

function EXERCISE_BRIEWS_FALLBACK(formKey) {
  return EXERCISE_BRIEFS[formKey] || "Match the reference profile posture.";
}

async function startCamera() {
  setStatus("loading");
  try {
    const landmarker = await getPoseLandmarker();
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 1280, height: 720, facingMode: "user" },
      audio: false,
    });

    els.video.srcObject = stream;
    await new Promise((resolve) => {
      els.video.onloadedmetadata = () => els.video.play().then(resolve);
    });

    els.canvas.width = els.video.videoWidth;
    els.canvas.height = els.video.videoHeight;
    state.lastVideoTime = -1;
    
    setStatus("running");
    startTimer();
    loop(landmarker);
  } catch (err) {
    console.error(err);
    setStatus("error");
  }
}

function stop() {
  if (state.rafId) cancelAnimationFrame(state.rafId);
  state.rafId = null;
  clearInterval(state.timerId);
  state.timerId = null;

  const stream = els.video?.srcObject;
  stream?.getTracks?.().forEach((track) => track.stop());
  if (els.video) els.video.srcObject = null;

  const ctx = els.canvas?.getContext("2d");
  ctx?.clearRect(0, 0, els.canvas.width, els.canvas.height);
  setStatus("idle");
}

function nextExercise() {
  state.currentExerciseIndex += 1;
  state.currentSet = 1;
  
  if (state.currentExerciseIndex < state.selectedExercises.length) {
    loadCurrentWorkoutExercise();
  } else {
    finishWorkout();
  }
}

async function finishWorkout() {
  stop();
  await saveWorkoutSession();
  
  state.selectedCategory = null;
  state.selectedExercise = null;
  state.selectedExercises = [];
  state.currentExerciseIndex = 0;
  state.currentSet = 1;
  
  els.selectionContainer?.classList.remove("hidden");
  els.workoutContainer?.classList.add("hidden");
  els.exercisesSelection?.classList.add("hidden");
  els.actionBar?.classList.add("hidden");
  
  // Reset active categories grid highlighting
  document.querySelectorAll(".category-card").forEach(c => {
    c.classList.remove("selected");
  });
  
  if (typeof window.showToast === "function") {
    window.showToast("🎉 Ghost Workout logged successfully!");
  }
}

async function saveWorkoutSession() {
  if (!state.selectedExercises.length) return;
  
  const elapsedSeconds = state.elapsed;
  const durationMinutes = Math.max(1, Math.round(elapsedSeconds / 60));
  const exerciseNames = state.selectedExercises.map(ex => ex.name).join(", ");
  
  const payload = {
    muscle_group: (state.selectedCategory || "Full Body").toUpperCase(),
    exercises_done: exerciseNames,
    duration: durationMinutes,
    mode: "ghost",
    zone: "green",
    exercises: state.selectedExercises.map(ex => ({
      name: ex.name,
      sets: [
        { reps: ex.reps, weight: 0 }
      ]
    }))
  };

  try {
    if (typeof window.apiFetch === "function") {
      await window.apiFetch("/api/workouts/log", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      if (typeof window.loadProgress === "function") {
        window.loadProgress();
      }
    }  else {
      await fetch(`${window.API || ""}/api/workouts/log`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("fc_token") || ""}`
        },
        body: JSON.stringify(payload)
      });
    }
  } catch (err) {
    console.error("Failed to log ghost workout:", err);
  }
}

function loop(landmarker) {
  if (!els.video || !els.canvas || state.status !== "running") return;
  const ctx = els.canvas.getContext("2d");
  const now = performance.now();

  if (els.video.currentTime !== state.lastVideoTime) {
    state.lastVideoTime = els.video.currentTime;
    const result = landmarker.detectForVideo(els.video, now);

    ctx.save();
    ctx.clearRect(0, 0, els.canvas.width, els.canvas.height);
    ctx.translate(els.canvas.width, 0);
    ctx.scale(-1, 1);

    const landmarks = result.landmarks?.[0] ?? [];
    if (landmarks.length) {
      const feedback = analyze({ landmarks, exercise: state.exercise });
      if (feedback) {
        const next = tick(state.repState, feedback);
        const previousReps = state.repState.reps;
        state.repState = next;
        state.reps = next.reps;
        state.feedback = feedback;
        state.stabilityScore = calculateStability(feedback.angles);
        state.acc = scoreForm({
          state: next,
          feedback,
          stabilityScore: state.stabilityScore,
        });
        
        if (state.reps > previousReps) {
          pulseRepCompletion();
          if (state.reps >= state.targetReps) {
            if (state.currentSet < 3) {
              state.currentSet += 1;
              state.reps = 0;
              state.repState = newRepState_ACTUAL();
              if (els.workoutSets) els.workoutSets.textContent = `${state.currentSet} of 3`;
              if (typeof window.showToast === "function") {
                window.showToast(`💪 Set ${state.currentSet - 1} complete! Prepare for Set ${state.currentSet}.`);
              }
            } else {
              if (typeof window.showToast === "function") {
                window.showToast("🎉 Exercise complete!");
              }
              setTimeout(nextExercise, 1500);
            }
          }
        }
        drawCoachingOverlay(ctx, landmarks, els.canvas.width, els.canvas.height, feedback);
      }
    } else {
      state.feedback = null;
    }
    ctx.restore();
    if (state.feedback) {
      drawAngleLabels(ctx, landmarks, state.feedback.angles, els.canvas.width, els.canvas.height, getScoreState(state.acc));
    }
    render();
  }

  state.rafId = requestAnimationFrame(() => loop(landmarker));
}

function drawCoachingOverlay(ctx, landmarks, width, height, feedback) {
  const scoreState = getScoreState(state.acc);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  drawGhostSkeleton(ctx, landmarks, width, height);
  drawSkeleton(ctx, landmarks, width, height, scoreState);
}

function drawSkeleton(ctx, landmarks, width, height, scoreState) {
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.shadowColor = scoreState.glow;
  ctx.shadowBlur = 22;
  ctx.lineWidth = 9;
  ctx.strokeStyle = scoreState.glow;
  drawEdges(ctx, landmarks, width, height, 4, 4, true);

  ctx.shadowBlur = 12;
  ctx.lineWidth = 4;
  ctx.strokeStyle = scoreState.color;
  drawEdges(ctx, landmarks, width, height, 0, 0, true);

  ctx.fillStyle = scoreState.color;
  ctx.shadowBlur = 16;
  for (let i = 11; i <= 28; i += 1) {
    const point = landmarks[i];
    if (!point) continue;
    ctx.beginPath();
    ctx.arc(point.x * width, point.y * height, 5.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(point.x * width, point.y * height, 10, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(255,255,255,.16)";
    ctx.lineWidth = 1;
    ctx.stroke();
  }
}

function drawEdges(ctx, landmarks, width, height, offsetX, offsetY, animated = false) {
  if (animated) {
    const dashOffset = -(performance.now() / 80) % 22;
    ctx.setLineDash([16, 6]);
    ctx.lineDashOffset = dashOffset;
  }
  for (const [a, b] of POSE_EDGES_ACTUAL) {
    const start = landmarks[a];
    const end = landmarks[b];
    if (!start || !end) continue;
    ctx.beginPath();
    ctx.moveTo(start.x * width + offsetX, start.y * height + offsetY);
    ctx.lineTo(end.x * width + offsetX, end.y * height + offsetY);
    ctx.stroke();
  }
  ctx.setLineDash([]);
}

function drawGhostSkeleton(ctx, landmarks, width, height) {
  const ghost = getIdealGhost(landmarks, width, height, state.exercise);
  if (!ghost.length) return;

  ctx.save();
  ctx.globalAlpha = 0.58;
  ctx.shadowColor = "rgba(167, 139, 250, .55)";
  ctx.shadowBlur = 22;
  ctx.strokeStyle = "rgba(216, 204, 255, .5)";
  ctx.lineWidth = 3;
  ctx.setLineDash([10, 12]);

  for (const [start, end] of ghost) {
    ctx.beginPath();
    ctx.moveTo(start.x, start.y);
    ctx.lineTo(end.x, end.y);
    ctx.stroke();
  }
  ctx.setLineDash([]);
  ctx.fillStyle = "rgba(216, 204, 255, .44)";
  for (const point of ghost.flat()) {
    ctx.beginPath();
    ctx.arc(point.x, point.y, 4, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

function drawAngleLabels(ctx, landmarks, angles, width, height, scoreState) {
  if (!angles) return;
  const labels = angleLabelAnchors(landmarks, angles);
  ctx.save();
  ctx.font = "700 12px DM Sans, sans-serif";
  ctx.textBaseline = "middle";
  ctx.shadowColor = scoreState.glow;
  ctx.shadowBlur = 12;

  for (const label of labels) {
    if (!label.point || !Number.isFinite(label.value)) continue;
    const x = (1 - label.point.x) * width + label.dx;
    const y = label.point.y * height + label.dy;
    const text = `${label.name} ${Math.round(label.value)}°`;
    const metrics = ctx.measureText(text);
    const boxW = metrics.width + 18;
    const boxH = 25;
    roundRect(ctx, x - boxW / 2, y - boxH / 2, boxW, boxH, 12);
    ctx.fillStyle = "rgba(7, 7, 15, .72)";
    ctx.fill();
    ctx.strokeStyle = scoreState.color;
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.fillStyle = scoreState.color;
    ctx.fillText(text, x - metrics.width / 2, y + 1);
  }
  ctx.restore();
}

function angleLabelAnchors(landmarks, angles) {
  return [
    { name: "ELBOW", value: angles.leftElbow, point: landmarks[LM_ACTUAL.LEFT_ELBOW], dx: -38, dy: -22 },
    { name: "ELBOW", value: angles.rightElbow, point: landmarks[LM_ACTUAL.RIGHT_ELBOW], dx: 38, dy: -22 },
    { name: "KNEE", value: angles.leftKnee, point: landmarks[LM_ACTUAL.LEFT_KNEE], dx: -34, dy: 24 },
    { name: "KNEE", value: angles.rightKnee, point: landmarks[LM_ACTUAL.RIGHT_KNEE], dx: 34, dy: 24 },
    { name: "HIP", value: angles.leftHip, point: landmarks[LM_ACTUAL.LEFT_HIP], dx: -34, dy: -24 },
    { name: "HIP", value: angles.rightHip, point: landmarks[LM_ACTUAL.RIGHT_HIP], dx: 34, dy: -24 },
    { name: "SHLD", value: angles.leftShoulder, point: landmarks[LM_ACTUAL.LEFT_SHOULDER], dx: -38, dy: -24 },
    { name: "SHLD", value: angles.rightShoulder, point: landmarks[LM_ACTUAL.RIGHT_SHOULDER], dx: 38, dy: -24 },
  ].filter((label) => Number.isFinite(label.value));
}

function getIdealGhost(landmarks, width, height, exercise) {
  const leftShoulder = landmarks[LM_ACTUAL.LEFT_SHOULDER];
  const rightShoulder = landmarks[LM_ACTUAL.RIGHT_SHOULDER];
  const leftHip = landmarks[LM_ACTUAL.LEFT_HIP];
  const rightHip = landmarks[LM_ACTUAL.RIGHT_HIP];
  if (!leftShoulder || !rightShoulder || !leftHip || !rightHip) return [];

  const centerX = ((leftHip.x + rightHip.x) / 2) * width;
  const hipY = ((leftHip.y + rightHip.y) / 2) * height;
  const shoulderY = ((leftShoulder.y + rightShoulder.y) / 2) * height;
  const body = Math.max(90, Math.abs(hipY - shoulderY));
  const spread = Math.max(60, Math.abs(leftShoulder.x - rightShoulder.x) * width);

  const p = {};
  if (exercise === "squat") {
    p.ls = { x: centerX - spread * .55, y: hipY - body * 1.15 };
    p.rs = { x: centerX + spread * .55, y: hipY - body * 1.15 };
    p.lh = { x: centerX - spread * .42, y: hipY };
    p.rh = { x: centerX + spread * .42, y: hipY };
    p.lk = { x: centerX - spread * .62, y: hipY + body * .62 };
    p.rk = { x: centerX + spread * .62, y: hipY + body * .62 };
    p.la = { x: centerX - spread * .72, y: hipY + body * 1.22 };
    p.ra = { x: centerX + spread * .72, y: hipY + body * 1.22 };
    p.le = { x: p.ls.x - spread * .18, y: p.ls.y + body * .34 };
    p.re = { x: p.rs.x + spread * .18, y: p.rs.y + body * .34 };
    p.lw = { x: p.le.x, y: p.le.y + body * .42 };
    p.rw = { x: p.re.x, y: p.re.y + body * .42 };
  } else if (exercise === "pushup") {
    const y = hipY + body * .25;
    p.ls = { x: centerX - spread * .55, y };
    p.rs = { x: centerX + spread * .55, y };
    p.lh = { x: centerX - spread * .25, y: y + body * .08 };
    p.rh = { x: centerX + spread * .25, y: y + body * .08 };
    p.lk = { x: centerX - spread * .05, y: y + body * .14 };
    p.rk = { x: centerX + spread * .05, y: y + body * .14 };
    p.la = { x: centerX + spread * .88, y: y + body * .2 };
    p.ra = { x: centerX + spread * 1.02, y: y + body * .2 };
    p.le = { x: p.ls.x - spread * .2, y: y + body * .38 };
    p.re = { x: p.rs.x + spread * .2, y: y + body * .38 };
    p.lw = { x: p.le.x - spread * .08, y: y + body * .74 };
    p.rw = { x: p.re.x - spread * .08, y: y + body * .74 };
  } else {
    p.rs = { x: centerX + spread * .45, y: shoulderY };
    p.rh = { x: centerX + spread * .35, y: hipY };
    p.rk = { x: centerX + spread * .35, y: hipY + body * .9 };
    p.ra = { x: centerX + spread * .35, y: hipY + body * 1.65 };
    p.re = { x: p.rs.x + spread * .02, y: shoulderY + body * .55 };
    p.rw = { x: p.re.x + spread * .22, y: shoulderY + body * .12 };
    p.ls = { x: centerX - spread * .45, y: shoulderY };
    p.lh = { x: centerX - spread * .35, y: hipY };
    p.le = { x: p.ls.x - spread * .04, y: shoulderY + body * .55 };
    p.lw = { x: p.le.x - spread * .04, y: shoulderY + body * 1.03 };
    p.lk = { x: p.lh.x, y: hipY + body * .9 };
    p.la = { x: p.lh.x, y: hipY + body * 1.65 };
  }

  return [
    [p.ls, p.rs], [p.ls, p.le], [p.le, p.lw], [p.rs, p.re], [p.re, p.rw],
    [p.ls, p.lh], [p.rs, p.rh], [p.lh, p.rh],
    [p.lh, p.lk], [p.lk, p.la], [p.rh, p.rk], [p.rk, p.ra],
  ];
}

function roundRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + width, y, x + width, y + height, radius);
  ctx.arcTo(x + width, y + height, x, y + height, radius);
  ctx.arcTo(x, y + height, x, y, radius);
  ctx.arcTo(x, y, x + width, y, radius);
  ctx.closePath();
}

function startTimer() {
  clearInterval(state.timerId);
  const startedAt = Date.now();
  state.elapsed = 0;
  state.timerId = setInterval(() => {
    state.elapsed = Math.floor((Date.now() - startedAt) / 1000);
    renderTimer();
  }, 1000);
  renderTimer();
}

function setStatus(status) {
  state.status = status;
  render();
}

function render() {
  if (!state.initialized) return;
  const running = state.status === "running";
  const loading = state.status === "loading";
  const error = state.status === "error";

  els.overlay?.classList.toggle("hidden", running);

  if (els.overlay) {
    const h3 = els.overlay.querySelector("h3");
    const p = els.overlay.querySelector("p");
    if (loading) {
      if (h3) h3.textContent = "Loading the model...";
      if (p) p.textContent = "Please wait while we initialize pose estimation.";
    } else if (error) {
      if (h3) h3.textContent = "Camera blocked";
      if (p) p.textContent = "Please check your browser permissions.";
    } else {
      if (h3) h3.textContent = "Starting Camera...";
      if (p) p.textContent = "Ensure your full body is visible in the frame.";
    }
  }

  state.displayAcc += (state.acc - state.displayAcc) * 0.22;
  const displayAcc = Math.round(state.displayAcc);
  const scoreState = getScoreState(displayAcc);

  if (els.reps) els.reps.textContent = String(state.reps);
  if (els.targetReps) els.targetReps.textContent = state.targetReps;
  if (els.accuracy) els.accuracy.textContent = `${displayAcc}%`;
  if (els.accuracyLabel) els.accuracyLabel.textContent = accuracyLabel(displayAcc);

  if (els.liveCue) {
    const cue = state.feedback?.cues?.[0] || "Good posture";
    els.liveCue.textContent = cue;
    els.liveCue.classList.toggle("good", Boolean(state.feedback && !state.feedback.cues.length));
    els.liveCue.classList.toggle("hidden", !running);
  }
}

function renderTimer() {
  if (!els.timer) return;
  const mins = Math.floor(state.elapsed / 60);
  const secs = state.elapsed % 60;
  els.timer.textContent = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function accuracyLabel(value) {
  if (value >= 90) return "Textbook execution";
  if (value >= 75) return "Solid, small tweaks";
  if (value >= 60) return "Watch your form";
  return "Slow down, reset";
}

function calculateStability(angles) {
  if (!angles) return 100;
  if (!state.previousAngles) {
    state.previousAngles = { ...angles };
    return 100;
  }
  const keys = Object.keys(angles).filter((key) => Number.isFinite(angles[key]) && Number.isFinite(state.previousAngles[key]));
  const delta = keys.reduce((sum, key) => sum + Math.abs(angles[key] - state.previousAngles[key]), 0) / Math.max(keys.length, 1);
  state.previousAngles = { ...angles };
  return Math.max(35, Math.min(100, 100 - delta * 4.5));
}

function getScoreState(value) {
  return SCORE_STATES.find((item) => value >= item.min) || SCORE_STATES[SCORE_STATES.length - 1];
}

function pulseRepCompletion() {
  // Option pulse effects
}

window.fitCoachGhostTrainer = { init, start: startSession, stop };

window.addEventListener("beforeunload", stop);
