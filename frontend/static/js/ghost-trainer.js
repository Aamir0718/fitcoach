(function () {
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

const EXERCISE_BRIEFS = {
  squat: "Feet shoulder-width. Hips back, knees tracking, chest tall.",
  lunge: "Step through, torso upright, drop the back knee straight down.",
  hip_hinge: "Soft knees, push hips back, keep your spine neutral — hinge, don't squat.",
  horizontal_push: "Hands under shoulders, elbows near 45°. Lock the core, press with control.",
  vertical_push: "Press straight overhead — don't let the bar drift forward. Brace your core.",
  horizontal_pull: "Pull with your elbow, not your hand. No momentum, no torso swing.",
  vertical_pull: "Pull straight down/up in a vertical line — chin toward the bar.",
  elbow_flexion: "Pin the upper arm and curl without letting the shoulder swing forward.",
  elbow_extension: "Keep your upper arm still — only the forearm moves. Full extension every rep.",
  lateral_raise: "Lead with the elbows, raise to shoulder height, control the negative.",
  calf_raise: "Full range — rise onto your toes, then lower all the way down.",
  core_isometric: "One straight line from shoulders to ankles. Breathe, don't sag.",
  core_flex: "Curl your ribs toward your hips — don't just pull with your neck.",
  core_rotation: "Rotate from the torso, not the arms. Controlled, not flung.",
  cardio_generic: "Keep a steady pace and controlled movement — quality over speed.",
  full_body_generic: "Match the reference posture and keep your movement controlled.",
};
function briefFor(pattern) {
  return EXERCISE_BRIEFS[pattern] || EXERCISE_BRIEFS.full_body_generic;
}

const SCORE_STATES = [
  { min: 82, key: "good", color: "rgb(16, 185, 129)", glow: "rgba(16, 185, 129, .42)" },
  { min: 62, key: "warn", color: "rgb(245, 158, 11)", glow: "rgba(245, 158, 11, .42)" },
  { min: 0, key: "poor", color: "rgb(239, 68, 68)", glow: "rgba(239, 68, 68, .42)" },
];

const state = {
  status: "idle", // "idle", "loading", "running", "error"
  selectedExercises: [],
  activeSlotKey: null, // Set when launched from the Planner tab — marks the weekly-plan pool slot done on finish
  sessionLabel: "Workout",

  currentExerciseIndex: 0,
  currentSet: 1,
  exercise: "full_body_generic",
  targetReps: TARGET_REPS_ACTUAL,
  reps: 0,
  acc: 100,
  displayAcc: 100,
  accHistory: [], // rolling recent-accuracy samples — what "Check my form" reports from, so the number it quotes isn't just whatever the last single frame happened to be
  elapsed: 0,
  feedback: null,
  personDetected: false, // no one framed yet until the first landmark hit lands
  rafId: null,
  timerId: null,
  lastVideoTime: -1,
  repState: newRepState_ACTUAL(),
  previousAngles: null,
  deltaEma: null,
  stabilityScore: 100,
  lastError: null,
};

// Parse a numeric rep target out of strings like "10-12", "45s", "2 min", "12" —
// falls back to TARGET_REPS_ACTUAL when nothing numeric is found.
function parseRepsTarget(reps) {
  if (typeof reps === "number") return reps;
  const match = String(reps || "").match(/\d+/);
  return match ? parseInt(match[0], 10) : TARGET_REPS_ACTUAL;
}

const els = {};
let elsCached = false;

function cacheEls() {
  if (elsCached) return;
  els.chatModeShell = document.getElementById("chat-mode-shell");
  els.workoutContainer = document.getElementById("ghost-workout-container");

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

  els.workoutProgress = document.getElementById("ghost-workout-progress");
  els.workoutExerciseName = document.getElementById("ghost-workout-exercise-name");
  els.workoutSets = document.getElementById("ghost-workout-sets");

  els.nextSetBtn = document.getElementById("ghost-workout-nextset-btn");
  els.nextBtn = document.getElementById("ghost-workout-next-btn");
  els.finishBtn = document.getElementById("ghost-workout-finish-btn");

  els.nextSetBtn?.addEventListener("click", completeSet);
  els.nextBtn?.addEventListener("click", nextExercise);
  els.finishBtn?.addEventListener("click", finishWorkout);

  els.chatLivebarExercise = document.getElementById("ghost-chat-livebar-exercise");
  els.chatLivebarReps = document.getElementById("ghost-chat-livebar-reps");
  els.chatLivebarAcc = document.getElementById("ghost-chat-livebar-acc");

  els.chatSuggestions = document.getElementById("ghost-chat-suggestions");
  els.chatSuggestions?.addEventListener("click", (e) => {
    const chip = e.target.closest(".ghost-chip");
    if (!chip) return;
    if (chip.dataset.intent === "check-form") return answerCheckFormLocally();
    if (chip.dataset.msg) sendChat(chip.dataset.msg);
  });

  elsCached = true;
}

// ── Entry point used by the Planner tab (and the Coach chat "start workout"
// intercept): opens the live camera + exercise + docked-chat session inside
// the Coach tab, in place of the normal chat view. slotKey ties completion
// back to the weekly-plan pool (marks it done on finish).
async function startWithExercises(exercises, label, slotKey) {
  if (!exercises || !exercises.length) return;
  cacheEls();
  state.activeSlotKey = slotKey || null;
  state.sessionLabel = label || "Workout";
  state.selectedExercises = exercises;

  els.chatModeShell?.classList.add("hidden");
  els.workoutContainer?.classList.remove("hidden");
  setViewMode("cam"); // always start a fresh session on the camera view

  state.currentExerciseIndex = 0;
  state.currentSet = 1;
  state.elapsed = 0;

  resetChat(state.sessionLabel);
  loadCurrentWorkoutExercise();
  renderWorkoutQueue();
  await startCamera();
}

function loadCurrentWorkoutExercise() {
  const activeEx = state.selectedExercises[state.currentExerciseIndex];
  if (!activeEx) return;

  state.exercise = activeEx.movement_pattern || "full_body_generic";
  state.targetReps = parseRepsTarget(activeEx.reps);
  state.repState = newRepState_ACTUAL();
  state.reps = 0;
  state.acc = 100;
  state.displayAcc = 100;
  state.feedback = null;
  state.previousAngles = null;
  state.deltaEma = null;
  state.stabilityScore = 100;
  state.personDetected = false;
  state.accHistory = [];
  logSets = []; // reseed the manual set tracker for the new exercise

  if (els.workoutProgress) {
    els.workoutProgress.textContent = `Exercise ${state.currentExerciseIndex + 1} / ${state.selectedExercises.length}`;
  }
  if (els.workoutExerciseName) {
    els.workoutExerciseName.textContent = activeEx.name;
  }
  if (els.chatLivebarExercise) {
    els.chatLivebarExercise.textContent = activeEx.name;
  }
  if (els.chatLivebarReps) {
    els.chatLivebarReps.textContent = `0/${state.targetReps} reps`;
  }
  if (els.chatLivebarAcc) {
    els.chatLivebarAcc.textContent = "—";
  }
  if (els.workoutSets) {
    els.workoutSets.textContent = `${state.currentSet} of 3`;
  }

  if (els.reps) els.reps.textContent = "0";
  if (els.targetReps) els.targetReps.textContent = state.targetReps;
  if (els.accuracy) els.accuracy.textContent = "100%";
  if (els.accuracyLabel) els.accuracyLabel.textContent = "Textbook execution";
  if (els.brief) els.brief.textContent = activeEx.trainer_tip || briefFor(state.exercise);

  renderWorkoutQueue();
  if (document.getElementById("ghost-workout-layout")?.dataset.ghostMode === "log") renderLogSets();
}

function renderWorkoutQueue() {
  const queueList = document.getElementById("ghost-queue-list");
  const progressText = document.getElementById("ghost-queue-progress-text");
  const progressFill = document.getElementById("ghost-queue-progress-fill");
  if (!queueList || !state.selectedExercises.length) return;

  const total = state.selectedExercises.length;
  const completedCount = state.currentExerciseIndex;
  if (progressText) {
    progressText.textContent = `${completedCount} / ${total} Completed`;
  }
  if (progressFill) {
    progressFill.style.width = `${Math.round((completedCount / total) * 100)}%`;
  }

  // Group by section (warmup / main / cooldown) if the backend tagged them;
  // exercises without a section tag are treated as "main".
  let lastSection = null;
  queueList.innerHTML = state.selectedExercises.map((ex, idx) => {
    let iconClass = "dot";
    let iconText = "✔";
    let statusClass = "upcoming";

    if (idx < state.currentExerciseIndex) {
      iconClass = "checkmark";
      iconText = "✔";
      statusClass = "completed";
    } else if (idx === state.currentExerciseIndex) {
      iconClass = "active-indicator";
      iconText = idx + 1;
      statusClass = "active";
    } else {
      iconText = idx + 1;
    }

    const section = ex.section || "main";
    let header = "";
    if (section !== lastSection) {
      lastSection = section;
      const label = section === "warmup" ? "🔥 Warm-up" : section === "cooldown" ? "❄️ Cool-down" : "🏋 Workout";
      header = `<div class="ghost-queue-section-header">${label}</div>`;
    }

    return `
      ${header}
      <div class="ghost-queue-item ${statusClass}">
        <span class="gqi-icon ${iconClass}">${iconText}</span>
        <span class="gqi-name">${ex.name}</span>
        ${ex.reps ? `<span class="gqi-reps">${ex.reps}</span>` : ""}
      </div>
    `;
  }).join("");
}

// ── Docked AI Coach chat (live session — camera + chat side by side) ─────────
function resetChat(categoryLabel) {
  const box = document.getElementById("ghost-chat-box");
  if (!box) return;
  box.innerHTML = "";
  document.getElementById("ghost-chat-suggestions")?.classList.remove("hidden");
  appendChatMessage("bot", `Live session started — **${categoryLabel}**. I can see your reps and form as you go. Say things like "I want to do legs instead" any time and I'll swap the plan for you.`);
}

function appendChatMessage(role, text) {
  const box = document.getElementById("ghost-chat-box");
  if (!box) return;
  const div = document.createElement("div");
  div.className = `gcm ${role}`;
  // Escape first so user/bot text can't inject markup, then re-enable just
  // **bold** — the coach's replies use markdown-style emphasis that was
  // otherwise showing up as literal asterisks.
  const escaped = text.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  div.innerHTML = escaped.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

// "Check my form" is answered from the live tracker state, not the backend
// chat model — that endpoint is text-only and has no view of the camera, so
// routing this through it produced generic flattering replies ("your form
// is looking solid!") even when no one was in frame or moving at all.
function answerCheckFormLocally() {
  document.getElementById("ghost-chat-suggestions")?.classList.add("hidden");
  appendChatMessage("user", "How's my form looking so far?");

  if (!state.personDetected) {
    appendChatMessage("bot", "I can't actually see you in frame right now — step back so your full body is visible and I'll start tracking your reps and form live.");
    return;
  }

  // Report the rolling average rather than this instant's displayAcc — a
  // single number sampled at the moment you happen to ask can land on
  // either side of a temporary dip/spike, which is what made two "check my
  // form" asks seconds apart give noticeably different answers.
  const history = state.accHistory.length ? state.accHistory : [state.displayAcc];
  const acc = Math.round(history.reduce((sum, v) => sum + v, 0) / history.length);
  const exerciseName = state.selectedExercises[state.currentExerciseIndex]?.name || "this exercise";
  const repsLine = state.reps > 0
    ? `You're at ${state.reps}/${state.targetReps} reps on **${exerciseName}**.`
    : `I haven't picked up a rep yet on **${exerciseName}** — go ahead and start the movement and I'll track it live.`;
  appendChatMessage("bot", `Right now you're at **${acc}% form accuracy** — ${accuracyLabel(acc).toLowerCase()}. ${repsLine}`);
}

async function sendChat(presetMessage) {
  const input = document.getElementById("ghost-chat-input");
  const message = (presetMessage ?? input?.value ?? "").trim();
  if (!message) return;
  if (input) input.value = "";
  document.getElementById("ghost-chat-suggestions")?.classList.add("hidden");
  appendChatMessage("user", message);

  try {
    const token = localStorage.getItem("fc_token") || "";
    const res = await fetch(`${window.API || ""}/api/coach/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    appendChatMessage("bot", data.reply || "");

    // If the coach swapped today's session (e.g. "do legs instead"), reload the
    // live session with the new exercise list so camera + queue stay in sync.
    if (data.type === "workout_start" && Array.isArray(data.exercises) && data.exercises.length) {
      await startWithExercises(data.exercises, data.muscle_group || "Workout", data.slot_key || null);
    }
  } catch (err) {
    console.error("Ghost session chat failed:", err);
    appendChatMessage("bot", "Sorry, I couldn't reach the coach right now.");
  }
}

// ── Camera lifecycle ──────────────────────────────────────────────────────
async function startCamera() {
  setStatus("loading");
  try {
    if (!window.isSecureContext) {
      throw new Error("Camera requires HTTPS (or localhost) — this page isn't a secure context.");
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("This browser doesn't support camera access (navigator.mediaDevices missing).");
    }

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
    console.error("Ghost Trainer camera failed to start:", err);
    state.lastError = err;
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
  if (els.canvas) ctx?.clearRect(0, 0, els.canvas.width, els.canvas.height);
  setStatus("idle");

  // Return to the normal chat view.
  els.workoutContainer?.classList.add("hidden");
  els.chatModeShell?.classList.remove("hidden");
}

// Advances from the current set to the next (or, on the last set, into the
// next exercise). Called both by the camera's automatic rep-detection (once
// it sees targetReps hit) and by the manual "Next Set" button — pose-based
// rep counting is far from perfect, so relying on it as the *only* way to
// progress meant a missed/miscounted rep could strand someone on set 1 with
// no way forward except skipping the whole exercise via "Next Exercise".
function completeSet() {
  if (state.currentSet < 3) {
    state.currentSet += 1;
    state.reps = 0;
    state.repState = newRepState_ACTUAL();
    if (els.workoutSets) els.workoutSets.textContent = `${state.currentSet} of 3`;
    if (els.reps) els.reps.textContent = "0";
    if (typeof window.showToast === "function") {
      window.showToast(`💪 Set ${state.currentSet - 1} complete! Prepare for Set ${state.currentSet}.`);
    }
  } else {
    if (typeof window.showToast === "function") {
      window.showToast("🎉 Exercise complete!");
    }
    setTimeout(nextExercise, 1200);
  }
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
  await saveWorkoutSession();
  stop();

  state.selectedExercises = [];
  state.activeSlotKey = null;
  state.currentExerciseIndex = 0;
  state.currentSet = 1;

  if (typeof window.showToast === "function") {
    window.showToast("🎉 Workout logged successfully!");
  }
}

async function saveWorkoutSession() {
  if (!state.selectedExercises.length) return;

  const elapsedSeconds = state.elapsed;
  const durationMinutes = Math.max(1, Math.round(elapsedSeconds / 60));
  // Warm-up/cool-down are logged as part of the session but shouldn't inflate
  // "exercises done" messaging beyond the main workout — log them all anyway
  // since they're still real activity, just tagged.
  const exerciseNames = state.selectedExercises.map(ex => ex.name).join(", ");

  const payload = {
    muscle_group: (state.sessionLabel || "Workout").toUpperCase(),
    exercises_done: exerciseNames,
    duration: durationMinutes,
    mode: "ghost",
    zone: "green",
    slot_key: state.activeSlotKey || undefined,
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
    } else {
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
    state.personDetected = landmarks.length > 0;
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

        if (state.reps > previousReps && state.reps >= state.targetReps) {
          completeSet();
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

// Maps every angle key any of the 13 movement-pattern analyzers can return
// (see ghost-form-analysis.js) to a screen label + landmark anchor, so the
// on-screen degree readout works for all of them, not just squat/pushup/curl.
function angleLabelAnchors(landmarks, angles) {
  const anchors = [
    { key: "leftElbow",    name: "ELBOW", point: LM_ACTUAL.LEFT_ELBOW,    dx: -38, dy: -22 },
    { key: "rightElbow",   name: "ELBOW", point: LM_ACTUAL.RIGHT_ELBOW,   dx: 38,  dy: -22 },
    { key: "leftKnee",     name: "KNEE",  point: LM_ACTUAL.LEFT_KNEE,     dx: -34, dy: 24 },
    { key: "rightKnee",    name: "KNEE",  point: LM_ACTUAL.RIGHT_KNEE,    dx: 34,  dy: 24 },
    { key: "workingKnee",  name: "KNEE",  point: LM_ACTUAL.LEFT_KNEE,     dx: -34, dy: 24 },
    { key: "leftHip",      name: "HIP",   point: LM_ACTUAL.LEFT_HIP,      dx: -34, dy: -24 },
    { key: "rightHip",     name: "HIP",   point: LM_ACTUAL.RIGHT_HIP,     dx: 34,  dy: -24 },
    { key: "leftShoulder", name: "SHLD",  point: LM_ACTUAL.LEFT_SHOULDER, dx: -38, dy: -24 },
    { key: "rightShoulder",name: "SHLD",  point: LM_ACTUAL.RIGHT_SHOULDER,dx: 38,  dy: -24 },
    { key: "bodyLine",     name: "LINE",  point: LM_ACTUAL.LEFT_HIP,      dx: -34, dy: -24 },
    { key: "torso",        name: "TORSO", point: LM_ACTUAL.LEFT_HIP,      dx: -34, dy: -24 },
    { key: "rightRaise",   name: "RAISE", point: LM_ACTUAL.RIGHT_SHOULDER,dx: 38,  dy: -24 },
    { key: "leftRaise",    name: "RAISE", point: LM_ACTUAL.LEFT_SHOULDER, dx: -38, dy: -24 },
    { key: "heelLift",     name: "HEEL",  point: LM_ACTUAL.LEFT_ANKLE,    dx: -34, dy: 24 },
    { key: "twist",        name: "TWIST", point: LM_ACTUAL.LEFT_SHOULDER, dx: -38, dy: -24 },
    { key: "posture",      name: "POSE",  point: LM_ACTUAL.LEFT_HIP,      dx: -34, dy: -24 },
  ];
  return anchors
    .map((a) => ({ name: a.name, value: angles[a.key], point: landmarks[a.point], dx: a.dx, dy: a.dy }))
    .filter((label) => Number.isFinite(label.value));
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
  // Group the 13 movement patterns onto the two hand-built skeleton poses that
  // are the closest visual match — squat-family (lower-body, hip-driven) vs
  // push-family (upper-body pressing); everything else uses the generic pose.
  const squatFamily = ["squat", "lunge", "hip_hinge", "calf_raise"];
  const pushFamily = ["horizontal_push", "vertical_push", "core_isometric", "core_flex"];
  const patternGroup = squatFamily.includes(exercise) ? "squat" : pushFamily.includes(exercise) ? "pushup" : "generic";

  if (patternGroup === "squat") {
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
  } else if (patternGroup === "pushup") {
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

// Human-readable message per real failure mode, instead of a single generic
// "Camera blocked" for every possible error.
function cameraErrorMessage(err) {
  const name = err?.name || "";
  if (name === "NotAllowedError" || name === "PermissionDeniedError") {
    return { title: "Camera permission denied", body: "Allow camera access for this site in your browser's address-bar/site settings, then try again." };
  }
  if (name === "NotFoundError" || name === "DevicesNotFoundError") {
    return { title: "No camera found", body: "This device doesn't have an accessible camera, or it's disabled in your OS settings." };
  }
  if (name === "NotReadableError" || name === "TrackStartError") {
    return { title: "Camera in use", body: "Another app or browser tab is using the camera. Close it and try again." };
  }
  if (err?.message?.includes("HTTPS")) {
    return { title: "Insecure connection", body: err.message };
  }
  if (err?.message?.includes("mediaDevices")) {
    return { title: "Unsupported browser", body: err.message };
  }
  return { title: "Camera failed to start", body: err?.message || "Unknown error — check the browser console for details." };
}

function render() {
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
      const { title, body } = cameraErrorMessage(state.lastError);
      if (h3) h3.textContent = title;
      if (p) p.textContent = body;
    } else {
      if (h3) h3.textContent = "Starting Camera...";
      if (p) p.textContent = "Ensure your full body is visible in the frame.";
    }
  }

  // Gentler easing (was 0.22) — the raw per-frame score still has some
  // natural noise even after smoothing calculateStability(), and the faster
  // constant let that show up as a visibly flickering number.
  state.displayAcc += (state.acc - state.displayAcc) * 0.1;
  const displayAcc = Math.round(state.displayAcc);
  if (state.personDetected) {
    state.accHistory.push(state.displayAcc);
    if (state.accHistory.length > 90) state.accHistory.shift();
  }
  const scoreState = getScoreState(displayAcc);

  if (els.reps) els.reps.textContent = String(state.reps);
  if (els.targetReps) els.targetReps.textContent = state.targetReps;

  // Nobody in frame yet (camera just started, or they've stepped out) — say so
  // plainly instead of showing a leftover/default "100% Textbook execution",
  // which used to render even though nothing was actually being measured.
  const noOneFramed = running && !state.personDetected;
  if (els.accuracy) els.accuracy.textContent = noOneFramed ? "—" : `${displayAcc}%`;
  if (els.accuracyLabel) els.accuracyLabel.textContent = noOneFramed ? "Step into frame" : accuracyLabel(displayAcc);

  if (els.liveCue) {
    const cue = noOneFramed ? "Step into frame" : (state.feedback?.cues?.[0] || "Good posture");
    els.liveCue.textContent = cue;
    els.liveCue.classList.toggle("good", !noOneFramed && Boolean(state.feedback && !state.feedback.cues.length));
    els.liveCue.classList.toggle("hidden", !running);
  }

  // Keep the AI Coach panel's live-stats strip honest and in sync — same
  // numbers the "Check my form" reply is built from.
  if (els.chatLivebarExercise) {
    els.chatLivebarExercise.textContent = state.selectedExercises[state.currentExerciseIndex]?.name || "—";
  }
  if (els.chatLivebarReps) {
    els.chatLivebarReps.textContent = `${state.reps}/${state.targetReps} reps`;
  }
  if (els.chatLivebarAcc) {
    els.chatLivebarAcc.textContent = noOneFramed ? "not in frame" : `${displayAcc}% form`;
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
    state.deltaEma = 0;
    return 100;
  }
  const keys = Object.keys(angles).filter((key) => Number.isFinite(angles[key]) && Number.isFinite(state.previousAngles[key]));
  const delta = keys.reduce((sum, key) => sum + Math.abs(angles[key] - state.previousAngles[key]), 0) / Math.max(keys.length, 1);
  state.previousAngles = { ...angles };

  // A raw single-frame delta swings wildly during the normal working part of
  // a rep (the joint is *supposed* to move fast there) — scoring off that
  // instant made the accuracy number flicker every frame instead of
  // reflecting sustained shakiness. Smoothing it with an EMA keeps one quick
  // frame from cratering the score, then bouncing right back the next.
  state.deltaEma = state.deltaEma == null ? delta : state.deltaEma * 0.75 + delta * 0.25;
  return Math.max(35, Math.min(100, 100 - state.deltaEma * 3.2));
}

function getScoreState(value) {
  return SCORE_STATES.find((item) => value >= item.min) || SCORE_STATES[SCORE_STATES.length - 1];
}

// ── Log Sets / Form Camera view switch ───────────────────────────────────
// Purely a local view toggle — the camera keeps running underneath either
// way (pose tracking doesn't pause), this just swaps what's shown in the
// left column and doesn't touch the rep/accuracy pipeline.
function setViewMode(mode) {
  const layout = document.getElementById("ghost-workout-layout");
  if (!layout) return;
  layout.dataset.ghostMode = mode;
  document.querySelectorAll("[data-ghost-view]").forEach((el) => {
    el.classList.toggle("hidden", el.dataset.ghostView !== mode);
  });
  document.querySelectorAll("#ghost-mode-switch .wm-mode-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.ghostMode === mode);
  });
  if (mode === "log") renderLogSets();
}

// Local-only set tracker for Log Sets mode: weight/reps you type in plus a
// done toggle, seeded from the current exercise's target reps. This is not
// a second source of truth for reps/accuracy — that's still the camera's
// job — it's just the manual-logging view the redesign's spec calls for.
let logSets = [];

function renderLogSets() {
  const activeEx = state.selectedExercises[state.currentExerciseIndex];
  const nameEl = document.getElementById("ghost-log-exercise");
  if (nameEl) nameEl.textContent = activeEx?.name || "—";

  if (!logSets.length) {
    logSets = [1, 2, 3].map((n) => ({ n, kg: "", reps: state.targetReps || "", done: false }));
  }
  paintLogSets();
}

function paintLogSets() {
  const rows = document.getElementById("ghost-log-rows");
  if (!rows) return;
  rows.innerHTML = logSets.map((s, i) => `
    <div class="wlp-row">
      <span class="wlp-set-n">${s.n}</span>
      <input type="number" inputmode="decimal" class="wlp-input" placeholder="0" value="${s.kg}" onchange="window.fitCoachGhostTrainer?.updateLogSet(${i},'kg',this.value)"/>
      <input type="number" inputmode="numeric" class="wlp-input" placeholder="0" value="${s.reps}" onchange="window.fitCoachGhostTrainer?.updateLogSet(${i},'reps',this.value)"/>
      <button type="button" class="wlp-check ${s.done ? "done" : ""}" onclick="window.fitCoachGhostTrainer?.toggleLogSet(${i})">✔</button>
    </div>
  `).join("");
}

function updateLogSet(i, field, value) {
  if (!logSets[i]) return;
  logSets[i][field] = value;
}

function toggleLogSet(i) {
  if (!logSets[i]) return;
  logSets[i].done = !logSets[i].done;
  paintLogSets();
}

function addLogSet() {
  const last = logSets[logSets.length - 1];
  logSets.push({ n: logSets.length + 1, kg: last?.kg || "", reps: last?.reps || "", done: false });
  paintLogSets();
}

window.fitCoachGhostTrainer = {
  startWithExercises, stop, sendChat,
  setViewMode, addLogSet, updateLogSet, toggleLogSet,
};

window.addEventListener("beforeunload", stop);
})();
