// Load MediaPipe from CDN (using global scope for non-module loading).
// The vision_bundle.js UMD build attaches everything under a `Vision`
// namespace global (window.Vision.PoseLandmarker etc.), not flat window.*
// globals — this was the actual cause of "camera failed to start" (the old
// code read window.PoseLandmarker directly, which never existed).
const PoseLandmarker = window.Vision?.PoseLandmarker;
const FilesetResolver = window.Vision?.FilesetResolver;

const LM = {
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

const POSE_EDGES = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [24, 26], [26, 28],
];

function angleDeg(a, b, c) {
  const v1x = a.x - b.x;
  const v1y = a.y - b.y;
  const v2x = c.x - b.x;
  const v2y = c.y - b.y;
  const dot = v1x * v2x + v1y * v2y;
  const mag = Math.hypot(v1x, v1y) * Math.hypot(v2x, v2y) || 1e-6;
  const cos = Math.min(1, Math.max(-1, dot / mag));
  return (Math.acos(cos) * 180) / Math.PI;
}

let cached = null;
let creating = null;

async function getPoseLandmarker() {
  if (cached) return cached;
  if (creating) return creating;

  creating = (async () => {
    const vision = await FilesetResolver.forVisionTasks(
      "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm",
    );
    cached = await PoseLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath:
          "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
        delegate: "GPU",
      },
      runningMode: "VIDEO",
      numPoses: 1,
      minPoseDetectionConfidence: 0.5,
      minPosePresenceConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });
    return cached;
  })();

  return creating;
}

// Export to global scope for other scripts
window.GhostPose = {
  getPoseLandmarker,
  POSE_EDGES,
  LM,
  angleDeg
};
