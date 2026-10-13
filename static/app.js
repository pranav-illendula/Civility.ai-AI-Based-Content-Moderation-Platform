/* ═══════════════════════════════════════════════
   CIVILITY AI — Frontend Logic
   Agentica 2.0 Hackathon · Team 34
═══════════════════════════════════════════════ */

const API_URL = "/api/analyze";

// ── DOM References ────────────────────────────
const $  = id => document.getElementById(id);
const dropZone     = $("dropZone");
const fileInput    = $("fileInput");
const filePreview  = $("filePreview");
const fpThumb      = $("fpThumb");
const fpName       = $("fpName");
const fpMeta       = $("fpMeta");
const fpRemove     = $("fpRemove");
const analyzeBtn   = $("analyzeBtn");
const uploadPanel  = $("uploadPanel");
const loadingPanel = $("loadingPanel");
const resultsPanel = $("resultsPanel");
const loaderStep   = $("loaderStep");
const loaderFill   = $("loaderFill");
const errorToast   = $("errorToast");
const errorMsg     = $("errorMsg");
const errorClose   = $("errorClose");
const jsonToggle   = $("jsonToggle");
const jsonBody     = $("jsonBody");
const jtChevron    = $("jtChevron");
const jsonPre      = $("jsonPre");
const jsonCopy     = $("jsonCopy");
const btnReset     = $("btnReset");

let selectedFile = null;
let loadingTimer = null;

/* ══════════════════════════════════════════════
   FILE HANDLING
══════════════════════════════════════════════ */

// Drag & Drop
dropZone.addEventListener("dragover", e => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", e => {
  if (!dropZone.contains(e.relatedTarget)) {
    dropZone.classList.remove("drag-over");
  }
});

dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) handleFileSelect(file);
});

dropZone.addEventListener("click", e => {
  if (e.target !== fileInput) fileInput.click();
});

fileInput.addEventListener("change", e => {
  if (e.target.files[0]) handleFileSelect(e.target.files[0]);
});

fpRemove.addEventListener("click", e => {
  e.stopPropagation();
  clearFile();
});

function handleFileSelect(file) {
  const allowedTypes = [
    "image/jpeg", "image/jpg", "image/png", "image/webp",
    "video/mp4", "video/quicktime"
  ];
  const allowedExts = [".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov"];
  const maxSize = 50 * 1024 * 1024;

  // Validate by MIME or extension
  const ext = "." + file.name.split(".").pop().toLowerCase();
  if (!allowedTypes.includes(file.type) && !allowedExts.includes(ext)) {
    showError(`Unsupported file type: "${file.type || ext}". Please upload JPG, PNG, WebP, or MP4.`);
    return;
  }

  if (file.size > maxSize) {
    showError(`File is too large (${formatSize(file.size)}). Maximum allowed size is 50 MB.`);
    return;
  }

  selectedFile = file;

  // Build thumbnail
  fpThumb.innerHTML = "";
  if (file.type.startsWith("image/")) {
    const img = document.createElement("img");
    img.src = URL.createObjectURL(file);
    img.onload = () => URL.revokeObjectURL(img.src);
    fpThumb.appendChild(img);
  } else {
    fpThumb.textContent = "🎬";
  }

  fpName.textContent = file.name;
  fpMeta.textContent = `${formatSize(file.size)} · ${file.type || ext}`;

  filePreview.style.display = "flex";
  analyzeBtn.disabled = false;
}

function clearFile() {
  selectedFile = null;
  fileInput.value = "";
  filePreview.style.display = "none";
  analyzeBtn.disabled = true;
}

function formatSize(bytes) {
  if (bytes < 1024)       return bytes + " B";
  if (bytes < 1048576)    return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1048576).toFixed(2) + " MB";
}

/* ══════════════════════════════════════════════
   ANALYSIS FLOW
══════════════════════════════════════════════ */

analyzeBtn.addEventListener("click", runAnalysis);

async function runAnalysis() {
  if (!selectedFile) return;

  showPanel("loading");
  startLoadingAnimation();

  try {
    const formData = new FormData();
    formData.append("file", selectedFile);

    setStep("Uploading content...", 15);

    const response = await fetch(API_URL, {
      method: "POST",
      body: formData,
    });

    setStep("Running AI analysis...", 70);

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || `Server error ${response.status}`);
    }

    setStep("Compiling results...", 95);
    await sleep(400);
    setStep("Done!", 100);
    await sleep(300);

    renderResults(data);
    showPanel("results");

    // Smooth scroll to results
    window.scrollTo({ top: 0, behavior: "smooth" });

  } catch (err) {
    showPanel("upload");
    showError(err.message || "An unexpected error occurred. Please try again.");
  }
}

/* ── Loading helpers ────────────────────────── */

function startLoadingAnimation() {
  const steps = [
    { text: "Uploading content...",           pct: 15 },
    { text: "Reading file metadata...",       pct: 28 },
    { text: "Extracting visual content...",   pct: 42 },
    { text: "Sending to Gemini AI...",        pct: 58 },
    { text: "Analyzing for harmful content...", pct: 72 },
    { text: "Classifying categories...",      pct: 84 },
    { text: "Finalizing moderation report...", pct: 91 },
  ];
  let i = 0;
  loadingTimer = setInterval(() => {
    if (i < steps.length) {
      setStep(steps[i].text, steps[i].pct);
      i++;
    }
  }, 2000);
}

function setStep(text, pct) {
  loaderStep.textContent = text;
  loaderFill.style.width = pct + "%";
}

function stopLoadingAnimation() {
  if (loadingTimer) { clearInterval(loadingTimer); loadingTimer = null; }
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

/* ── Panel switcher ─────────────────────────── */

function showPanel(name) {
  stopLoadingAnimation();
  uploadPanel.style.display  = name === "upload"  ? "block" : "none";
  loadingPanel.style.display = name === "loading" ? "block" : "none";
  resultsPanel.style.display = name === "results" ? "block" : "none";
}

/* ══════════════════════════════════════════════
   RESULTS RENDERING
══════════════════════════════════════════════ */

function renderResults(data) {
  renderVerdict(data);
  renderDescription(data);
  renderClassification(data);
  renderEmotions(data);
  renderSceneElements(data);
  renderRiskReasoning(data);
  renderJSON(data);
}

function renderVerdict(data) {
  const verdict   = (data.final_verdict   || "REVIEW NEEDED").toUpperCase().trim();
  const severity  = (data.severity_level  || "none").toLowerCase();
  const confidence = data.confidence_score != null
    ? Math.round(data.confidence_score * 100) + "% confidence"
    : "";

  const banner    = $("verdictBanner");
  const vbIcon    = $("vbIcon");
  const vbText    = $("vbText");
  const vbSev     = $("vbSeverity");
  const vbConf    = $("vbConfidence");

  let cls, icon;
  if (verdict.includes("SAFE"))   { cls = "safe";    icon = "✅"; }
  else if (verdict.includes("BLOCK")) { cls = "blocked"; icon = "🚫"; }
  else if (verdict.includes("FLAG"))  { cls = "flagged"; icon = "⚠️"; }
  else                                { cls = "review";  icon = "🔍"; }

  banner.className   = "verdict-banner " + cls;
  vbIcon.textContent = icon;
  vbText.textContent = verdict;
  vbSev.textContent  = "Severity: " + severity.toUpperCase();
  vbConf.textContent = confidence;

  if (data.frame_count) {
    vbConf.textContent += (confidence ? " · " : "") + `${data.frame_count} frames analyzed`;
  }
}

function renderDescription(data) {
  $("rDesc").textContent = data.general_description || "No description available.";
}

function renderClassification(data) {
  const cc = data.content_classification || {};
  const items = [
    { key: "nsfw",            label: "NSFW / Adult Content" },
    { key: "violence",        label: "Violence / Gore" },
    { key: "bullying",        label: "Bullying / Harassment" },
    { key: "hate_speech",     label: "Hate Speech" },
    { key: "illegal_content", label: "Illegal Content" },
  ];

  $("classList").innerHTML = items.map(({ key, label }) => {
    const flagged = cc[key] === true;
    return `
      <div class="ci ${flagged ? "flagged" : "clean"}">
        <div class="ci-left">
          <div class="ci-dot"></div>
          <span class="ci-label">${label}</span>
        </div>
        <span class="ci-status">${flagged ? "DETECTED" : "CLEAR"}</span>
      </div>`;
  }).join("");
}

function renderEmotions(data) {
  const emotions = data.emotions_detected || [];
  $("emotionCloud").innerHTML = emotions.length
    ? emotions.map(e => `<span class="tag emotion">${capitalize(e)}</span>`).join("")
    : `<span class="tag-empty">No emotions detected</span>`;
}

function renderSceneElements(data) {
  const scene = data.scene_elements || [];
  $("sceneCloud").innerHTML = scene.length
    ? scene.map(s => `<span class="tag">${capitalize(s)}</span>`).join("")
    : `<span class="tag-empty">No scene elements identified</span>`;
}

function renderRiskReasoning(data) {
  $("rRisk").textContent = data.risk_reasoning || "No risk reasoning provided.";
}

function renderJSON(data) {
  // Exclude raw_ai_response from display
  const clean = Object.fromEntries(
    Object.entries(data).filter(([k]) => k !== "raw_ai_response")
  );
  jsonPre.textContent = JSON.stringify(clean, null, 2);
}

function capitalize(str) {
  return str ? str.charAt(0).toUpperCase() + str.slice(1).toLowerCase() : str;
}

/* ══════════════════════════════════════════════
   JSON TOGGLE & COPY
══════════════════════════════════════════════ */

jsonToggle.addEventListener("click", () => {
  const isOpen = jsonBody.style.display !== "none";
  jsonBody.style.display = isOpen ? "none" : "block";
  jtChevron.classList.toggle("open", !isOpen);
});

jsonCopy.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(jsonPre.textContent);
    jsonCopy.textContent = "Copied!";
    setTimeout(() => { jsonCopy.textContent = "Copy JSON"; }, 2000);
  } catch {
    jsonCopy.textContent = "Failed";
    setTimeout(() => { jsonCopy.textContent = "Copy JSON"; }, 2000);
  }
});

/* ══════════════════════════════════════════════
   RESET
══════════════════════════════════════════════ */

btnReset.addEventListener("click", () => {
  clearFile();
  // Reset JSON panel state
  jsonBody.style.display = "none";
  jtChevron.classList.remove("open");
  showPanel("upload");
});

/* ══════════════════════════════════════════════
   ERROR TOAST
══════════════════════════════════════════════ */

let errorTimeout = null;

function showError(msg) {
  if (errorTimeout) clearTimeout(errorTimeout);
  errorMsg.textContent = msg;
  errorToast.style.display = "flex";
  errorTimeout = setTimeout(hideError, 7000);
}

function hideError() {
  errorToast.style.display = "none";
  if (errorTimeout) { clearTimeout(errorTimeout); errorTimeout = null; }
}

errorClose.addEventListener("click", hideError);
