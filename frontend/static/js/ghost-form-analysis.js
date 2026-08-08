(function () {
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

// ── Legacy names still used by older exercise-name maps — fold them onto the
// pattern they actually are so old and new callers both work.
const PATTERN_ALIASES = { pushup: "horizontal_push", biceps: "elbow_flexion" };
function resolvePattern(exercise) {
  return PATTERN_ALIASES[exercise] || exercise || "full_body_generic";
}

// ── Per-pattern joint sets used for the visibility/reliability check ──────────
const KEY_JOINTS = {
  squat: [
    LM_ACTUAL.LEFT_HIP, LM_ACTUAL.LEFT_KNEE, LM_ACTUAL.LEFT_ANKLE,
    LM_ACTUAL.RIGHT_HIP, LM_ACTUAL.RIGHT_KNEE, LM_ACTUAL.RIGHT_ANKLE,
    LM_ACTUAL.LEFT_SHOULDER,
  ],
  lunge: [
    LM_ACTUAL.LEFT_HIP, LM_ACTUAL.LEFT_KNEE, LM_ACTUAL.LEFT_ANKLE,
    LM_ACTUAL.RIGHT_HIP, LM_ACTUAL.RIGHT_KNEE, LM_ACTUAL.RIGHT_ANKLE,
  ],
  hip_hinge: [
    LM_ACTUAL.LEFT_SHOULDER, LM_ACTUAL.LEFT_HIP, LM_ACTUAL.LEFT_KNEE,
    LM_ACTUAL.RIGHT_HIP, LM_ACTUAL.RIGHT_KNEE,
  ],
  horizontal_push: [
    LM_ACTUAL.LEFT_SHOULDER, LM_ACTUAL.LEFT_ELBOW, LM_ACTUAL.LEFT_WRIST,
    LM_ACTUAL.RIGHT_SHOULDER, LM_ACTUAL.RIGHT_ELBOW, LM_ACTUAL.RIGHT_WRIST,
    LM_ACTUAL.LEFT_HIP, LM_ACTUAL.LEFT_ANKLE,
  ],
  vertical_push: [
    LM_ACTUAL.LEFT_SHOULDER, LM_ACTUAL.LEFT_ELBOW, LM_ACTUAL.LEFT_WRIST,
    LM_ACTUAL.RIGHT_SHOULDER, LM_ACTUAL.RIGHT_ELBOW, LM_ACTUAL.RIGHT_WRIST, LM_ACTUAL.LEFT_HIP,
  ],
  horizontal_pull: [
    LM_ACTUAL.LEFT_SHOULDER, LM_ACTUAL.LEFT_ELBOW, LM_ACTUAL.LEFT_WRIST,
    LM_ACTUAL.RIGHT_SHOULDER, LM_ACTUAL.RIGHT_ELBOW, LM_ACTUAL.RIGHT_WRIST, LM_ACTUAL.LEFT_HIP,
  ],
  vertical_pull: [
    LM_ACTUAL.LEFT_SHOULDER, LM_ACTUAL.LEFT_ELBOW, LM_ACTUAL.LEFT_WRIST,
    LM_ACTUAL.RIGHT_SHOULDER, LM_ACTUAL.RIGHT_ELBOW, LM_ACTUAL.RIGHT_WRIST, LM_ACTUAL.LEFT_HIP,
  ],
  elbow_flexion: [LM_ACTUAL.RIGHT_SHOULDER, LM_ACTUAL.RIGHT_ELBOW, LM_ACTUAL.RIGHT_WRIST, LM_ACTUAL.RIGHT_HIP],
  elbow_extension: [LM_ACTUAL.RIGHT_SHOULDER, LM_ACTUAL.RIGHT_ELBOW, LM_ACTUAL.RIGHT_WRIST, LM_ACTUAL.RIGHT_HIP],
  lateral_raise: [
    LM_ACTUAL.RIGHT_SHOULDER, LM_ACTUAL.RIGHT_ELBOW, LM_ACTUAL.RIGHT_HIP,
    LM_ACTUAL.LEFT_SHOULDER, LM_ACTUAL.LEFT_ELBOW, LM_ACTUAL.LEFT_HIP,
  ],
  calf_raise: [LM_ACTUAL.LEFT_KNEE, LM_ACTUAL.LEFT_ANKLE, LM_ACTUAL.RIGHT_KNEE, LM_ACTUAL.RIGHT_ANKLE],
  core_isometric: [LM_ACTUAL.LEFT_SHOULDER, LM_ACTUAL.LEFT_HIP, LM_ACTUAL.LEFT_ANKLE],
  core_flex: [LM_ACTUAL.LEFT_SHOULDER, LM_ACTUAL.LEFT_HIP, LM_ACTUAL.LEFT_KNEE],
  core_rotation: [LM_ACTUAL.LEFT_SHOULDER, LM_ACTUAL.RIGHT_SHOULDER, LM_ACTUAL.LEFT_HIP, LM_ACTUAL.RIGHT_HIP],
  cardio_generic: [LM_ACTUAL.LEFT_SHOULDER, LM_ACTUAL.LEFT_HIP, LM_ACTUAL.LEFT_KNEE, LM_ACTUAL.RIGHT_HIP, LM_ACTUAL.RIGHT_KNEE],
  full_body_generic: [LM_ACTUAL.LEFT_SHOULDER, LM_ACTUAL.LEFT_HIP, LM_ACTUAL.LEFT_KNEE, LM_ACTUAL.RIGHT_HIP, LM_ACTUAL.RIGHT_KNEE],
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

function checkPoseReliability(landmarks, pattern) {
  const joints = KEY_JOINTS[pattern] || [];
  for (const j of joints) {
    const lm = landmarks[j];
    if (!lm) return false;
    if (lm.visibility !== undefined && lm.visibility < 0.7) {
      return false;
    }
  }
  return true;
}

function newRepState() {
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
    holdSeconds: 0,       // used by core_isometric only
    activeSeconds: 0,     // used by cardio_generic / full_body_generic only
    lastTickTime: 0,
  };
}

// ── Dispatcher ──────────────────────────────────────────────────────────────
function analyze({ landmarks, exercise }) {
  if (!landmarks || landmarks.length < 29) return null;
  const pattern = resolvePattern(exercise);

  // 1. Smooth landmarks using EMA to eliminate camera noise/jitter
  const smoothed = smoothLandmarks(landmarks);
  if (!smoothed) return null;

  // 2. Validate pose confidence and visibility
  const reliable = checkPoseReliability(smoothed, pattern);
  if (!reliable) {
    return {
      primaryAngle: 0,
      exercise: pattern,
      phase: "up",
      good: false,
      cues: ["Body not fully visible - check camera alignment"],
      errors: ["low_visibility"],
      depthPct: 0,
      precision: 0,
      angles: {},
    };
  }

  const analyzer = ANALYZERS[pattern] || analyzeFullBodyGeneric;
  return analyzer(smoothed);
}

// ── Shared helpers ──────────────────────────────────────────────────────────
function clamp(val, min, max) {
  return Math.max(min, Math.min(max, val));
}

function targetScore(val, target, range) {
  const diff = Math.abs(val - target);
  const pct = Math.max(0, 1 - diff / range);
  return pct;
}

function scoreTargets(scores) {
  if (!scores.length) return 0;
  const sum = scores.reduce((a, b) => a + b, 0);
  return sum / scores.length;
}

function average(values, fallback) {
  if (!values.length) return fallback;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

// ── Per-pattern analyzers ───────────────────────────────────────────────────
// Each returns { primaryAngle, exercise (pattern key), phase, good, cues, errors,
// depthPct, precision, angles }. Direction of "good rep" ROM is handled centrally
// in tick() via PATTERN_ROM below — analyzers just report the current joint angle.

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
  const torsoLean = hipAngle;
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
    primaryAngle: kneeAngle, exercise: "squat", phase, good, cues, errors, depthPct, precision,
    angles: { leftKnee: kneeAngle, rightKnee: rightKneeAngle, leftHip: hipAngle },
  };
}

function analyzeLunge(lm) {
  // Track whichever leg is currently more bent as the "working" (front) leg —
  // a single 2D camera can't reliably tell front from back leg otherwise.
  const hip = lm[LM_ACTUAL.LEFT_HIP], rightHip = lm[LM_ACTUAL.RIGHT_HIP];
  const knee = lm[LM_ACTUAL.LEFT_KNEE], rightKnee = lm[LM_ACTUAL.RIGHT_KNEE];
  const ankle = lm[LM_ACTUAL.LEFT_ANKLE], rightAnkle = lm[LM_ACTUAL.RIGHT_ANKLE];
  const shoulder = lm[LM_ACTUAL.LEFT_SHOULDER];

  const leftAngle = angleDeg(hip, knee, ankle);
  const rightAngle = angleDeg(rightHip, rightKnee, rightAnkle);
  const kneeAngle = Math.min(leftAngle, rightAngle);
  const hipAngle = angleDeg(shoulder, hip, knee);
  const cues = [];
  let good = true;
  const errors = [];

  if (hipAngle < 135) {
    cues.push("Keep your torso upright");
    good = false;
    errors.push("leaning_torso");
  }
  if (kneeAngle > 110 && kneeAngle <= 140) {
    cues.push("Drop the back knee lower");
    errors.push("shallow_lunge");
  }

  const depthPct = clamp(((160 - kneeAngle) / 80) * 100, 0, 100);
  const phase = kneeAngle < 105 ? "down" : "up";
  const precision = scoreTargets([targetScore(kneeAngle, 90, 70), targetScore(hipAngle, 165, 40)]);

  return {
    primaryAngle: kneeAngle, exercise: "lunge", phase, good, cues, errors, depthPct, precision,
    angles: { workingKnee: kneeAngle, leftHip: hipAngle },
  };
}

function analyzeHipHinge(lm) {
  const shoulder = lm[LM_ACTUAL.LEFT_SHOULDER];
  const hip = lm[LM_ACTUAL.LEFT_HIP];
  const knee = lm[LM_ACTUAL.LEFT_KNEE];
  const rightHip = lm[LM_ACTUAL.RIGHT_HIP];
  const rightKnee = lm[LM_ACTUAL.RIGHT_KNEE];

  const hipAngle = angleDeg(shoulder, hip, knee);
  const kneeAngle = angleDeg(hip, knee, lm[LM_ACTUAL.LEFT_ANKLE]);
  const cues = [];
  let good = true;
  const errors = [];

  if (kneeAngle < 140) {
    cues.push("Keep a soft knee bend, don't squat it");
    errors.push("too_much_knee_bend");
  }
  if (hipAngle < 60) {
    cues.push("Don't round your lower back");
    good = false;
    errors.push("rounded_back");
  }

  const depthPct = clamp(((165 - hipAngle) / 100) * 100, 0, 100);
  const phase = hipAngle < 100 ? "down" : "up";
  const precision = scoreTargets([targetScore(hipAngle, 90, 75)]);

  return {
    primaryAngle: hipAngle, exercise: "hip_hinge", phase, good, cues, errors, depthPct, precision,
    angles: { leftHip: hipAngle, leftKnee: kneeAngle },
  };
}

function analyzeHorizontalPush(lm) {
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
  const cues = [];
  let good = true;
  const errors = [];

  if (bodyLine < 160) {
    cues.push("Keep a stable, braced base");
    good = false;
    errors.push("unstable_base");
  }
  if (Math.abs(elbow.x - shoulder.x) > 0.16) {
    cues.push("Keep elbows tucked ~45°");
    good = false;
    errors.push("elbow_flare");
  }
  if (elbowAngle > 105 && elbowAngle <= 145) {
    cues.push("Lower further before pressing");
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
    primaryAngle: elbowAngle, exercise: "horizontal_push", phase, good, cues, errors, depthPct, precision,
    angles: { leftElbow: elbowAngle, rightElbow: rightElbowAngle, leftHip: bodyLine },
  };
}

function analyzeVerticalPush(lm) {
  const shoulder = lm[LM_ACTUAL.LEFT_SHOULDER];
  const rightShoulder = lm[LM_ACTUAL.RIGHT_SHOULDER];
  const elbow = lm[LM_ACTUAL.LEFT_ELBOW];
  const rightElbow = lm[LM_ACTUAL.RIGHT_ELBOW];
  const wrist = lm[LM_ACTUAL.LEFT_WRIST];
  const rightWrist = lm[LM_ACTUAL.RIGHT_WRIST];
  const hip = lm[LM_ACTUAL.LEFT_HIP];

  const elbowAngle = angleDeg(shoulder, elbow, wrist);
  const rightElbowAngle = angleDeg(rightShoulder, rightElbow, rightWrist);
  const torsoLean = angleDeg(lm[LM_ACTUAL.LEFT_KNEE] || hip, hip, shoulder);
  const cues = [];
  let good = true;
  const errors = [];

  if (wrist.y > elbow.y + 0.03) {
    cues.push("Press straight overhead, not forward");
    errors.push("bar_path");
  }
  if (torsoLean < 155) {
    cues.push("Don't lean back — brace your core");
    good = false;
    errors.push("leaning_back");
  }

  const depthPct = clamp(((165 - elbowAngle) / 90) * 100, 0, 100);
  const phase = elbowAngle < 95 ? "down" : "up";
  const precision = scoreTargets([targetScore(elbowAngle, 90, 85), targetScore(rightElbowAngle, 90, 85)]);

  return {
    primaryAngle: elbowAngle, exercise: "vertical_push", phase, good, cues, errors, depthPct, precision,
    angles: { leftElbow: elbowAngle, rightElbow: rightElbowAngle },
  };
}

function analyzeHorizontalPull(lm) {
  const shoulder = lm[LM_ACTUAL.LEFT_SHOULDER];
  const rightShoulder = lm[LM_ACTUAL.RIGHT_SHOULDER];
  const elbow = lm[LM_ACTUAL.LEFT_ELBOW];
  const rightElbow = lm[LM_ACTUAL.RIGHT_ELBOW];
  const wrist = lm[LM_ACTUAL.LEFT_WRIST];
  const rightWrist = lm[LM_ACTUAL.RIGHT_WRIST];
  const hip = lm[LM_ACTUAL.LEFT_HIP];

  const elbowAngle = angleDeg(shoulder, elbow, wrist);
  const rightElbowAngle = angleDeg(rightShoulder, rightElbow, rightWrist);
  const torsoLean = angleDeg(lm[LM_ACTUAL.LEFT_KNEE] || hip, hip, shoulder);
  const cues = [];
  let good = true;
  const errors = [];

  if (torsoLean < 140) {
    cues.push("Don't use momentum — control the pull");
    good = false;
    errors.push("using_momentum");
  }
  if (Math.abs(elbow.y - shoulder.y) > 0.12) {
    cues.push("Pull elbow back and slightly down");
    errors.push("elbow_path");
  }

  const depthPct = clamp(((165 - elbowAngle) / 100) * 100, 0, 100);
  const phase = elbowAngle < 90 ? "down" : "up";
  const precision = scoreTargets([targetScore(elbowAngle, 75, 85), targetScore(rightElbowAngle, 75, 85)]);

  return {
    primaryAngle: elbowAngle, exercise: "horizontal_pull", phase, good, cues, errors, depthPct, precision,
    angles: { leftElbow: elbowAngle, rightElbow: rightElbowAngle },
  };
}

function analyzeVerticalPull(lm) {
  const shoulder = lm[LM_ACTUAL.LEFT_SHOULDER];
  const rightShoulder = lm[LM_ACTUAL.RIGHT_SHOULDER];
  const elbow = lm[LM_ACTUAL.LEFT_ELBOW];
  const rightElbow = lm[LM_ACTUAL.RIGHT_ELBOW];
  const wrist = lm[LM_ACTUAL.LEFT_WRIST];
  const rightWrist = lm[LM_ACTUAL.RIGHT_WRIST];

  const elbowAngle = angleDeg(shoulder, elbow, wrist);
  const rightElbowAngle = angleDeg(rightShoulder, rightElbow, rightWrist);
  const cues = [];
  let good = true;
  const errors = [];

  if (Math.abs(wrist.x - shoulder.x) > 0.22) {
    cues.push("Pull in a straight vertical line");
    errors.push("swinging");
  }
  if (elbowAngle > 90 && elbowAngle <= 150) {
    cues.push("Pull higher — chin toward the bar");
    errors.push("shallow_pull");
  }

  const depthPct = clamp(((165 - elbowAngle) / 100) * 100, 0, 100);
  const phase = elbowAngle < 80 ? "down" : "up";
  const precision = scoreTargets([targetScore(elbowAngle, 75, 85), targetScore(rightElbowAngle, 75, 85)]);

  return {
    primaryAngle: elbowAngle, exercise: "vertical_pull", phase, good, cues, errors, depthPct, precision,
    angles: { leftElbow: elbowAngle, rightElbow: rightElbowAngle },
  };
}

function analyzeElbowFlexion(lm) {
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
  const precision = scoreTargets([targetScore(elbowAngle, 55, 115), targetScore(shoulderAngle, 35, 35)]);
  return {
    primaryAngle: elbowAngle, exercise: "elbow_flexion", phase, good, cues, errors, depthPct, precision,
    angles: { rightElbow: elbowAngle, rightShoulder: shoulderAngle },
  };
}

function analyzeElbowExtension(lm) {
  const shoulder = lm[LM_ACTUAL.RIGHT_SHOULDER];
  const elbow = lm[LM_ACTUAL.RIGHT_ELBOW];
  const wrist = lm[LM_ACTUAL.RIGHT_WRIST];
  const hip = lm[LM_ACTUAL.RIGHT_HIP];
  const elbowAngle = angleDeg(shoulder, elbow, wrist);
  const shoulderAngle = angleDeg(elbow, shoulder, hip);
  const cues = [];
  let good = true;
  const errors = [];

  if (Math.abs(elbow.x - shoulder.x) > 0.1) {
    cues.push("Pin your upper arm still — only the forearm moves");
    good = false;
    errors.push("upper_arm_moving");
  }
  if (elbowAngle < 150 && elbowAngle >= 110) {
    cues.push("Extend fully at the bottom");
    errors.push("incomplete_extension");
  }

  const depthPct = clamp(((elbowAngle - 40) / 130) * 100, 0, 100);
  const phase = elbowAngle > 140 ? "down" : "up"; // "down" here = extended/working position
  const precision = scoreTargets([targetScore(elbowAngle, 160, 60), targetScore(shoulderAngle, 15, 30)]);
  return {
    primaryAngle: elbowAngle, exercise: "elbow_extension", phase, good, cues, errors, depthPct, precision,
    angles: { rightElbow: elbowAngle, rightShoulder: shoulderAngle },
  };
}

function analyzeLateralRaise(lm) {
  const shoulder = lm[LM_ACTUAL.RIGHT_SHOULDER];
  const elbow = lm[LM_ACTUAL.RIGHT_ELBOW];
  const hip = lm[LM_ACTUAL.RIGHT_HIP];
  const leftShoulder = lm[LM_ACTUAL.LEFT_SHOULDER];
  const leftElbow = lm[LM_ACTUAL.LEFT_ELBOW];
  const leftHip = lm[LM_ACTUAL.LEFT_HIP];

  const raiseAngle = angleDeg(hip, shoulder, elbow);
  const leftRaiseAngle = angleDeg(leftHip, leftShoulder, leftElbow);
  const cues = [];
  let good = true;
  const errors = [];

  if (elbow.y < shoulder.y - 0.05) {
    cues.push("Raise to shoulder height, not above");
    errors.push("too_high");
  }
  if (Math.abs(raiseAngle - leftRaiseAngle) > 20) {
    cues.push("Raise both arms evenly");
    good = false;
    errors.push("uneven_raise");
  }

  const depthPct = clamp(((raiseAngle - 15) / 65) * 100, 0, 100);
  const phase = raiseAngle > 60 ? "down" : "up"; // "down" = arms raised (working phase)
  const precision = scoreTargets([targetScore(raiseAngle, 80, 40)]);
  return {
    primaryAngle: raiseAngle, exercise: "lateral_raise", phase, good, cues, errors, depthPct, precision,
    angles: { rightRaise: raiseAngle, leftRaise: leftRaiseAngle },
  };
}

function analyzeCalfRaise(lm) {
  // MediaPipe's 13-point subset here has no foot/toe landmark, so true ankle
  // plantarflexion angle isn't measurable — approximate using the ankle's
  // vertical rise relative to the knee as a heel-lift proxy, scaled to look
  // like a 0-180 "angle" so it can reuse the same rep state machine.
  const knee = lm[LM_ACTUAL.LEFT_KNEE];
  const ankle = lm[LM_ACTUAL.LEFT_ANKLE];
  const rightKnee = lm[LM_ACTUAL.RIGHT_KNEE];
  const rightAnkle = lm[LM_ACTUAL.RIGHT_ANKLE];

  const lift = clamp((knee.y - ankle.y) * -400, -20, 40); // more negative ankle.y (higher) = bigger lift
  const pseudoAngle = 90 + lift; // baseline ~90, rises toward ~130 at full raise
  const cues = [];
  const errors = [];

  const depthPct = clamp((lift / 30) * 100, 0, 100);
  const phase = pseudoAngle > 108 ? "down" : "up"; // "down" = raised (working phase)
  const precision = scoreTargets([targetScore(pseudoAngle, 110, 25)]);
  return {
    primaryAngle: pseudoAngle, exercise: "calf_raise", phase, good: true, cues, errors, depthPct, precision,
    angles: { heelLift: pseudoAngle },
  };
}

function analyzeCoreIsometric(lm) {
  const shoulder = lm[LM_ACTUAL.LEFT_SHOULDER];
  const hip = lm[LM_ACTUAL.LEFT_HIP];
  const ankle = lm[LM_ACTUAL.LEFT_ANKLE];
  const bodyLine = angleDeg(shoulder, hip, ankle);
  const cues = [];
  let good = true;
  const errors = [];

  if (bodyLine < 160) {
    cues.push("Straighten your body into one line");
    good = false;
    errors.push("hips_sagging_or_piked");
  }

  const precision = scoreTargets([targetScore(bodyLine, 178, 25)]);
  return {
    primaryAngle: bodyLine, exercise: "core_isometric", phase: "hold", good, cues, errors,
    depthPct: good ? 100 : 40, precision, angles: { bodyLine },
  };
}

function analyzeCoreFlex(lm) {
  const shoulder = lm[LM_ACTUAL.LEFT_SHOULDER];
  const hip = lm[LM_ACTUAL.LEFT_HIP];
  const knee = lm[LM_ACTUAL.LEFT_KNEE];
  const torsoAngle = angleDeg(shoulder, hip, knee);
  const cues = [];
  const errors = [];
  let good = true;

  if (torsoAngle > 130 && torsoAngle <= 150) {
    cues.push("Curl further — lift your shoulders higher");
    errors.push("shallow_crunch");
  }

  const depthPct = clamp(((150 - torsoAngle) / 60) * 100, 0, 100);
  const phase = torsoAngle < 115 ? "down" : "up"; // "down" = crunched (working phase)
  const precision = scoreTargets([targetScore(torsoAngle, 110, 45)]);
  return {
    primaryAngle: torsoAngle, exercise: "core_flex", phase, good, cues, errors, depthPct, precision,
    angles: { torso: torsoAngle },
  };
}

function analyzeCoreRotation(lm) {
  // A single front-facing camera can't measure true axial rotation from 2D
  // landmarks — approximate using how much shoulder-width shrinks relative to
  // hip-width as the torso twists away from the camera, mapped onto the same
  // 0-180 pseudo-angle scale the rep engine expects.
  const ls = lm[LM_ACTUAL.LEFT_SHOULDER], rs = lm[LM_ACTUAL.RIGHT_SHOULDER];
  const lh = lm[LM_ACTUAL.LEFT_HIP], rh = lm[LM_ACTUAL.RIGHT_HIP];
  const shoulderWidth = Math.abs(ls.x - rs.x);
  const hipWidth = Math.abs(lh.x - rh.x) || 0.15;
  const twistRatio = clamp(shoulderWidth / hipWidth, 0.2, 1.2);
  const pseudoAngle = 90 * twistRatio; // ~90 = facing camera square, lower = twisted

  const cues = [];
  const errors = [];
  const depthPct = clamp(((90 - pseudoAngle) / 55) * 100, 0, 100);
  const phase = pseudoAngle < 60 ? "down" : "up"; // "down" = twisted (working phase)
  const precision = scoreTargets([targetScore(pseudoAngle, 55, 35)]);
  return {
    primaryAngle: pseudoAngle, exercise: "core_rotation", phase, good: true, cues, errors, depthPct, precision,
    angles: { twist: pseudoAngle },
  };
}

function analyzeFullBodyGeneric(lm) {
  // No single joint angle defines these (drills, cardio, machine work, sport
  // skills) — honestly report motion presence rather than a false-precision
  // form score. tick() paces "reps" off elapsed active time for this pattern.
  const shoulder = lm[LM_ACTUAL.LEFT_SHOULDER];
  const hip = lm[LM_ACTUAL.LEFT_HIP];
  const knee = lm[LM_ACTUAL.LEFT_KNEE];
  const postureAngle = angleDeg(shoulder, hip, knee);
  return {
    primaryAngle: postureAngle, exercise: "full_body_generic", phase: "active", good: true,
    cues: ["Keep a steady pace and controlled movement"], errors: [], depthPct: 60, precision: 0.8,
    angles: { posture: postureAngle },
  };
}

const ANALYZERS = {
  squat: analyzeSquat,
  lunge: analyzeLunge,
  hip_hinge: analyzeHipHinge,
  horizontal_push: analyzeHorizontalPush,
  vertical_push: analyzeVerticalPush,
  horizontal_pull: analyzeHorizontalPull,
  vertical_pull: analyzeVerticalPull,
  elbow_flexion: analyzeElbowFlexion,
  elbow_extension: analyzeElbowExtension,
  lateral_raise: analyzeLateralRaise,
  calf_raise: analyzeCalfRaise,
  core_isometric: analyzeCoreIsometric,
  core_flex: analyzeCoreFlex,
  core_rotation: analyzeCoreRotation,
  cardio_generic: analyzeFullBodyGeneric,
  full_body_generic: analyzeFullBodyGeneric,
};

// ── Rep-counting state machine — table-driven so every pattern above shares one
// implementation instead of a bespoke if/else chain per exercise. `invert: true`
// means the working ROM raises the angle instead of lowering it (e.g. lateral
// raise, calf raise, triceps extension).
const PATTERN_ROM = {
  squat:            { ready: 155, down: 105, up: 145 },
  lunge:            { ready: 150, down: 100, up: 140 },
  hip_hinge:        { ready: 160, down: 90,  up: 145 },
  horizontal_push:  { ready: 155, down: 95,  up: 145 },
  vertical_push:    { ready: 160, down: 90,  up: 150 },
  horizontal_pull:  { ready: 160, down: 70,  up: 140 },
  vertical_pull:    { ready: 160, down: 75,  up: 140 },
  elbow_flexion:    { ready: 155, down: 65,  up: 150 },
  elbow_extension:  { ready: 70,  down: 150, up: 100, invert: true },
  lateral_raise:    { ready: 25,  down: 65,  up: 40,  invert: true },
  calf_raise:       { ready: 95,  down: 118, up: 100, invert: true },
  core_flex:        { ready: 150, down: 90,  up: 130 },
  core_rotation:    { ready: 85,  down: 55,  up: 70,  invert: true },
};

function tick(state, fb) {
  const next = {
    ...state,
    totalFrames: state.totalFrames + 1,
    goodFrames: state.goodFrames + (fb.good ? 1 : 0),
    depthSamples: [...state.depthSamples.slice(-80), fb.depthPct],
    angleScores: [...state.angleScores.slice(-80), fb.precision ?? 100],
  };

  const now = Date.now();
  const dt = state.lastTickTime ? Math.min(1, (now - state.lastTickTime) / 1000) : 0;
  next.lastTickTime = now;

  // If the frame is invalid (low visibility or bad landmarks), pause transitions and return
  if (!fb.good && fb.errors && fb.errors.includes("low_visibility")) {
    next.pendingState = null;
    next.pendingStateTime = 0;
    return next;
  }

  const exercise = fb.exercise;

  // ── Isometric holds (plank / wall sit): reps field repurposed as seconds held ──
  if (exercise === "core_isometric") {
    next.holdSeconds = fb.good ? (state.holdSeconds || 0) + dt : Math.max(0, (state.holdSeconds || 0) - dt * 2);
    next.reps = Math.floor(next.holdSeconds);
    return next;
  }

  // ── Generic drills/cardio: pace a "rep" every 3s of continued activity ──
  if (exercise === "cardio_generic" || exercise === "full_body_generic") {
    next.activeSeconds = (state.activeSeconds || 0) + dt;
    next.reps = Math.floor(next.activeSeconds / 3);
    return next;
  }

  const rom = PATTERN_ROM[exercise];
  if (!rom) return next; // unknown pattern — no rep counting, just visibility/precision tracking

  const COOLDOWN = 700; // ms, prevents double counting
  const lastRepTime = state.lastRepTime || 0;
  if (now - lastRepTime < COOLDOWN) {
    next.pendingState = null;
    next.pendingStateTime = 0;
    return next;
  }

  const primaryAngle = fb.primaryAngle;
  const currentStateName = state.stateName || "READY";

  // Track angle trend (increasing/decreasing) to require real motion, not noise
  const prevAngle = state.lastAngle;
  let angleTrend = state.angleTrend || 0;
  if (prevAngle !== null) {
    const diff = primaryAngle - prevAngle;
    if (Math.abs(diff) > 2.0) angleTrend = diff > 0 ? 1 : -1;
  }
  next.lastAngle = primaryAngle;
  next.angleTrend = angleTrend;

  // Target-state determination, generalized across normal and inverted-ROM patterns
  let targetState = null;
  if (!rom.invert) {
    if (primaryAngle > rom.ready) targetState = "READY";
    else if (primaryAngle < rom.down && angleTrend === -1) targetState = "DOWN";
    else if (primaryAngle > rom.up && currentStateName === "DOWN" && angleTrend === 1) targetState = "UP";
  } else {
    if (primaryAngle < rom.ready) targetState = "READY";
    else if (primaryAngle > rom.down && angleTrend === 1) targetState = "DOWN";
    else if (primaryAngle < rom.up && currentStateName === "DOWN" && angleTrend === -1) targetState = "UP";
  }

  // Stability check (300ms) before committing a state transition, to reject jitter
  if (targetState && targetState !== currentStateName) {
    if (targetState !== state.pendingState) {
      next.pendingState = targetState;
      next.pendingStateTime = now;
    } else if (now - (state.pendingStateTime || 0) >= 300) {
      if (currentStateName === "UP" && targetState === "READY") {
        next.reps = state.reps + 1;
        next.lastRepTime = now;
      }
      next.stateName = targetState;
      next.pendingState = null;
      next.pendingStateTime = 0;
    }
  } else {
    next.pendingState = null;
    next.pendingStateTime = 0;
  }

  next.phase = next.stateName === "DOWN" ? "down" : "up";

  // Real-time guide cue, generic across patterns since the exact ROM language
  // already comes from fb.cues (per-analyzer form feedback) — this just orients
  // the user within the rep (ready / working / finishing).
  const guideCues = [];
  const activeState = next.stateName;
  if (activeState === "READY") {
    guideCues.push("Ready — begin the movement");
  } else if (activeState === "DOWN") {
    guideCues.push("Good range — now reverse the movement");
  } else if (activeState === "UP") {
    guideCues.push("Finish the rep — return to the start position");
  }
  fb.cues = [...guideCues, ...(fb.cues || [])];

  return next;
}

function scoreForm({ state, feedback, stabilityScore }) {
  if (!feedback || !state.totalFrames) return 100;
  const posture = (state.goodFrames / state.totalFrames) * 100;
  const precision = average(state.angleScores, feedback.precision ?? 100);
  const range = rangeConsistency(state.depthSamples);
  return Math.round(clamp(
    posture * 0.35 + precision * 0.30 + (stabilityScore ?? 100) * 0.20 + range * 0.15,
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

// Export to global scope for other scripts
window.GhostFormAnalysis = {
  TARGET_REPS,
  analyze,
  tick,
  scoreForm,
  newRepState,
  resolvePattern,
};
})();
