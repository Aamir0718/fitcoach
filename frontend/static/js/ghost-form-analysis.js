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

// ── Side-aware joint model ──────────────────────────────────────────────────
// Previously every analyzer hardcoded LEFT_* (or, for the arm-isolation
// patterns, RIGHT_*) landmarks, and checkPoseReliability demanded BOTH sides
// at once — so a side-on camera view (the only view that actually reads
// knee/hip flexion correctly) always failed visibility, since the far leg
// is inherently occluded from that angle. pickSide() resolves "shoulder",
// "hip", etc. to whichever physical side is requested, with the other side
// available as opp* for the handful of checks that are genuinely bilateral
// (knee-collapse width, left/right raise symmetry) — those checks run only
// when the opposite side is actually visible (visOK below), so a side-on
// view silently skips a front-view-only check instead of false-firing it.
function pickSide(lm, side) {
  const s = side === "right" ? "RIGHT_" : "LEFT_";
  const o = side === "right" ? "LEFT_" : "RIGHT_";
  return {
    side,
    shoulder: lm[LM_ACTUAL[s + "SHOULDER"]], elbow: lm[LM_ACTUAL[s + "ELBOW"]], wrist: lm[LM_ACTUAL[s + "WRIST"]],
    hip: lm[LM_ACTUAL[s + "HIP"]], knee: lm[LM_ACTUAL[s + "KNEE"]], ankle: lm[LM_ACTUAL[s + "ANKLE"]],
    oppShoulder: lm[LM_ACTUAL[o + "SHOULDER"]], oppElbow: lm[LM_ACTUAL[o + "ELBOW"]], oppWrist: lm[LM_ACTUAL[o + "WRIST"]],
    oppHip: lm[LM_ACTUAL[o + "HIP"]], oppKnee: lm[LM_ACTUAL[o + "KNEE"]], oppAnkle: lm[LM_ACTUAL[o + "ANKLE"]],
  };
}

function visOK(pt) {
  return !!pt && (pt.visibility === undefined || pt.visibility >= VISIBILITY_THRESHOLD);
}

// Generic joint KEYS (not landmark indices) needed from a SINGLE side for
// that pattern to be analyzable — checked against left, then right.
const SIDE_JOINT_KEYS = {
  squat: ["shoulder", "hip", "knee", "ankle"],
  lunge: ["hip", "knee", "ankle"],
  hip_hinge: ["shoulder", "hip", "knee"],
  horizontal_push: ["shoulder", "elbow", "wrist", "hip", "ankle"],
  vertical_push: ["shoulder", "elbow", "wrist", "hip"],
  horizontal_pull: ["shoulder", "elbow", "wrist", "hip"],
  vertical_pull: ["shoulder", "elbow", "wrist"],
  elbow_flexion: ["shoulder", "elbow", "wrist", "hip"],
  elbow_extension: ["shoulder", "elbow", "wrist", "hip"],
  lateral_raise: ["shoulder", "elbow", "hip"],
  calf_raise: ["knee", "ankle"],
  core_isometric: ["shoulder", "hip", "ankle"],
  core_flex: ["shoulder", "hip", "knee"],
  cardio_generic: ["shoulder", "hip", "knee"],
  full_body_generic: ["shoulder", "hip", "knee"],
};
// core_rotation is a genuine exception: it measures shoulder-width-vs-hip-
// width, which is meaningless from a single side — it keeps the old
// both-sides-required check further down, by design, not by oversight.
const BOTH_SIDES_REQUIRED = new Set(["core_rotation"]);
const CORE_ROTATION_JOINTS = [
  LM_ACTUAL.LEFT_SHOULDER, LM_ACTUAL.RIGHT_SHOULDER, LM_ACTUAL.LEFT_HIP, LM_ACTUAL.RIGHT_HIP,
];

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

// 0.7 was strict enough that normal camera framing (slight angle, one side
// a little occluded, imperfect lighting) routinely failed this and froze
// rep counting entirely — "Body not fully visible" firing even when the
// athlete was doing the exercise correctly. Full per-side tracking (using
// whichever side IS clearly visible, instead of requiring both) is the
// real fix and is still pending; this lower threshold is the safe, quick
// improvement in the meantime — permissive enough that reps count in
// realistic conditions, not so permissive that a genuinely-out-of-frame
// athlete still tracks.
const VISIBILITY_THRESHOLD = 0.35;

function sideHasAllJoints(p, keys) {
  for (const k of keys) {
    if (!visOK(p[k])) return false;
  }
  return true;
}

// Returns { ok, side } — side is "left"/"right" for everything the figure
// can be read from one side, or "both" for the few genuinely-bilateral
// patterns. Tries left first (matches the old default so a front-facing
// user with both sides visible sees no behavior change), then right — so a
// side-on view now succeeds using whichever side the camera actually sees,
// instead of requiring both.
function checkPoseReliability(landmarks, pattern) {
  if (BOTH_SIDES_REQUIRED.has(pattern)) {
    for (const j of CORE_ROTATION_JOINTS) {
      if (!visOK(landmarks[j])) return { ok: false };
    }
    return { ok: true, side: "both" };
  }
  const keys = SIDE_JOINT_KEYS[pattern] || ["shoulder", "hip", "knee"];
  const left = pickSide(landmarks, "left");
  if (sideHasAllJoints(left, keys)) return { ok: true, side: "left" };
  const right = pickSide(landmarks, "right");
  if (sideHasAllJoints(right, keys)) return { ok: true, side: "right" };
  return { ok: false };
}

function newRepState() {
  return {
    reps: 0,
    phase: "up",
    stateName: "READY",   // READY <-> WORKING — see tick()'s peak/valley model
    repExtreme: null,     // angle extreme reached during the current WORKING excursion
    lastRepTime: 0,
    goodFrames: 0,
    totalFrames: 0,
    depthSamples: [],
    angleScores: [],
    holdSeconds: 0,       // used by core_isometric only
    activeSeconds: 0,     // used by cardio_generic / full_body_generic only
    lastTickTime: 0,
    lastRepROM: null,     // 0-1+ achieved range-of-motion of the most recently completed rep
    shallowReps: 0,       // reps completed but below the full-ROM floor — counted, not discarded
  };
}

// ── Dispatcher ──────────────────────────────────────────────────────────────
function analyze({ landmarks, exercise }) {
  if (!landmarks || landmarks.length < 29) return null;
  const pattern = resolvePattern(exercise);

  // 1. Smooth landmarks using EMA to eliminate camera noise/jitter
  const smoothed = smoothLandmarks(landmarks);
  if (!smoothed) return null;

  // 2. Validate pose confidence and visibility — on whichever side is
  // actually in frame, not both at once (see checkPoseReliability above).
  const reliability = checkPoseReliability(smoothed, pattern);
  if (!reliability.ok) {
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
  return analyzer(smoothed, reliability.side);
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

function analyzeSquat(lm, side) {
  const p = pickSide(lm, side || "left");
  const { hip, knee, ankle, shoulder, oppKnee, oppHip, oppAnkle } = p;
  const oppVisible = visOK(oppHip) && visOK(oppKnee) && visOK(oppAnkle);

  const kneeAngle = angleDeg(hip, knee, ankle);
  // Only a real second reading when the far leg is actually visible (a
  // front/3-quarter view) — in a true side-on view it's occluded, and
  // averaging in a near-arbitrary occluded-landmark angle would silently
  // drag the precision score around. Fall back to the primary angle.
  const rightKneeAngle = oppVisible ? angleDeg(oppHip, oppKnee, oppAnkle) : kneeAngle;
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
  // Knee-collapse (valgus) is a FRONT-view check — comparing left/right knee
  // separation against ankle separation is meaningless foreshortened from
  // the side, where it would read as near-zero and false-fire every rep.
  // Only run it when the far leg is actually visible.
  if (oppVisible) {
    const kneeWidth = Math.abs(knee.x - oppKnee.x);
    const ankleWidth = Math.abs(ankle.x - oppAnkle.x);
    if (kneeWidth < ankleWidth * 0.68) {
      cues.push("Push knees out");
      good = false;
      errors.push("knee_collapse");
    }
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
    side: p.side,
    angles: { leftKnee: kneeAngle, rightKnee: rightKneeAngle, leftHip: hipAngle },
  };
}

function analyzeLunge(lm, side) {
  // Track whichever leg is currently more bent as the "working" (front) leg —
  // a single 2D camera can't reliably tell front from back leg otherwise.
  // Primary side drives the fallback shoulder reading (lunge's visibility
  // key set doesn't require shoulder, so grab it defensively).
  const p = pickSide(lm, side || "left");
  const { hip, knee, ankle, oppHip, oppKnee, oppAnkle } = p;
  const shoulder = p.shoulder || p.oppShoulder;
  const oppVisible = visOK(oppHip) && visOK(oppKnee) && visOK(oppAnkle);

  const primaryAngle = angleDeg(hip, knee, ankle);
  const oppAngle = oppVisible ? angleDeg(oppHip, oppKnee, oppAnkle) : primaryAngle;
  const kneeAngle = Math.min(primaryAngle, oppAngle);
  const hipAngle = shoulder ? angleDeg(shoulder, hip, knee) : 165; // 165 = neutral/upright fallback, never flags a fault
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
    side: p.side,
    angles: { workingKnee: kneeAngle, leftHip: hipAngle },
  };
}

function analyzeHipHinge(lm, side) {
  const p = pickSide(lm, side || "left");
  const { shoulder, hip, knee, ankle } = p;

  const hipAngle = angleDeg(shoulder, hip, knee);
  const kneeAngle = angleDeg(hip, knee, ankle);
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
    side: p.side,
    angles: { leftHip: hipAngle, leftKnee: kneeAngle },
  };
}

function analyzeHorizontalPush(lm, side) {
  const p = pickSide(lm, side || "left");
  const { shoulder, elbow, wrist, hip, ankle, oppShoulder, oppElbow, oppWrist } = p;
  const oppVisible = visOK(oppShoulder) && visOK(oppElbow) && visOK(oppWrist);

  const elbowAngle = angleDeg(shoulder, elbow, wrist);
  const rightElbowAngle = oppVisible ? angleDeg(oppShoulder, oppElbow, oppWrist) : elbowAngle;
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
    side: p.side,
    angles: { leftElbow: elbowAngle, rightElbow: rightElbowAngle, leftHip: bodyLine },
  };
}

function analyzeVerticalPush(lm, side) {
  const p = pickSide(lm, side || "left");
  const { shoulder, elbow, wrist, hip, knee, oppShoulder, oppElbow, oppWrist } = p;
  const oppVisible = visOK(oppShoulder) && visOK(oppElbow) && visOK(oppWrist);

  const elbowAngle = angleDeg(shoulder, elbow, wrist);
  const rightElbowAngle = oppVisible ? angleDeg(oppShoulder, oppElbow, oppWrist) : elbowAngle;
  const torsoLean = angleDeg(knee || hip, hip, shoulder);
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
    side: p.side,
    angles: { leftElbow: elbowAngle, rightElbow: rightElbowAngle },
  };
}

function analyzeHorizontalPull(lm, side) {
  const p = pickSide(lm, side || "left");
  const { shoulder, elbow, wrist, hip, knee, oppShoulder, oppElbow, oppWrist } = p;
  const oppVisible = visOK(oppShoulder) && visOK(oppElbow) && visOK(oppWrist);

  const elbowAngle = angleDeg(shoulder, elbow, wrist);
  const rightElbowAngle = oppVisible ? angleDeg(oppShoulder, oppElbow, oppWrist) : elbowAngle;
  const torsoLean = angleDeg(knee || hip, hip, shoulder);
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
    side: p.side,
    angles: { leftElbow: elbowAngle, rightElbow: rightElbowAngle },
  };
}

function analyzeVerticalPull(lm, side) {
  const p = pickSide(lm, side || "left");
  const { shoulder, elbow, wrist, oppShoulder, oppElbow, oppWrist } = p;
  const oppVisible = visOK(oppShoulder) && visOK(oppElbow) && visOK(oppWrist);

  const elbowAngle = angleDeg(shoulder, elbow, wrist);
  const rightElbowAngle = oppVisible ? angleDeg(oppShoulder, oppElbow, oppWrist) : elbowAngle;
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
    side: p.side,
    angles: { leftElbow: elbowAngle, rightElbow: rightElbowAngle },
  };
}

function analyzeElbowFlexion(lm, side) {
  const p = pickSide(lm, side || "left");
  const { shoulder, elbow, wrist, hip } = p;
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
    side: p.side,
    angles: { rightElbow: elbowAngle, rightShoulder: shoulderAngle },
  };
}

function analyzeElbowExtension(lm, side) {
  const p = pickSide(lm, side || "left");
  const { shoulder, elbow, wrist, hip } = p;
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
    side: p.side,
    angles: { rightElbow: elbowAngle, rightShoulder: shoulderAngle },
  };
}

function analyzeLateralRaise(lm, side) {
  const p = pickSide(lm, side || "left");
  const { shoulder, elbow, hip, oppShoulder, oppElbow, oppHip } = p;
  const oppVisible = visOK(oppShoulder) && visOK(oppElbow) && visOK(oppHip);

  const raiseAngle = angleDeg(hip, shoulder, elbow);
  const oppRaiseAngle = oppVisible ? angleDeg(oppHip, oppShoulder, oppElbow) : raiseAngle;
  const cues = [];
  let good = true;
  const errors = [];

  if (elbow.y < shoulder.y - 0.05) {
    cues.push("Raise to shoulder height, not above");
    errors.push("too_high");
  }
  // Only a real symmetry check when the opposite arm is actually visible —
  // otherwise oppRaiseAngle === raiseAngle by the fallback above, and this
  // would never fire (harmless — just correctly inert instead of a false
  // "uneven" report from a nonsense occluded-side angle).
  if (oppVisible && Math.abs(raiseAngle - oppRaiseAngle) > 20) {
    cues.push("Raise both arms evenly");
    good = false;
    errors.push("uneven_raise");
  }

  const depthPct = clamp(((raiseAngle - 15) / 65) * 100, 0, 100);
  const phase = raiseAngle > 60 ? "down" : "up"; // "down" = arms raised (working phase)
  const precision = scoreTargets([targetScore(raiseAngle, 80, 40)]);
  return {
    primaryAngle: raiseAngle, exercise: "lateral_raise", phase, good, cues, errors, depthPct, precision,
    side: p.side,
    angles: { rightRaise: raiseAngle, leftRaise: oppRaiseAngle },
  };
}

function analyzeCalfRaise(lm, side) {
  // MediaPipe's 13-point subset here has no foot/toe landmark, so true ankle
  // plantarflexion angle isn't measurable — approximate using the ankle's
  // vertical rise relative to the knee as a heel-lift proxy, scaled to look
  // like a 0-180 "angle" so it can reuse the same rep state machine.
  const p = pickSide(lm, side || "left");
  const { knee, ankle } = p;

  const lift = clamp((knee.y - ankle.y) * -400, -20, 40); // more negative ankle.y (higher) = bigger lift
  const pseudoAngle = 90 + lift; // baseline ~90, rises toward ~130 at full raise
  const cues = [];
  const errors = [];

  const depthPct = clamp((lift / 30) * 100, 0, 100);
  const phase = pseudoAngle > 108 ? "down" : "up"; // "down" = raised (working phase)
  const precision = scoreTargets([targetScore(pseudoAngle, 110, 25)]);
  return {
    primaryAngle: pseudoAngle, exercise: "calf_raise", phase, good: true, cues, errors, depthPct, precision,
    side: p.side,
    angles: { heelLift: pseudoAngle },
  };
}

function analyzeCoreIsometric(lm, side) {
  const p = pickSide(lm, side || "left");
  const { shoulder, hip, ankle } = p;
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
    depthPct: good ? 100 : 40, precision, side: p.side, angles: { bodyLine },
  };
}

function analyzeCoreFlex(lm, side) {
  const p = pickSide(lm, side || "left");
  const { shoulder, hip, knee } = p;
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
    side: p.side,
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

// Below this fraction of the ready->down range, a "rep" is rejected outright
// rather than merely flagged shallow — this is the floor that keeps a twitch
// near the ready position from registering as a rep at all.
const MIN_REP_ROM = 0.35;
// Below this fraction, a completed rep still counts (nothing is silently
// dropped — see B1) but is tagged shallow so the UI/summary can flag it.
const FULL_REP_ROM = 0.75;

function tick(state, fb) {
  const next = {
    ...state,
    totalFrames: state.totalFrames + 1,
    goodFrames: state.goodFrames + (fb.good ? 1 : 0),
    depthSamples: [...state.depthSamples.slice(-80), fb.depthPct],
    // Store precision on the SAME 0-100 scale as everything else scoreForm()
    // combines it with. Analyzers return precision as a 0-1 fraction
    // (targetScore()/scoreTargets()); storing that fraction directly here
    // (with a same-scale-mismatched "100" fallback) is what silently capped
    // displayed form accuracy at ~70% even on a textbook rep — see scoreForm().
    angleScores: [...state.angleScores.slice(-80), (fb.precision ?? 1) * 100],
  };

  const now = Date.now();
  const dt = state.lastTickTime ? Math.min(1, (now - state.lastTickTime) / 1000) : 0;
  next.lastTickTime = now;

  // If the frame is invalid (low visibility or bad landmarks), pause transitions and return
  if (!fb.good && fb.errors && fb.errors.includes("low_visibility")) {
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

  // ── Peak/valley rep counting ──────────────────────────────────────────────
  // Replaces a 3-zone (READY/DOWN/UP) state machine that required the angle
  // to land inside a narrow ~10° window AND hold there for 300ms to register
  // a rep — a real ascent crosses that window in ~100-150ms, so most
  // completed reps were silently swallowed (the state jumped DOWN -> READY
  // directly, never passing through a committed "UP"). This model instead
  // just tracks the extreme angle reached during one WORKING excursion and
  // grades the achieved range-of-motion when the athlete returns to ready —
  // no narrow window, no hold-to-commit, and no per-frame direction gate (so
  // it behaves identically at 30fps and 60fps — a fixed angle THRESHOLD
  // crossing needs no dt normalization, unlike the old frame-to-frame trend
  // check it replaces).
  const angle = fb.primaryAngle;
  const span = Math.abs(rom.ready - rom.down) || 1;
  // Small guard band around "ready" so sensor jitter right at the top can't
  // repeatedly flick WORKING on/off; NOT a narrow commit window like before —
  // entering WORKING only requires crossing past it once.
  const deadband = span * 0.15;

  const COOLDOWN = 350; // ms — pure double-count guard; unlike before, it does
                        // NOT freeze an in-progress rep, only re-arming READY.
  const cooling = now - (state.lastRepTime || 0) < COOLDOWN;

  // True hysteresis: the exit boundary sits BETWEEN the entry boundary and
  // "ready" itself (closer to ready), not on ready's far side — the top of a
  // rep never overshoots past its own starting angle, it only returns to it.
  // A single shared boundary would flicker WORKING on/off on any noise
  // sitting right on that line; two boundaries with a gap between them
  // don't, while still not requiring the athlete to fully lock out at the
  // exact starting angle to get credit for the rep.
  const enteringWorking = rom.invert ? angle > rom.ready + deadband : angle < rom.ready - deadband;
  const returnedToReady = rom.invert ? angle < rom.ready + deadband * 0.4 : angle > rom.ready - deadband * 0.4;

  if (state.stateName !== "WORKING") {
    if (enteringWorking && !cooling) {
      next.stateName = "WORKING";
      next.repExtreme = angle;
    }
  } else {
    next.repExtreme = rom.invert
      ? Math.max(state.repExtreme ?? angle, angle)
      : Math.min(state.repExtreme ?? angle, angle);

    if (returnedToReady) {
      const achieved = rom.invert
        ? (next.repExtreme - rom.ready) / (rom.down - rom.ready)
        : (rom.ready - next.repExtreme) / (rom.ready - rom.down);
      if (achieved >= MIN_REP_ROM) {
        next.reps = state.reps + 1;
        next.lastRepTime = now;
        next.lastRepROM = achieved;
        if (achieved < FULL_REP_ROM) {
          next.shallowReps = (state.shallowReps || 0) + 1;
          fb.cues = ["Nice — go a little deeper next rep for full credit", ...(fb.cues || [])];
        }
      }
      next.stateName = "READY";
      next.repExtreme = null;
    }
  }

  next.phase = next.stateName === "WORKING" ? "down" : "up";

  // Real-time guide cue, generic across patterns since the exact ROM language
  // already comes from fb.cues (per-analyzer form feedback) — this just orients
  // the user within the rep (ready / working).
  const guideCues = [];
  if (next.stateName === "READY") {
    guideCues.push("Ready — begin the movement");
  } else if (next.stateName === "WORKING") {
    guideCues.push("Good — control it back to the start position");
  }
  fb.cues = [...guideCues, ...(fb.cues || [])];

  return next;
}

function scoreForm({ state, feedback, stabilityScore }) {
  if (!feedback || !state.totalFrames) return 100;
  const posture = (state.goodFrames / state.totalFrames) * 100;
  // Same 0-1-vs-0-100 scale fix as tick()'s angleScores push above — this
  // fallback only fires if scoreForm() is ever called before a first tick().
  const precision = average(state.angleScores, (feedback.precision ?? 1) * 100);
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
