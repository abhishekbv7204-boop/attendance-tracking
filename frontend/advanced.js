const API_BASE = window.location.origin;
const SESSION_KEY = "attendance_user";
const SUBJECTS = [
  "Artificial Intelligence",
  "Computer Networks",
  "Data Structures",
  "Database Systems",
  "Machine Learning",
  "Operating Systems",
  "Software Engineering"
];
const DEFAULT_COLLEGES = [
  "Ballari Institute of Technology and Management",
  "BMS College of Engineering",
  "Christ University",
  "Dayananda Sagar College of Engineering",
  "Indian Institute of Science",
  "National Institute of Technology Trichy",
  "PES University",
  "Ramaiah Institute of Technology",
  "RV College of Engineering",
  "Visvesvaraya Technological University"
];

const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const registerImageInput = document.getElementById("register_image");
const loginImageInput = document.getElementById("login_image");
const capturedPreview = document.getElementById("captured_preview");
let streamRef;
let chartRef;
let capturedImageData = null;

async function startCamera() {
  if (!video || !navigator.mediaDevices?.getUserMedia) return;

  try {
    streamRef = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "user",
        width: { ideal: 1280 },
        height: { ideal: 720 },
        frameRate: { ideal: 24 }
      },
      audio: false
    });
    video.srcObject = streamRef;
    await video.play();
  } catch (error) {
    setStatus("camera_status", "Camera access failed. Check browser permissions.", true);
    console.error(error);
  }
}

function stopCamera() {
  if (!streamRef) return;
  streamRef.getTracks().forEach(track => track.stop());
  streamRef = null;
}

window.addEventListener("beforeunload", stopCamera);

function captureImage() {
  if (!video || !canvas || !video.videoWidth) {
    return null;
  }

  const context = canvas.getContext("2d");
  const width = video.videoWidth;
  const height = video.videoHeight;
  canvas.width = width;
  canvas.height = height;
  context.clearRect(0, 0, width, height);
  context.drawImage(video, 0, 0, width, height);
  return canvas.toDataURL("image/jpeg", 0.95).split(",")[1];
}

function captureForPreview(mode) {
  const image = captureImage();
  if (!image) {
    setStatus("camera_status", "Camera frame not available yet. Wait a moment and try again.", true);
    return;
  }

  capturedImageData = image;
  if (capturedPreview) {
    capturedPreview.src = `data:image/jpeg;base64,${image}`;
    capturedPreview.classList.add("visible");
  }
  setStatus("camera_status", `Photo captured for ${mode}. You can now continue.`, false);
}

function clearCapturedImage() {
  capturedImageData = null;
  if (capturedPreview) {
    capturedPreview.removeAttribute("src");
    capturedPreview.classList.remove("visible");
  }
  if (registerImageInput) registerImageInput.value = "";
  if (loginImageInput) loginImageInput.value = "";
  setStatus("camera_status", "Capture cleared. Take a new photo.", false);
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      resolve(result.includes(",") ? result.split(",")[1] : result);
    };
    reader.onerror = () => reject(new Error("Could not read the selected image."));
    reader.readAsDataURL(file);
  });
}

async function getFaceImage(inputId) {
  if (capturedImageData) {
    return capturedImageData;
  }

  const fileInput = document.getElementById(inputId);
  const file = fileInput?.files?.[0];
  if (file) {
    setStatus("camera_status", "Using uploaded image instead of camera capture.", false);
    return readFileAsBase64(file);
  }

  setStatus("camera_status", "Camera is not ready. Upload a clear face photo instead.", true);
  return null;
}

function bindFileInput(input, label) {
  if (!input) return;
  input.addEventListener("change", () => {
    const file = input.files?.[0];
    if (file) {
      capturedImageData = null;
      if (capturedPreview) {
        capturedPreview.removeAttribute("src");
        capturedPreview.classList.remove("visible");
      }
      setStatus("camera_status", `${label} selected: ${file.name}`, false);
    }
  });
}

function setStatus(id, message, isError = false) {
  const element = document.getElementById(id);
  if (!element) return;
  element.textContent = message;
  element.classList.toggle("error", isError);
  element.classList.toggle("success", !isError);
}

function getValue(id) {
  return document.getElementById(id)?.value.trim() || "";
}

function setSession(user) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(user));
}

function getSession() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY) || "null");
  } catch {
    return null;
  }
}

function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

async function fetchJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || "Request failed");
  }
  return data;
}

function goRegister() {
  window.location.href = "register.html";
}

function goLogin() {
  window.location.href = "index.html";
}

async function loadColleges() {
  const collegeInput = document.getElementById("college");
  const collegeOptions = document.getElementById("college_options");
  if (!collegeInput || !collegeOptions) return;

  const renderColleges = (colleges) => {
    const uniqueColleges = [...new Set(colleges)].sort((a, b) => a.localeCompare(b));
    collegeOptions.innerHTML = uniqueColleges
      .map(college => `<option value="${college}"></option>`)
      .join("");
  };

  try {
    const colleges = await fetchJson("/colleges");
    renderColleges(colleges.length ? colleges : DEFAULT_COLLEGES);
  } catch (error) {
    renderColleges(DEFAULT_COLLEGES);
    setStatus("register_status", "Loaded local college list.", false);
  }
}

function populateSubjectList() {
  const list = document.getElementById("subject_options");
  if (!list) return;
  list.innerHTML = SUBJECTS.map(subject => `<option value="${subject}"></option>`).join("");
}

async function register() {
  const image = await getFaceImage("register_image");
  if (!image) return;

  const payload = {
    usn: getValue("usn"),
    full_name: getValue("full_name"),
    dob: getValue("dob"),
    email: getValue("email"),
    college: getValue("college"),
    image
  };

  if (!payload.usn || !payload.full_name || !payload.dob || !payload.email || !payload.college) {
    setStatus("register_status", "Complete every field before registering.", true);
    return;
  }

  try {
    const data = await fetchJson("/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    setStatus("register_status", `${data.message} Use the same position and lighting when logging in.`, false);
    setTimeout(() => goLogin(), 900);
  } catch (error) {
    setStatus("register_status", error.message, true);
  }
}

async function login() {
  const image = await getFaceImage("login_image");
  if (!image) return;

  const payload = {
    usn: getValue("login_usn"),
    dob: getValue("login_dob"),
    email: getValue("login_email"),
    image
  };

  if (!payload.usn || !payload.dob || !payload.email) {
    setStatus("login_status", "Enter your USN, DOB, and email first.", true);
    return;
  }

  try {
    const data = await fetchJson("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    setSession(data.user);
    setStatus("login_status", `${data.message} Match score ${data.match_score}.`, false);
    setTimeout(() => {
      window.location.href = "dashboard.html";
    }, 700);
  } catch (error) {
    setStatus("login_status", error.message, true);
  }
}

function logout() {
  clearSession();
  window.location.href = "index.html";
}

function renderStats(stats) {
  const mappings = {
    total_classes: stats.total_classes,
    today_classes: stats.today_classes,
    tracked_subjects: stats.tracked_subjects,
    last_updated: new Date(stats.last_updated).toLocaleString()
  };

  Object.entries(mappings).forEach(([id, value]) => {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  });
}

function renderProfile(user) {
  const profileName = document.getElementById("profile_name");
  const profileMeta = document.getElementById("profile_meta");
  const userBadge = document.getElementById("user_badge");

  if (profileName) profileName.textContent = user.full_name;
  if (profileMeta) profileMeta.textContent = `${user.usn} - ${user.college}`;
  if (userBadge) {
    userBadge.textContent = user.full_name
      .split(" ")
      .map(part => part[0])
      .join("")
      .slice(0, 2);
  }
}

function renderTable(records) {
  const table = document.getElementById("attendance_rows");
  if (!table) return;

  if (!records.length) {
    table.innerHTML = '<tr><td colspan="4">No attendance records yet.</td></tr>';
    return;
  }

  table.innerHTML = records.map(record => `
    <tr>
      <td>${record.subject}</td>
      <td>${record.attendance_date}</td>
      <td>${record.status}</td>
      <td>${new Date(record.marked_at).toLocaleString()}</td>
    </tr>
  `).join("");
}

function renderChart(subjects) {
  const chartCanvas = document.getElementById("chart");
  if (!chartCanvas || typeof Chart === "undefined") return;

  if (chartRef) chartRef.destroy();

  chartRef = new Chart(chartCanvas, {
    type: "bar",
    data: {
      labels: subjects.map(item => item.subject),
      datasets: [{
        label: "Attendance count",
        data: subjects.map(item => item.count),
        backgroundColor: ["#ff7a18", "#ffb347", "#ffd166", "#6ee7b7", "#22d3ee", "#60a5fa", "#f472b6"],
        borderRadius: 12
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: { ticks: { color: "#dbeafe" }, grid: { display: false } },
        y: { ticks: { color: "#dbeafe", precision: 0 }, grid: { color: "rgba(219,234,254,0.08)" } }
      }
    }
  });
}

async function loadDashboard() {
  const session = getSession();
  if (!session) {
    window.location.href = "index.html";
    return;
  }

  try {
    const data = await fetchJson(`/dashboard?usn=${encodeURIComponent(session.usn)}`);
    renderProfile(data.user);
    renderStats(data.stats);
    renderChart(data.attendance_by_subject);
    renderTable(data.recent_attendance);
    setStatus("dashboard_status", "Dashboard refreshed.", false);
  } catch (error) {
    setStatus("dashboard_status", error.message, true);
  }
}

async function markAttendance() {
  const session = getSession();
  if (!session) {
    logout();
    return;
  }

  const subject = getValue("subject");
  if (!subject) {
    setStatus("dashboard_status", "Choose or type a subject before marking attendance.", true);
    return;
  }

  try {
    const data = await fetchJson("/mark", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ usn: session.usn, subject })
    });
    setStatus("dashboard_status", data.message, false);
    document.getElementById("subject").value = "";
    await loadDashboard();
  } catch (error) {
    setStatus("dashboard_status", error.message, true);
  }
}

function downloadExcel() {
  const session = getSession();
  const suffix = session?.usn ? `?usn=${encodeURIComponent(session.usn)}` : "";
  window.open(`${API_BASE}/export${suffix}`, "_blank");
}

document.addEventListener("DOMContentLoaded", () => {
  startCamera();
  loadColleges();
  populateSubjectList();
  bindFileInput(registerImageInput, "Register image");
  bindFileInput(loginImageInput, "Login image");
  if (document.getElementById("camera_status")) {
    setStatus("camera_status", "Camera ready. Keep your full face inside the guide.", false);
  }

  if (document.body.dataset.page === "dashboard") {
    loadDashboard();
  }
});
