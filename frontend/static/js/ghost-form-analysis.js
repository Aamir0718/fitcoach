// Import from global scope
const { angleDeg, LM } = window.GhostPose || {};

// Fallback LM if global not available
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

const LM_ACTUAL = LM || LM_FALLBACK;
const TARGET_REPS = 12;

const KEY_JOINTS = {
  squat: [
    LM_ACTUAL.LEFT_HIP, LM_ACTUAL.LEFT_KNEE, LM_ACTUAL.LEFT_ANKLE,
    LM_ACTUAL.RIGHT_HIP, LM_ACTUAL.RIGHT_KNEE, LM_ACTUAL.RIGHT_ANKLE,
    LM_ACTUAL.LEFT_SHOULDER
  ],
  pushup: [
    LM_ACTUAL.LEFT_SHOULDER, LM_ACTUAL.LEFT_ELBOW, LM_ACTUAL.LEFT_WRIST,
    LM_ACTUAL.RIGHT_SHOULDER, LM_ACTUAL.RIGHT_ELBOW, LM_ACTUAL.RIGHT_WRIST,
    LM_ACTUAL.LEFT_HIP, LM_ACTUAL.LEFT_ANKLE
  ],
  biceps: [
    LM_ACTUAL.RIGHT_SHOULDER, LM_ACTUAL.RIGHT_ELBOW, LM_ACTUAL.RIGHT_WRIST,
    LM_ACTUAL.RIGHT_HIP
  ]
};

let lastSmoothedLandmarks = null;
const ALPHA = 0.35;

function smoothLandmarks(current) {
  if (!current) return null;
  if (!lastSmoothedLandmarks || lastSmoothedLandmarks.length !== current.length) {
    lastSmoothedLandmarks = current.map(lm => ({ ...lm }));
    return lastSmoothedLandmarks;
  }
  for (let i = 0; i < current.length; i++) {
    lastSmoothedLandmarks[i].x = ALPHA * current[i].x + (1 - ALPHA) * lastSmoothedLandmarks[i].x;
    lastSmoothedLandmarks[i].y = ALPHA * current[i].y + (1 - ALPHA) * lastSmoothedLandmarks[i].y;
    lastSmoothedLandmarks[i].z = ALPHA * current[i].z + (1 - ALPHA) * lastSmoothedLandmarks[i].z;
    if (current[i].visibility !== undefined) {
      lastSmoothedLandmarks[i].visibility = ALPHA * current[i].visibility + (1 - ALPHA) * (lastSmoothedLandmarks[i].visibility || 0);
    }
  }
  return lastSmoothedLandmarks;
}

function checkPoseReliability(landmarks, exercise) {
  const joints = KEY_JOINTS[exercise] || [];
  for (const j of joints) {
    const lm = landmarks[j];
    if (!lm) return false;
    if (lm.visibility !== undefined && lm.visibility < 0.7) {
      return false;
    }
  }
  return true;
}

export function newRepState() {
  return {
    reps: 0,
    phase: "up",
    stateName: "READY", // READY -> DOWN -> UP
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
}

export function analyze({ landmarks, exercise }) {
  if (!landmarks || landmarks.length < 29) return null;

  // 1. Smooth landmarks using EMA to eliminate camera noise/jitter
  const smoothed = smoothLandmarks(landmarks);
  if (!smoothed) return null;

  // 2. Validate pose confidence and visibility
  const reliable = checkPoseReliability(smoothed, exercise);
  if (!reliable) {
    return {
      primaryAngle: 0,
      exercise,
      phase: "up",
      good: false,
      cues: ["Body not fully visible - check camera alignment"],
      errors: ["low_visibility"],
      depthPct: 0,
      precision: 0,
      angles: {}
    };
  }

  // 3. Analyze based on smoothed landmarks
  if (exercise === "squat") return analyzeSquat(smoothed);
  if (exercise === "pushup") return analyzePushup(smoothed);
  return analyzeBiceps(smoothed);
}

function analyzeSquat(lm) {
  const hip = lm[LM_ACTUAL.LEFT_HIP];
  const rightHip = lm[LM_ACTUAL.RIGHT_HIP];
  const knee = lm[LM_ACTUAL.LEFT_KNEE];
  const rightKnee = lm[LM_ACTUAL.RIGHT_KNEE];
  const ankle = lm[LM_ACTUAL.LEFT_ANKLE];
  const rightAnkle = lm[LM_ACTUAL.RIGHT_ANKLE];
  const shoulder = lm[LM_ACTUAL.LEFT_SHOULDER];

  const kneeAngle = angleDeg(hip, knee, ankle);
  const rightKneeAngle = angleDeg(rightHip, rightKnee, rightAnkle);
  const hipAngle = angleDeg(shoulder, hip, knee);
  const torsoLean = angleDeg(shoulder, hip, knee);
  const cues = [];
  let good = true;
  const errors = [];

  if (torsoLean < 130) {
    cues.push("Straighten your back");
    good = false;
    errors.push("leaning_torso");
  }
  const kneeWidth = Math.abs(knee.x - rightKnee.x);
  const ankleWidth = Math.abs(ankle.x - rightAnkle.x);
  if (kneeWidth < ankleWidth * 0.68) {
    cues.push("Push knees out");
    good = false;
    errors.push("knee_collapse");
  }
  if (Math.abs(knee.x - ankle.x) > 0.08) {
    cues.push("Keep knees over toes");
    good = false;
    errors.push("knee_tracking");
  }
  if (kneeAngle > 115 && kneeAngle <= 145) {
    cues.push("Go lower");
    errors.push("shallow_squat");
  }

  const depthPct = clamp(((170 - kneeAngle) / 90) * 100, 0, 100);
  const phase = kneeAngle < 110 ? "down" : "up";
  const precision = scoreTargets([
    targetScore(kneeAngle, 90, 85),
    targetScore(rightKneeAngle, 90, 85),
    targetScore(hipAngle, 95, 80),
  ]);

  return {
    primaryAngle: kneeAngle,
    exercise: "squat",
    phase,
    good,
    cues,
    errors,
    depthPct,
    precision,
    angles: {
      leftKnee: kneeAngle,
      rightKnee: rightKneeAngle,
      leftHip: hipAngle,
      leftShoulder: angleDeg(lm[LM_ACTUAL.LEFT_ELBOW], shoulder, hip),
    },
  };
}

function analyzePushup(lm) {
  const shoulder = lm[LM_ACTUAL.LEFT_SHOULDER];
  const rightShoulder = lm[LM_ACTUAL.RIGHT_SHOULDER];
  const elbow = lm[LM_ACTUAL.LEFT_ELBOW];
  const rightElbow = lm[LM_ACTUAL.RIGHT_ELBOW];
  const wrist = lm[LM_ACTUAL.LEFT_WRIST];
  const rightWrist = lm[LM_ACTUAL.RIGHT_WRIST];
  const hip = lm[LM_ACTUAL.LEFT_HIP];
  const ankle = lm[LM_ACTUAL.LEFT_ANKLE];

  const elbowAngle = angleDeg(shoulder, elbow, wrist);
  const rightElbowAngle = angleDeg(rightShoulder, rightElbow, rightWrist);
  const bodyLine = angleDeg(shoulder, hip, ankle);
  const shoulderAngle = angleDeg(elbow, shoulder, hip);
  const cues = [];
  let good = true;
  const errors = [];

  if (bodyLine < 160) {
    cues.push("Hips sagging - engage your core");
    good = false;
    errors.push("hips_sagging");
  }
  if (Math.abs(elbow.x - shoulder.x) > 0.16) {
    cues.push("Keep elbows tucked");
    good = false;
    errors.push("elbow_flare");
  }
  if (elbowAngle > 105 && elbowAngle <= 145) {
    cues.push("Lower your chest");
    errors.push("shallow_rep");
  }

  const depthPct = clamp(((170 - elbowAngle) / 90) * 100, 0, 100);
  const phase = elbowAngle < 100 ? "down" : "up";
  const precision = scoreTargets([
    targetScore(elbowAngle, 90, 85),
    targetScore(rightElbowAngle, 90, 85),
    targetScore(bodyLine, 175, 30),
  ]);

  return {
    primaryAngle: elbowAngle,
    exercise: "pushup",
    phase,
    good,
    cues,
    errors,
    depthPct,
    precision,
    angles: {
      leftElbow: elbowAngle,
      rightElbow: rightElbowAngle,
      leftShoulder: shoulderAngle,
      leftHip: bodyLine,
    },
  };
}

function analyzeBiceps(lm) {
  const shoulder = lm[LM_ACTUAL.RIGHT_SHOULDER];
  const elbow = lm[LM_ACTUAL.RIGHT_ELBOW];
  const wrist = lm[LM_ACTUAL.RIGHT_WRIST];
  const hip = lm[LM_ACTUAL.RIGHT_HIP];
  const elbowAngle = angleDeg(shoulder, elbow, wrist);
  const shoulderAngle = angleDeg(elbow, shoulder, hip);
  const cues = [];
  let good = true;
  const errors = [];

  if (elbow.x < shoulder.x - 0.06) {
    cues.push("Keep elbow tucked in");
    good = false;
    errors.push("swinging_arms");
  }
  if (shoulderAngle < 18 || shoulderAngle > 52) {
    cues.push("Stop swinging");
    good = false;
    errors.push("swinging_arms");
  }
  if (elbowAngle > 75 && elbowAngle <= 145) {
    cues.push("Curl all the way up");
    errors.push("incomplete_contraction");
  }
  if (elbowAngle < 50) cues.push("Squeeze at the top");

  const depthPct = clamp(((170 - elbowAngle) / 130) * 100, 0, 100);
  const phase = elbowAngle < 70 ? "down" : "up";
  const precision = scoreTargets([
    targetScore(elbowAngle, 55, 115),
    targetScore(shoulderAngle, 35, 35),
  ]);
  return {
    primaryAngle: elbowAngle,
    exercise: "biceps",
    phase,
    good,
    cues,
    errors,
    depthPct,
    precision,
    angles: {
      rightElbow: elbowAngle,
      rightShoulder: shoulderAngle,
      rightHip: angleDeg(shoulder, hip, lm[LM_ACTUAL.RIGHT_KNEE]),
    },
  };
}

export function tick(state, fb) {
  const next = {
    ...state,
    totalFrames: state.totalFrames + 1,
    goodFrames: state.goodFrames + (fb.good ? 1 : 0),
    depthSamples: [...state.depthSamples.slice(-80), fb.depthPct],
    angleScores: [...state.angleScores.slice(-80), fb.precision ?? 100],
  };

  // If the frame is invalid (low visibility or bad landmarks), pause transitions and return
  if (!fb.good || (fb.errors && fb.errors.includes("low_visibility"))) {
    next.pendingState = null;
    next.pendingStateTime = 0;
    return next;
  }

  const now = Date.now();
  const COOLDOWN = 700; // Cooldown of 700ms to prevent double counting
  const lastRepTime = state.lastRepTime || 0;

  // Ignore all detections during cooldown
  if (now - lastRepTime < COOLDOWN) {
    next.pendingState = null;
    next.pendingStateTime = 0;
    return next;
  }

  const primaryAngle = fb.primaryAngle;
  const exercise = fb.exercise;
  const currentStateName = state.stateName || "READY";

  // Rule 5: Direction check. Track angle trend (increasing/decreasing)
  const prevAngle = state.lastAngle;
  let angleTrend = state.angleTrend || 0; // -1 = decreasing, 1 = increasing
  if (prevAngle !== null) {
    const diff = primaryAngle - prevAngle;
    if (Math.abs(diff) > 2.0) { // Ignore small fluctuations below 2 degrees
      angleTrend = diff > 0 ? 1 : -1;
    }
  }
  next.lastAngle = primaryAngle;
  next.angleTrend = angleTrend;

  // Rule 2 & 9 & 10: State Machine target state determination based on ROM thresholds
  let targetState = null;
  if (exercise === "squat") {
    if (primaryAngle > 155) {
      targetState = "READY";
    } else if (primaryAngle < 105 && angleTrend === -1) {
      targetState = "DOWN";
    } else if (primaryAngle > 145 && currentStateName === "DOWN" && angleTrend === 1) {
      targetState = "UP";
    }
  } else if (exercise === "pushup") {
    if (primaryAngle > 155) {
      targetState = "READY";
    } else if (primaryAngle < 95 && angleTrend === -1) {
      targetState = "DOWN";
    } else if (primaryAngle > 145 && currentStateName === "DOWN" && angleTrend === 1) {
      targetState = "UP";
    }
  } else if (exercise === "biceps") {
    if (primaryAngle > 155) {
      targetState = "READY";
    } else if (primaryAngle < 65 && angleTrend === -1) {
      targetState = "DOWN";
    } else if (primaryAngle > 150 && currentStateName === "DOWN" && angleTrend === 1) {
      targetState = "UP";
    }
  }

  // Rule 3: Stability check (300ms delay) before transitioning state
  if (targetState && targetState !== currentStateName) {
    if (targetState !== state.pendingState) {
      next.pendingState = targetState;
      next.pendingStateTime = now;
    } else if (now - (state.pendingStateTime || 0) >= 300) {
      // Transition confirmed!
      if (currentStateName === "UP" && targetState === "READY") {
        next.reps = state.reps + 1;
        next.lastRepTime = now;
      }
      next.stateName = targetState;
      next.pendingState = null;
      next.pendingStateTime = 0;
    }
  } else {
    // Reset pending state if we don't have a new target state or user returns to current state
    next.pendingState = null;
    next.pendingStateTime = 0;
  }

  // Update dynamic phase value for form scoring logic compatibility
  next.phase = next.stateName === "DOWN" ? "down" : "up";

  // Rule 11: Real-time context feedback cues
  const guideCues = [];
  const activeState = next.stateName;

  if (exercise === "squat") {
    if (activeState === "READY") {
      if (primaryAngle < 150) {
        guideCues.push("Squat deeper - lower further");
      } else {
        guideCues.push("Ready - begin squatting");
      }
    } else if (activeState === "DOWN") {
      if (primaryAngle > 115) {
        guideCues.push("Lower further");
      } else {
        guideCues.push("Good depth - now push up!");
      }
    } else if (activeState === "UP") {
      guideCues.push("Almost done - stand all the way up");
    }
  } else if (exercise === "pushup") {
    if (activeState === "READY") {
      if (primaryAngle < 145) {
        guideCues.push("Lower further");
      } else {
        guideCues.push("Ready - begin push-up");
      }
    } else if (activeState === "DOWN") {
      if (primaryAngle > 105) {
        guideCues.push("Lower chest further");
      } else {
        guideCues.push("Good depth - push all the way up");
      }
    } else if (activeState === "UP") {
      guideCues.push("Straighten your arms completely");
    }
  } else if (exercise === "biceps") {
    if (activeState === "READY") {
      if (primaryAngle < 145) {
        guideCues.push("Straighten your arm completely");
      } else {
        guideCues.push("Ready - begin curl");
      }
    } else if (activeState === "DOWN") {
      if (primaryAngle > 75) {
        guideCues.push("Curl higher - raise higher");
      } else {
        guideCues.push("Good squeeze - lower slowly");
      }
    } else if (activeState === "UP") {
      guideCues.push("Straighten your arm completely");
    }
  }

  // Inject the guide cue at the front of the cues array
  fb.cues = [...guideCues, ...(fb.cues || [])];

  return next;
}

export function accuracy(state) {
  if (!state.totalFrames) return 100;
  return Math.round((state.goodFrames / state.totalFrames) * 100);
}

export function scoreForm({ state, feedback, stabilityScore }) {
  if (!feedback || !state.totalFrames) return 100;
  const posture = (state.goodFrames / state.totalFrames) * 100;
  const precision = average(state.angleScores, feedback.precision ?? 100);
  const range = rangeConsistency(state.depthSamples);
  return Math.round(clamp(
    posture * 0.35 + precision * 0.30 + stabilityScore * 0.20 + range * 0.15,
    0,
    100,
  ));
}

function rangeConsistency(samples) {
  if (!samples.length) return 100;
  const maxDepth = Math.max(...samples);
  const avgDepth = average(samples, 0);
  return clamp(maxDepth * 0.72 + avgDepth * 0.28, 0, 100);
}

function targetScore(value, target, tolerance) {
  return clamp(100 - (Math.abs(value - target) / tolerance) * 100, 0, 100);
}

function scoreTargets(values) {
  return Math.round(average(values, 100));
}

function average(values, fallback) {
  if (!values.length) return fallback;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

// Export to global scope for other scripts
window.GhostFormAnalysis = {
  TARGET_REPS,
  analyze,
  tick,
  scoreForm,
  newRepState
};
