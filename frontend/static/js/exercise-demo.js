/*
 * FitCoach exercise demo renderer.
 *
 * Runtime-rendered (no image/video files, no downloads) filled-figure
 * animation for every exercise in the catalog. Shares its movement-pattern
 * vocabulary EXACTLY with the camera's rep-counting/analysis module
 * (ghost-form-analysis.js's ANALYZERS keys) rather than inventing a
 * separate one — one vocabulary, two consumers.
 *
 * Public API:
 *   window.FCDemo.renderDemo(exercise, opts) -> HTML string (a placeholder
 *     container with a unique id; call FCDemo.mount() after inserting it
 *     into the DOM, or use the auto-mount MutationObserver below).
 *   window.FCDemo.motionParams(exercise) -> derived {pattern, stance, grip,
 *     support, implement, unilateral} for reuse elsewhere (e.g. the camera's
 *     future per-exercise form rules can read the same params).
 *
 * One shared requestAnimationFrame loop drives every mounted demo — not one
 * loop per element — so a long exercise list doesn't spawn dozens of
 * independent loops on a mid-range phone.
 */
(function () {
  "use strict";

  // ── Movement-pattern vocabulary — must match ghost-form-analysis.js ────────
  var PATTERNS = [
    "squat", "lunge", "hip_hinge", "horizontal_push", "vertical_push",
    "horizontal_pull", "vertical_pull", "elbow_flexion", "elbow_extension",
    "lateral_raise", "calf_raise", "core_isometric", "core_flex",
    "core_rotation", "cardio_generic", "full_body_generic",
  ];

  // ── Name -> pattern classification ──────────────────────────────────────
  // Mirrors backend plan_service.py's classify_movement_pattern() keyword
  // idiom so a given exercise name resolves to the same pattern on both
  // sides — but this runs entirely client-side as a fallback for whenever
  // the exercise object doesn't already carry a server-provided
  // `movement_pattern` (which is preferred — see motionParams() below).
  var VERTICAL_PRESS_QUALIFIERS = ["overhead", "shoulder", "military", "pike", "arnold", "seated"];
  var PATTERN_RULES = [
    [["leg curl", "hamstring curl", "nordic"], "hip_hinge"],
    [["calf raise"], "calf_raise"],
    [["leg raise"], "core_flex"],
    [["lateral raise", "front raise", "upright row"], "lateral_raise"],
    [["push-up", "push up", "chest fly"], "horizontal_push"],
    [["pallof"], "core_rotation"],
    [["pull-up", "pull up", "chin-up", "chin up", "pulldown", "lat pull"], "vertical_pull"],
    [["row", "face pull", "pull-apart", "pull apart"], "horizontal_pull"],
    [["deadlift", "hip thrust", "glute bridge", "kickback", "good morning", "hip drive", "hip circle", "donkey kick", "fire hydrant", "clamshell", "abductor", "hip abduction"], "hip_hinge"],
    [["lunge", "split squat", "step-up", "step up"], "lunge"],
    [["squat", "leg press", "hack squat", "sissy squat"], "squat"],
    [["curl"], "elbow_flexion"],
    [["pushdown", "triceps extension", "tricep extension", "skull crusher", "overhead extension", "dip"], "elbow_extension"],
    [["plank", "wall sit", "hold", "hollow body", "pigeon pose", "wrist roller"], "core_isometric"],
    [["twist", "chop", "windmill"], "core_rotation"],
    [["crunch", "sit-up", "situp", "rollout", "v-up"], "core_flex"],
    [["external rotation"], "lateral_raise"],
    [["front-foot", "back-foot", "foot transfer"], "lunge"],
    [["slam"], "vertical_push"],
    [["block landing", "landing drill"], "lunge"],
    [["up-down", "crouch"], "squat"],
    [["jump", "sprint", "run", "walk", "shuttle", "ladder", "burpee", "mountain climber",
      "jumping jack", "star jump", "skip", "bound", "high knee", "butt kick", "box jump",
      "interval", "repeat", "conditioning", "dribble", "throw", "swing", "batting", "bowling",
      "fielding", "footwork", "agility", "drill", "stretch", "mobility", "cool-down", "cooldown",
      "stairmaster", "treadmill", "rowing machine", "cycling", "inchworm", "bear crawl", "sprawl",
      "dive and recover", "yo-yo", "passing", "receiving", "heading", "kicking", "negative split",
      "acceleration start", "ankle circles", "block save", "save technique", "striking"], "cardio_generic"],
  ];

  function classifyPattern(name) {
    var n = (name || "").toLowerCase();
    if (n.indexOf("press") !== -1 && n.indexOf("leg press") === -1 && n.indexOf("pallof") === -1) {
      for (var q = 0; q < VERTICAL_PRESS_QUALIFIERS.length; q++) {
        if (n.indexOf(VERTICAL_PRESS_QUALIFIERS[q]) !== -1) return "vertical_push";
      }
      return "horizontal_push";
    }
    for (var i = 0; i < PATTERN_RULES.length; i++) {
      var kws = PATTERN_RULES[i][0];
      for (var k = 0; k < kws.length; k++) {
        if (n.indexOf(kws[k]) !== -1) return PATTERN_RULES[i][1];
      }
    }
    return "full_body_generic";
  }

  // ── Name -> visual parameters (stance/grip/support/implement/unilateral) ──
  function has(n, words) { for (var i = 0; i < words.length; i++) if (n.indexOf(words[i]) !== -1) return true; return false; }

  function deriveParams(ex, patternHint) {
    var name = (ex && ex.name || "").toLowerCase();
    var pattern = patternHint || (ex && ex.movement_pattern) || classifyPattern(name);

    var unilateral = has(name, ["single", " ea", "each", "alternating", "one-arm", "one arm", "bulgarian"]);

    var stance = "shoulder";
    if (has(name, ["sumo"])) stance = "sumo";
    else if (has(name, ["bulgarian"])) stance = "bulgarian";
    else if (has(name, ["split squat", "split stance"])) stance = "split";
    else if (has(name, ["narrow", "close stance", "diamond"])) stance = "narrow";
    else if (has(name, ["wide"])) stance = "wide";

    var grip = "neutral";
    if (has(name, ["close-grip", "close grip"])) grip = "close";
    if (has(name, ["wide-grip", "wide grip"])) grip = "wide";
    if (has(name, ["underhand", "chin-up", "chin up", "hammer"])) grip = "underhand";

    var support = "standing";
    if (has(name, ["incline"])) support = "bench-incline";
    else if (has(name, ["decline"])) support = "bench-decline";
    else if (has(name, ["bench press", "flat dumbbell", "chest press", "lying"])) support = "bench-flat";
    else if (has(name, ["seated", "machine", "leg press", "hack squat", "leg extension", "leg curl", "lat pulldown"])) support = "seated";
    else if (has(name, ["plank", "push-up", "push up", "crunch", "sit-up", "leg raise", "hollow", "bird dog", "mountain climber", "burpee"])) support = "floor";

    var implement = "none";
    if (has(name, ["barbell"])) implement = "barbell";
    else if (has(name, ["dumbbell", "goblet"])) implement = "dumbbells";
    else if (has(name, ["kettlebell"])) implement = "kettlebell";
    else if (has(name, ["cable", "pushdown", "pulldown", "face pull", "pallof", "seated row", "cable row"])) implement = "cable";
    else if (has(name, ["band", "resistance band"])) implement = "band";
    else if (has(name, ["pull-up", "pull up", "chin-up", "chin up"])) implement = "bar";
    else if (has(name, ["cricket ball", "throwing"])) implement = "cricket-ball";
    else if (has(name, ["football", "ball striking", "dribble", "wall pass"]) && pattern === "cardio_generic") implement = "football";
    else if (has(name, ["med ball", "medicine ball"])) implement = "medball";

    return { pattern: pattern, stance: stance, grip: grip, support: support, implement: implement, unilateral: unilateral };
  }

  // ── Geometry helpers ─────────────────────────────────────────────────────
  var NS = "http://www.w3.org/2000/svg";
  function svgEl(tag, attrs) {
    var n = document.createElementNS(NS, tag);
    if (attrs) for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }
  // World-angle convention: 0deg = straight down, 90 = right (the direction
  // the figure faces), 180 = up, 270 = left/back. Shared by every pattern.
  function pt(o, angleDeg, len) {
    var r = (angleDeg * Math.PI) / 180;
    return { x: o.x + Math.sin(r) * len, y: o.y + Math.cos(r) * len };
  }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function lerpPt(a, b, t) { return { x: lerp(a.x, b.x, t), y: lerp(a.y, b.y, t) }; }
  function easeInOutSine(x) { return -(Math.cos(Math.PI * x) - 1) / 2; }

  // Stage palette — fixed, not page-theme-linked (the demo stage is its own
  // dark "video chip" in both light and dark viewer themes; see the sample
  // preview this was validated against).
  var COLOR = {
    figure: "#EDE8DF",
    figureDim: "#B9B3A6",
    bench: "#9a8f7c",
    accent: "#FF6B45",
    floor: "#3a352c",
    dark: "#0e0c09",
    steel: "#DAD4C4",
  };

  var LENS = { torso: 44, neck: 9, upperArm: 26, forearm: 24, thigh: 36, shin: 34, headR: 13 };

  // ── Shared skeleton: builds the persistent SVG elements once, exposes
  // setPose(pose) which positions every element via forward kinematics from
  // a hip anchor + world angles, and returns the computed joint points so
  // per-pattern equipment can attach to hands/feet/shoulder. ──────────────
  function buildSkeleton(svg, lens) {
    lens = lens || LENS;
    var torso = svgEl("line", { stroke: COLOR.figure, "stroke-width": 15, "stroke-linecap": "round" });
    var neck = svgEl("line", { stroke: COLOR.figure, "stroke-width": 9, "stroke-linecap": "round" });
    var head = svgEl("circle", { r: lens.headR, fill: COLOR.figure });
    var thighL = svgEl("line", { stroke: COLOR.figure, "stroke-width": 13, "stroke-linecap": "round" });
    var shinL = svgEl("line", { stroke: COLOR.figure, "stroke-width": 10, "stroke-linecap": "round" });
    var footL = svgEl("ellipse", { rx: 11, ry: 6, fill: COLOR.figure });
    var thighR = svgEl("line", { stroke: COLOR.figureDim, "stroke-width": 13, "stroke-linecap": "round" });
    var shinR = svgEl("line", { stroke: COLOR.figureDim, "stroke-width": 10, "stroke-linecap": "round" });
    var footR = svgEl("ellipse", { rx: 11, ry: 6, fill: COLOR.figureDim });
    var upperArmL = svgEl("line", { stroke: COLOR.figure, "stroke-width": 11, "stroke-linecap": "round" });
    var forearmL = svgEl("line", { stroke: COLOR.figure, "stroke-width": 9, "stroke-linecap": "round" });
    var handL = svgEl("circle", { r: 6, fill: COLOR.figure });
    var upperArmR = svgEl("line", { stroke: COLOR.figureDim, "stroke-width": 11, "stroke-linecap": "round" });
    var forearmR = svgEl("line", { stroke: COLOR.figureDim, "stroke-width": 9, "stroke-linecap": "round" });
    var handR = svgEl("circle", { r: 6, fill: COLOR.figureDim });

    // z-order: far-side limbs first (behind), then torso/head, then near-side
    [thighR, shinR, footR, upperArmR, forearmR, handR,
     torso, neck, head,
     thighL, shinL, footL, upperArmL, forearmL, handL]
      .forEach(function (n) { svg.appendChild(n); });

    function setPose(p) {
      var hip = p.hip;
      var shoulder = pt(hip, p.torsoAngle, lens.torso);
      var neckPt = pt(shoulder, p.neckAngle != null ? p.neckAngle : p.torsoAngle, lens.neck);
      var headPt = pt(neckPt, p.neckAngle != null ? p.neckAngle : p.torsoAngle, lens.headR * 0.9);

      var elbowL = pt(shoulder, p.armL.shoulderAngle, lens.upperArm);
      var wristL = p.armL.wrist || pt(elbowL, p.armL.elbowAngle, lens.forearm);
      var elbowR = pt(shoulder, p.armR.shoulderAngle, lens.upperArm);
      var wristR = p.armR.wrist || pt(elbowR, p.armR.elbowAngle, lens.forearm);

      var kneeL = pt(hip, p.legL.hipAngle, lens.thigh);
      var ankleL = pt(kneeL, p.legL.kneeAngle, lens.shin);
      var kneeR = pt(hip, p.legR.hipAngle, lens.thigh);
      var ankleR = pt(kneeR, p.legR.kneeAngle, lens.shin);

      torso.setAttribute("x1", hip.x); torso.setAttribute("y1", hip.y);
      torso.setAttribute("x2", shoulder.x); torso.setAttribute("y2", shoulder.y);
      neck.setAttribute("x1", shoulder.x); neck.setAttribute("y1", shoulder.y);
      neck.setAttribute("x2", neckPt.x); neck.setAttribute("y2", neckPt.y);
      head.setAttribute("cx", headPt.x); head.setAttribute("cy", headPt.y);

      thighL.setAttribute("x1", hip.x); thighL.setAttribute("y1", hip.y);
      thighL.setAttribute("x2", kneeL.x); thighL.setAttribute("y2", kneeL.y);
      shinL.setAttribute("x1", kneeL.x); shinL.setAttribute("y1", kneeL.y);
      shinL.setAttribute("x2", ankleL.x); shinL.setAttribute("y2", ankleL.y);
      footL.setAttribute("cx", ankleL.x + Math.sin((p.legL.kneeAngle * Math.PI) / 180) * 9);
      footL.setAttribute("cy", ankleL.y + 4);

      thighR.setAttribute("x1", hip.x); thighR.setAttribute("y1", hip.y);
      thighR.setAttribute("x2", kneeR.x); thighR.setAttribute("y2", kneeR.y);
      shinR.setAttribute("x1", kneeR.x); shinR.setAttribute("y1", kneeR.y);
      shinR.setAttribute("x2", ankleR.x); shinR.setAttribute("y2", ankleR.y);
      footR.setAttribute("cx", ankleR.x + Math.sin((p.legR.kneeAngle * Math.PI) / 180) * 9);
      footR.setAttribute("cy", ankleR.y + 4);

      upperArmL.setAttribute("x1", shoulder.x); upperArmL.setAttribute("y1", shoulder.y);
      upperArmL.setAttribute("x2", elbowL.x); upperArmL.setAttribute("y2", elbowL.y);
      forearmL.setAttribute("x1", elbowL.x); forearmL.setAttribute("y1", elbowL.y);
      forearmL.setAttribute("x2", wristL.x); forearmL.setAttribute("y2", wristL.y);
      handL.setAttribute("cx", wristL.x); handL.setAttribute("cy", wristL.y);

      upperArmR.setAttribute("x1", shoulder.x); upperArmR.setAttribute("y1", shoulder.y);
      upperArmR.setAttribute("x2", elbowR.x); upperArmR.setAttribute("y2", elbowR.y);
      forearmR.setAttribute("x1", elbowR.x); forearmR.setAttribute("y1", elbowR.y);
      forearmR.setAttribute("x2", wristR.x); forearmR.setAttribute("y2", wristR.y);
      handR.setAttribute("cx", wristR.x); handR.setAttribute("cy", wristR.y);

      return { hip: hip, shoulder: shoulder, neck: neckPt, head: headPt,
        elbowL: elbowL, wristL: wristL, elbowR: elbowR, wristR: wristR,
        kneeL: kneeL, ankleL: ankleL, kneeR: kneeR, ankleR: ankleR };
    }

    return { setPose: setPose, els: { torso: torso, head: head } };
  }

  function lerpPose(a, b, t) {
    return {
      hip: lerpPt(a.hip, b.hip, t),
      torsoAngle: lerp(a.torsoAngle, b.torsoAngle, t),
      neckAngle: lerp(a.neckAngle != null ? a.neckAngle : a.torsoAngle, b.neckAngle != null ? b.neckAngle : b.torsoAngle, t),
      legL: { hipAngle: lerp(a.legL.hipAngle, b.legL.hipAngle, t), kneeAngle: lerp(a.legL.kneeAngle, b.legL.kneeAngle, t) },
      legR: { hipAngle: lerp(a.legR.hipAngle, b.legR.hipAngle, t), kneeAngle: lerp(a.legR.kneeAngle, b.legR.kneeAngle, t) },
      armL: { shoulderAngle: lerp(a.armL.shoulderAngle, b.armL.shoulderAngle, t), elbowAngle: lerp(a.armL.elbowAngle, b.armL.elbowAngle, t) },
      armR: { shoulderAngle: lerp(a.armR.shoulderAngle, b.armR.shoulderAngle, t), elbowAngle: lerp(a.armR.elbowAngle, b.armR.elbowAngle, t) },
    };
  }

  // ── Per-pattern ready/working keyframes ─────────────────────────────────
  // Each entry: { ready, working, hold } — hold (0-1) is how long, as a
  // fraction of the cycle, the pose pauses at the "working" extreme (a real
  // rep pauses briefly at the squeeze/lockout point).
  function standingLegs(hipA, kneeA) { return { hipAngle: hipA, kneeAngle: kneeA }; }

  // Angle-convention note (this is what was wrong before): 0 = straight
  // DOWN, 180 = straight up. An arm hanging naturally at a standing
  // figure's side is close to 0, not close to 180 — every "resting arm"
  // pose below was previously written near 170-178 (i.e. pointing the arm
  // up alongside the head) instead of near 5-15 (pointing down at the
  // side). Rewritten throughout, verified against real Playwright
  // screenshots this time, not just reasoned about.
  var HANG = { shoulderAngle: 10, elbowAngle: 12 }; // arms relaxed at the sides

  var PATTERN_POSES = {
    squat: {
      ready: { hip: { x: 150, y: 116 }, torsoAngle: 174, legL: standingLegs(8, 8), legR: standingLegs(8, 8), armL: HANG, armR: HANG },
      working: { hip: { x: 146, y: 150 }, torsoAngle: 158, legL: standingLegs(76, 344), legR: standingLegs(76, 344), armL: HANG, armR: HANG },
      hold: 0.08,
    },
    lunge: {
      ready: { hip: { x: 150, y: 116 }, torsoAngle: 175, legL: standingLegs(14, 10), legR: standingLegs(2, 6), armL: HANG, armR: HANG },
      working: { hip: { x: 149, y: 128 }, torsoAngle: 170, legL: standingLegs(58, 300), legR: standingLegs(320, 250), armL: HANG, armR: HANG },
      hold: 0.06,
    },
    hip_hinge: {
      ready: { hip: { x: 150, y: 116 }, torsoAngle: 174, legL: standingLegs(10, 10), legR: standingLegs(10, 10), armL: { shoulderAngle: 8, elbowAngle: 8 }, armR: { shoulderAngle: 8, elbowAngle: 8 } },
      working: { hip: { x: 150, y: 122 }, torsoAngle: 108, legL: standingLegs(26, 26), legR: standingLegs(26, 26), armL: { shoulderAngle: 40, elbowAngle: 40 }, armR: { shoulderAngle: 40, elbowAngle: 40 } },
      hold: 0.05,
    },
    horizontal_push: {
      ready: { hip: { x: 150, y: 140 }, torsoAngle: 270, legL: standingLegs(100, 20), legR: standingLegs(100, 20), armL: { shoulderAngle: 150, elbowAngle: 60 }, armR: { shoulderAngle: 150, elbowAngle: 60 } },
      working: { hip: { x: 150, y: 140 }, torsoAngle: 270, legL: standingLegs(100, 20), legR: standingLegs(100, 20), armL: { shoulderAngle: 176, elbowAngle: 168 }, armR: { shoulderAngle: 176, elbowAngle: 168 } },
      hold: 0.1,
    },
    vertical_push: {
      ready: { hip: { x: 150, y: 116 }, torsoAngle: 176, legL: standingLegs(10, 10), legR: standingLegs(10, 10), armL: { shoulderAngle: 70, elbowAngle: 170 }, armR: { shoulderAngle: 70, elbowAngle: 170 } },
      working: { hip: { x: 150, y: 116 }, torsoAngle: 172, legL: standingLegs(10, 10), legR: standingLegs(10, 10), armL: { shoulderAngle: 178, elbowAngle: 178 }, armR: { shoulderAngle: 178, elbowAngle: 178 } },
      hold: 0.12,
    },
    horizontal_pull: {
      ready: { hip: { x: 150, y: 122 }, torsoAngle: 110, legL: standingLegs(20, 20), legR: standingLegs(20, 20), armL: { shoulderAngle: 45, elbowAngle: 45 }, armR: { shoulderAngle: 45, elbowAngle: 45 } },
      working: { hip: { x: 150, y: 122 }, torsoAngle: 110, legL: standingLegs(20, 20), legR: standingLegs(20, 20), armL: { shoulderAngle: 135, elbowAngle: 225 }, armR: { shoulderAngle: 135, elbowAngle: 225 } },
      hold: 0.14,
    },
    vertical_pull: {
      ready: { hip: { x: 150, y: 120 }, torsoAngle: 176, legL: standingLegs(15, 70), legR: standingLegs(15, 70), armL: { shoulderAngle: 174, elbowAngle: 174 }, armR: { shoulderAngle: 174, elbowAngle: 174 } },
      working: { hip: { x: 150, y: 120 }, torsoAngle: 178, legL: standingLegs(15, 70), legR: standingLegs(15, 70), armL: { shoulderAngle: 25, elbowAngle: 340 }, armR: { shoulderAngle: 25, elbowAngle: 340 } },
      hold: 0.12,
    },
    elbow_flexion: {
      ready: { hip: { x: 150, y: 116 }, torsoAngle: 176, legL: standingLegs(8, 8), legR: standingLegs(8, 8), armL: { shoulderAngle: 10, elbowAngle: 12 }, armR: { shoulderAngle: 10, elbowAngle: 12 } },
      working: { hip: { x: 150, y: 116 }, torsoAngle: 176, legL: standingLegs(8, 8), legR: standingLegs(8, 8), armL: { shoulderAngle: 10, elbowAngle: 172 }, armR: { shoulderAngle: 10, elbowAngle: 172 } },
      hold: 0.14,
    },
    elbow_extension: {
      ready: { hip: { x: 150, y: 116 }, torsoAngle: 172, legL: standingLegs(8, 8), legR: standingLegs(8, 8), armL: { shoulderAngle: 30, elbowAngle: 170 }, armR: { shoulderAngle: 30, elbowAngle: 170 } },
      working: { hip: { x: 150, y: 116 }, torsoAngle: 172, legL: standingLegs(8, 8), legR: standingLegs(8, 8), armL: { shoulderAngle: 30, elbowAngle: 20 }, armR: { shoulderAngle: 30, elbowAngle: 20 } },
      hold: 0.1,
    },
    lateral_raise: {
      ready: { hip: { x: 150, y: 116 }, torsoAngle: 176, legL: standingLegs(8, 8), legR: standingLegs(8, 8), armL: { shoulderAngle: 12, elbowAngle: 15 }, armR: { shoulderAngle: 12, elbowAngle: 15 } },
      working: { hip: { x: 150, y: 116 }, torsoAngle: 176, legL: standingLegs(8, 8), legR: standingLegs(8, 8), armL: { shoulderAngle: 92, elbowAngle: 96 }, armR: { shoulderAngle: 92, elbowAngle: 96 } },
      hold: 0.12,
    },
    calf_raise: {
      ready: { hip: { x: 150, y: 116 }, torsoAngle: 178, legL: standingLegs(8, 8), legR: standingLegs(8, 8), armL: HANG, armR: HANG },
      working: { hip: { x: 150, y: 108 }, torsoAngle: 178, legL: standingLegs(8, 8), legR: standingLegs(8, 8), armL: HANG, armR: HANG },
      hold: 0.16,
    },
    core_isometric: {
      ready: { hip: { x: 150, y: 150 }, torsoAngle: 270, legL: standingLegs(88, 92), legR: standingLegs(92, 88), armL: { shoulderAngle: 20, elbowAngle: 95 }, armR: { shoulderAngle: 20, elbowAngle: 95 } },
      working: { hip: { x: 150, y: 148 }, torsoAngle: 268, legL: standingLegs(88, 92), legR: standingLegs(92, 88), armL: { shoulderAngle: 20, elbowAngle: 95 }, armR: { shoulderAngle: 20, elbowAngle: 95 } },
      hold: 0.7,
    },
    core_flex: {
      ready: { hip: { x: 150, y: 150 }, torsoAngle: 270, legL: standingLegs(60, 300), legR: standingLegs(60, 300), armL: { shoulderAngle: 220, elbowAngle: 250 }, armR: { shoulderAngle: 220, elbowAngle: 250 } },
      working: { hip: { x: 150, y: 150 }, torsoAngle: 240, legL: standingLegs(60, 300), legR: standingLegs(60, 300), armL: { shoulderAngle: 220, elbowAngle: 250 }, armR: { shoulderAngle: 220, elbowAngle: 250 } },
      hold: 0.14,
    },
    core_rotation: {
      ready: { hip: { x: 150, y: 122 }, torsoAngle: 176, legL: standingLegs(15, 70), legR: standingLegs(15, 70), armL: { shoulderAngle: 105, elbowAngle: 60 }, armR: { shoulderAngle: 105, elbowAngle: 60 } },
      working: { hip: { x: 150, y: 122 }, torsoAngle: 154, legL: standingLegs(15, 70), legR: standingLegs(15, 70), armL: { shoulderAngle: 105, elbowAngle: 60 }, armR: { shoulderAngle: 105, elbowAngle: 60 } },
      hold: 0.1,
    },
    // Leg press / hack squat / leg extension — a distinct machine position,
    // not a standing squat, even though it shares the same knee/hip flexion
    // idea. Selected by support === "seated" in createInstance below.
    squat_seated: {
      ready: { hip: { x: 90, y: 110 }, torsoAngle: 220, legL: standingLegs(95, 15), legR: standingLegs(95, 15), armL: { shoulderAngle: 230, elbowAngle: 230 }, armR: { shoulderAngle: 230, elbowAngle: 230 } },
      working: { hip: { x: 90, y: 110 }, torsoAngle: 220, legL: standingLegs(95, 70), legR: standingLegs(95, 70), armL: { shoulderAngle: 230, elbowAngle: 230 }, armR: { shoulderAngle: 230, elbowAngle: 230 } },
      hold: 0.1,
    },
    cardio_generic: {
      ready: { hip: { x: 150, y: 116 }, torsoAngle: 176, legL: standingLegs(350, 300), legR: standingLegs(20, 330), armL: { shoulderAngle: 80, elbowAngle: 90 }, armR: { shoulderAngle: 280, elbowAngle: 260 } },
      working: { hip: { x: 150, y: 108 }, torsoAngle: 170, legL: standingLegs(60, 300), legR: standingLegs(330, 30), armL: { shoulderAngle: 200, elbowAngle: 260 }, armR: { shoulderAngle: 80, elbowAngle: 90 } },
      hold: 0,
    },
  };
  PATTERN_POSES.full_body_generic = PATTERN_POSES.cardio_generic;

  // ── Equipment (drawn behind/around the figure, positioned from the FK
  // points the skeleton returns each frame) ───────────────────────────────
  function buildEquipment(svg, params) {
    var g = svgEl("g");
    svg.insertBefore(g, svg.firstChild); // behind the (already-appended) skeleton

    var nodes = {};
    function add(tag, attrs) { var n = svgEl(tag, attrs); g.appendChild(n); return n; }

    if (params.support === "bench-flat" || params.support === "bench-incline" || params.support === "bench-decline") {
      add("rect", { x: 55, y: 142, width: 150, height: 10, rx: 4, fill: COLOR.bench });
      add("rect", { x: 66, y: 152, width: 6, height: 30, fill: COLOR.bench, opacity: 0.85 });
      add("rect", { x: 178, y: 152, width: 6, height: 30, fill: COLOR.bench, opacity: 0.85 });
    }
    if (params.support === "seated") {
      add("rect", { x: 130, y: 150, width: 40, height: 10, rx: 3, fill: COLOR.bench });
      add("rect", { x: 133, y: 160, width: 6, height: 22, fill: COLOR.bench, opacity: 0.85 });
      add("rect", { x: 161, y: 160, width: 6, height: 22, fill: COLOR.bench, opacity: 0.85 });
    }
    add("line", { x1: 20, y1: 182, x2: 280, y2: 182, stroke: COLOR.floor, "stroke-width": 2 });

    if (params.implement === "bar" || (params.pattern === "vertical_pull" && params.implement !== "cable")) {
      nodes.overheadBar = add("line", { x1: 90, y1: 40, x2: 210, y2: 40, stroke: COLOR.steel, "stroke-width": 6, "stroke-linecap": "round" });
      add("line", { x1: 90, y1: 40, x2: 90, y2: 20, stroke: COLOR.bench, "stroke-width": 4 });
      add("line", { x1: 210, y1: 40, x2: 210, y2: 20, stroke: COLOR.bench, "stroke-width": 4 });
    }
    if (params.implement === "cable") {
      var top = params.pattern === "vertical_pull" ? 30 : 30;
      add("rect", { x: 216, y: top, width: 8, height: 130, fill: COLOR.bench, opacity: 0.7 });
      nodes.cable = add("line", { stroke: COLOR.figureDim, "stroke-width": 2 });
      nodes.pulley = add("circle", { cx: 220, cy: top, r: 6, fill: COLOR.bench });
    }

    return { g: g, nodes: nodes };
  }

  function barbellAt(g, x, y) {
    var el1 = svgEl("line", { x1: x - 38, y1: y, x2: x + 16, y2: y, stroke: COLOR.steel, "stroke-width": 6, "stroke-linecap": "round" });
    var farRing = svgEl("circle", { cx: x - 34, cy: y, r: 13, fill: COLOR.figureDim, stroke: COLOR.dark, "stroke-width": 2, "stroke-opacity": 0.5 });
    var nearRing = svgEl("circle", { cx: x + 10, cy: y, r: 18, fill: COLOR.accent, stroke: COLOR.dark, "stroke-width": 2.5, "stroke-opacity": 0.5 });
    var nearHub = svgEl("circle", { cx: x + 10, cy: y, r: 5, fill: COLOR.dark, opacity: 0.55 });
    g.appendChild(el1); g.appendChild(farRing); g.appendChild(nearRing); g.appendChild(nearHub);
    return { line: el1, farRing: farRing, nearRing: nearRing, nearHub: nearHub,
      reposition: function (nx, ny) {
        el1.setAttribute("x1", nx - 38); el1.setAttribute("y1", ny);
        el1.setAttribute("x2", nx + 16); el1.setAttribute("y2", ny);
        farRing.setAttribute("cx", nx - 34); farRing.setAttribute("cy", ny);
        nearRing.setAttribute("cx", nx + 10); nearRing.setAttribute("cy", ny);
        nearHub.setAttribute("cx", nx + 10); nearHub.setAttribute("cy", ny);
      } };
  }

  function dumbbellAt(g, x, y) {
    var bar = svgEl("line", { x1: x - 8, y1: y, x2: x + 8, y2: y, stroke: COLOR.steel, "stroke-width": 3 });
    var c1 = svgEl("circle", { cx: x - 8, cy: y, r: 6, fill: COLOR.accent });
    var c2 = svgEl("circle", { cx: x + 8, cy: y, r: 6, fill: COLOR.accent });
    g.appendChild(bar); g.appendChild(c1); g.appendChild(c2);
    return { reposition: function (nx, ny) {
      bar.setAttribute("x1", nx - 8); bar.setAttribute("y1", ny); bar.setAttribute("x2", nx + 8); bar.setAttribute("y2", ny);
      c1.setAttribute("cx", nx - 8); c1.setAttribute("cy", ny);
      c2.setAttribute("cx", nx + 8); c2.setAttribute("cy", ny);
    } };
  }

  function kettlebellAt(g, x, y) {
    var body = svgEl("circle", { cx: x, cy: y + 4, r: 9, fill: COLOR.accent });
    var handle = svgEl("path", { fill: "none", stroke: COLOR.steel, "stroke-width": 3 });
    function setHandle(nx, ny) {
      handle.setAttribute("d", "M " + (nx - 5) + " " + (ny - 2) + " Q " + nx + " " + (ny - 10) + " " + (nx + 5) + " " + (ny - 2));
    }
    setHandle(x, y);
    g.appendChild(body); g.appendChild(handle);
    return { reposition: function (nx, ny) { body.setAttribute("cx", nx); body.setAttribute("cy", ny + 4); setHandle(nx, ny); } };
  }

  // Fixed (non-arm-driven) barbell resting across the shoulders/back — used
  // for barbell squats, where the hands only steady the bar rather than
  // carry it through the rep, so animating it off the wrist (as bench/curl
  // do) would be wrong.
  function shoulderBarAt(g, x, y) {
    var line = svgEl("line", { x1: x - 34, y1: y, x2: x + 34, y2: y, stroke: COLOR.steel, "stroke-width": 7, "stroke-linecap": "round" });
    var p1 = svgEl("circle", { cx: x - 30, cy: y, r: 10, fill: COLOR.accent, stroke: COLOR.dark, "stroke-width": 2, "stroke-opacity": 0.5 });
    var p2 = svgEl("circle", { cx: x + 30, cy: y, r: 10, fill: COLOR.accent, stroke: COLOR.dark, "stroke-width": 2, "stroke-opacity": 0.5 });
    g.appendChild(line); g.appendChild(p1); g.appendChild(p2);
    return { reposition: function (nx, ny) {
      line.setAttribute("x1", nx - 34); line.setAttribute("y1", ny); line.setAttribute("x2", nx + 34); line.setAttribute("y2", ny);
      p1.setAttribute("cx", nx - 30); p1.setAttribute("cy", ny);
      p2.setAttribute("cx", nx + 30); p2.setAttribute("cy", ny);
    } };
  }

  // Seated leg-machine platform (leg press / hack squat / leg extension) —
  // these are NOT the same exercise as a standing squat and must not render
  // identically to one, even though they share the "squat" knee/hip pattern.
  function legMachineAt(g) {
    var add_ = function (tag, attrs) { var n = svgEl(tag, attrs); g.appendChild(n); return n; };
    add_("rect", { x: 70, y: 150, width: 46, height: 10, rx: 3, fill: COLOR.bench }); // seat
    add_("rect", { x: 70, y: 70, width: 10, height: 90, rx: 3, fill: COLOR.bench, opacity: 0.85 }); // backrest
    add_("rect", { x: 190, y: 60, width: 10, height: 100, rx: 3, fill: COLOR.bench, opacity: 0.85 }); // footplate frame
    add_("rect", { x: 170, y: 55, width: 46, height: 10, rx: 3, fill: COLOR.steel, opacity: 0.9 }); // footplate
  }

  // ── One playing demo instance ────────────────────────────────────────────
  // This is where deriveParams()'s stance/support/implement actually change
  // what gets drawn — previously those were computed and never consumed, so
  // e.g. every squat-pattern exercise rendered byte-identical regardless of
  // being a barbell back squat, a bodyweight squat, or a seated leg press.
  function createInstance(svg, exercise) {
    var params = deriveParams(exercise);

    // Leg press / hack squat / leg extension are a different machine
    // position, not a standing squat, even though the knee/hip motion is
    // the same pattern — swap the whole pose set, not just the equipment.
    var useSeatedSquat = params.pattern === "squat" && params.support === "seated";
    var poseKey = useSeatedSquat ? "squat_seated" : params.pattern;
    var poses = PATTERN_POSES[poseKey] || PATTERN_POSES.full_body_generic;

    var skeleton = buildSkeleton(svg);
    var equip = buildEquipment(svg, params);
    if (useSeatedSquat) legMachineAt(equip.g);

    // A barbell squat holds the bar fixed across the shoulders — it doesn't
    // travel with the hands through the rep the way a press or curl does,
    // so it's a separate shoulder-anchored prop, not a wrist-anchored one.
    var shoulderProp = (params.pattern === "squat" && !useSeatedSquat && params.implement === "barbell")
      ? { type: "shoulderBar", inst: null } : null;

    var handProp = null;
    if (!useSeatedSquat && !shoulderProp) {
      if (params.implement === "barbell") handProp = { type: "barbell" };
      else if (params.implement === "dumbbells") handProp = { type: "dumbbell" };
      else if (params.implement === "kettlebell") handProp = { type: "kettlebell" };
      else if (params.implement === "none" && (params.pattern === "elbow_flexion" || params.pattern === "lateral_raise" || params.pattern === "squat")) {
        // Unspecified implement on a pattern that's visually empty-handed
        // otherwise reads as "holding nothing" with no cue at all — default
        // to a light dumbbell rather than leave it ambiguous. Genuinely
        // bodyweight-only names (push-up, pull-up, bodyweight squat) still
        // show nothing: "none" here only fires for implement-ambiguous ones.
        handProp = /bodyweight|push-up|push up|pull-up|pull up|chin-up|chin up|air squat/i.test(exercise && exercise.name || "") ? null : { type: "dumbbell" };
      }
    }

    function propAt(type, g, x, y) {
      if (type === "barbell") return barbellAt(g, x, y);
      if (type === "dumbbell") return dumbbellAt(g, x, y);
      if (type === "kettlebell") return kettlebellAt(g, x, y);
      return shoulderBarAt(g, x, y);
    }

    function frame(t) {
      var pose = lerpPose(poses.ready, poses.working, t);
      var points = skeleton.setPose(pose);

      if (equip.nodes.cable) {
        equip.nodes.cable.setAttribute("x1", equip.nodes.pulley.getAttribute("cx"));
        equip.nodes.cable.setAttribute("y1", equip.nodes.pulley.getAttribute("cy"));
        equip.nodes.cable.setAttribute("x2", points.wristL.x);
        equip.nodes.cable.setAttribute("y2", points.wristL.y);
      }
      if (handProp) {
        if (!handProp.inst) handProp.inst = propAt(handProp.type, equip.g, points.wristL.x, points.wristL.y);
        handProp.inst.reposition(points.wristL.x, points.wristL.y);
      }
      if (shoulderProp) {
        if (!shoulderProp.inst) shoulderProp.inst = propAt("shoulderBar", equip.g, points.shoulder.x, points.shoulder.y);
        shoulderProp.inst.reposition(points.shoulder.x, points.shoulder.y);
      }
    }

    frame(0);
    return { frame: frame, hold: poses.hold || 0 };
  }

  // ── Shared animation loop across every mounted instance ─────────────────
  var REGISTRY = new Map();
  var rafStarted = false;
  var CYCLE_MS = 1700;

  function tickAll(ts) {
    REGISTRY.forEach(function (inst, el) {
      if (!el.isConnected) { REGISTRY.delete(el); return; }
      if (!inst.__start) inst.__start = ts;
      var holdMs = (inst.hold || 0) * CYCLE_MS;
      var total = CYCLE_MS + holdMs;
      var elapsed = (ts - inst.__start) % total;
      var t;
      if (elapsed < CYCLE_MS) {
        var p = elapsed / CYCLE_MS;
        t = p < 0.5 ? easeInOutSine(p * 2) : 1 - easeInOutSine((p - 0.5) * 2);
      } else {
        t = 1;
      }
      inst.frame(t);
    });
    requestAnimationFrame(tickAll);
  }

  function mount(container) {
    var svg = container.querySelector ? container.querySelector("svg.fc-demo-rig") : null;
    if (!svg) return;
    var exerciseJson = container.getAttribute("data-exercise");
    var exercise;
    try { exercise = JSON.parse(exerciseJson || "{}"); } catch (e) { exercise = {}; }
    var inst = createInstance(svg, exercise);
    REGISTRY.set(svg, inst);
    if (!rafStarted) { rafStarted = true; requestAnimationFrame(tickAll); }
  }

  // Auto-mount anything already in the DOM plus anything inserted later —
  // callers just insert the HTML from renderDemo(); they don't need to
  // remember to call mount() themselves.
  function autoMountScan(root) {
    var list = (root || document).querySelectorAll(".fc-demo[data-fc-pending]");
    for (var i = 0; i < list.length; i++) {
      list[i].removeAttribute("data-fc-pending");
      mount(list[i]);
    }
  }
  if (typeof MutationObserver !== "undefined") {
    new MutationObserver(function (muts) {
      for (var i = 0; i < muts.length; i++) {
        for (var j = 0; j < muts[i].addedNodes.length; j++) {
          var n = muts[i].addedNodes[j];
          if (n.nodeType === 1) {
            if (n.matches && n.matches(".fc-demo[data-fc-pending]")) { n.removeAttribute("data-fc-pending"); mount(n); }
            else if (n.querySelectorAll) autoMountScan(n);
          }
        }
      }
    }).observe(document.documentElement, { childList: true, subtree: true });
  }

  function escapeAttr(s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/"/g, "&quot;"); }

  function renderDemo(exercise, opts) {
    opts = opts || {};
    var size = opts.size || "hero"; // "hero" | "thumb"
    var viewBox = "0 0 300 190";
    var minimalExercise = {
      name: exercise && exercise.name,
      movement_pattern: exercise && exercise.movement_pattern,
    };
    var json = escapeAttr(JSON.stringify(minimalExercise));
    var cls = size === "thumb" ? "fc-demo fc-demo-thumb" : "fc-demo fc-demo-hero";
    return (
      '<div class="' + cls + '" data-fc-pending data-exercise="' + json + '">' +
      '<svg class="fc-demo-rig" viewBox="' + viewBox + '" preserveAspectRatio="xMidYMid meet" aria-hidden="true"></svg>' +
      "</div>"
    );
  }

  window.FCDemo = {
    PATTERNS: PATTERNS,
    renderDemo: renderDemo,
    motionParams: deriveParams,
    mount: mount,
    // QA-only: set a mounted instance to an exact t (0..1), bypassing the
    // shared rAF clock, so visual review isn't at the mercy of wall-clock
    // timing across many cards. Not used by the app itself.
    _debugSetFrame: function (svg, t) {
      var inst = REGISTRY.get(svg);
      if (inst) inst.frame(t);
    },
  };
})();
