const form = document.querySelector("#damageForm");
const apiKeyInput = document.querySelector("#apiKey");
const useDamageModelInput = document.querySelector("#useDamageModel");
const useVehicleClassifierInput = document.querySelector("#useVehicleClassifier");
const toggleKey = document.querySelector("#toggleKey");
const toggleKeyIcon = document.querySelector("#toggleKeyIcon");
const fileInput = document.querySelector("#fileInput");
const dropzone = document.querySelector("#dropzone");
const preview = document.querySelector("#preview");
const imagePreview = document.querySelector("#imagePreview");
const videoPreview = document.querySelector("#videoPreview");
const fileName = document.querySelector("#fileName");
const fileMeta = document.querySelector("#fileMeta");
const fileListElement = document.querySelector("#fileList");
const submitButton = document.querySelector("#submitButton");
const clearButton = document.querySelector("#clearButton");
const resultBox = document.querySelector("#resultBox");
const emptyState = document.querySelector("#emptyState");
const reportView = document.querySelector("#reportView");
const vehicleTitle = document.querySelector("#vehicleTitle");
const severityBadge = document.querySelector("#severityBadge");
const totalCost = document.querySelector("#totalCost");
const costBreakdown = document.querySelector("#costBreakdown");
const damageSummary = document.querySelector("#damageSummary");
const repairTime = document.querySelector("#repairTime");
const imageCount = document.querySelector("#imageCount");
const repairAdvice = document.querySelector("#repairAdvice");
const partsList = document.querySelector("#partsList");
const expertNote = document.querySelector("#expertNote");
const assumptionsList = document.querySelector("#assumptionsList");
const modelStatus = document.querySelector("#modelStatus");
const modelFile = document.querySelector("#modelFile");
const damageMode = document.querySelector("#damageMode");
const vehicleMode = document.querySelector("#vehicleMode");
const vehicleModelStatus = document.querySelector("#vehicleModelStatus");
const damageClasses = document.querySelector("#damageClasses");
const keyStatus = document.querySelector("#keyStatus");

let previewUrl = "";
let selectedFiles = [];

function formatMoney(value) {
  if (typeof value !== "number") return "-";
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value);
}

function setText(element, value, fallback = "-") {
  element.textContent = value || fallback;
}

function fillChipList(element, items) {
  element.innerHTML = "";
  if (!Array.isArray(items) || !items.length) {
    const empty = document.createElement("span");
    empty.className = "muted-text";
    empty.textContent = "Belirtilmedi";
    element.appendChild(empty);
    return;
  }

  for (const item of items) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = item;
    element.appendChild(chip);
  }
}

function fillCleanList(element, items) {
  element.innerHTML = "";
  if (!Array.isArray(items) || !items.length) {
    const item = document.createElement("li");
    item.textContent = "Belirtilmedi";
    element.appendChild(item);
    return;
  }

  for (const text of items) {
    const item = document.createElement("li");
    item.textContent = text;
    element.appendChild(item);
  }
}

function getReport(data) {
  return data?.gemini_raporu?.rapor || data?.gemini_sonucu?.rapor || null;
}

function showResult(data) {
  const report = getReport(data);
  emptyState.hidden = true;
  reportView.hidden = false;
  resultBox.textContent = JSON.stringify(data, null, 2);

  if (!report) {
    setText(vehicleTitle, "Rapor olusmadi");
    setText(severityBadge, "Atlandi");
    setText(totalCost, "-");
    setText(costBreakdown, data?.gemini_raporu?.message || "Gemini raporu bulunamadi.");
    setText(damageSummary, "Teknik JSON bolumunden cevabi inceleyebilirsin.");
    setText(repairTime, "-");
    setText(imageCount, data?.message || "-");
    setText(repairAdvice, "-");
    fillChipList(partsList, []);
    setText(expertNote, "-");
    fillCleanList(assumptionsList, []);
    return;
  }

  const cost = report.tahmini_maliyet_2026_tl || {};
  const brand = report.arac_marka || "Marka belirsiz";
  const model = report.arac_model || "Model belirsiz";
  setText(vehicleTitle, `${brand} ${model}`);
  setText(severityBadge, report.hasar_seviyesi);
  severityBadge.className = `severity-badge severity-${String(report.hasar_seviyesi || "").toLowerCase()}`;
  setText(totalCost, formatMoney(cost.toplam_maliyet));
  setText(
    costBreakdown,
    `Parca: ${formatMoney(cost.parca_maliyeti)} | Iscilik: ${formatMoney(cost.iscilik_maliyeti)}`
  );
  setText(damageSummary, report.hasar_durumu_ozeti);
  setText(repairTime, report.tahmini_islem_suresi);
  setText(imageCount, String(data?.islenen_gorsel_sayisi || "-"));
  setText(repairAdvice, report.onarim_onerisi);
  fillChipList(partsList, report.degisecek_parcalar);
  setText(expertNote, report.usta_notu);
  fillCleanList(assumptionsList, report.varsayimlar);
}

function showMessage(message) {
  emptyState.hidden = true;
  reportView.hidden = true;
  emptyState.hidden = false;
  emptyState.textContent = message;
}

function resetPreview() {
  if (previewUrl) {
    URL.revokeObjectURL(previewUrl);
    previewUrl = "";
  }

  preview.hidden = true;
  imagePreview.hidden = true;
  videoPreview.hidden = true;
  imagePreview.removeAttribute("src");
  videoPreview.removeAttribute("src");
  fileName.textContent = "";
  fileMeta.textContent = "";
  fileListElement.innerHTML = "";
}

function formatBytes(bytes) {
  if (!bytes) return "0 KB";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** index;
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

function addSelectedFiles(files) {
  for (const file of Array.from(files || [])) {
    const key = `${file.name}-${file.size}-${file.lastModified}`;
    const exists = selectedFiles.some(
      (selectedFile) => `${selectedFile.name}-${selectedFile.size}-${selectedFile.lastModified}` === key
    );
    if (!exists && (file.type.startsWith("image/") || file.type.startsWith("video/"))) {
      selectedFiles.push(file);
    }
  }
}

function updatePreview() {
  resetPreview();
  const currentFiles = selectedFiles;
  const file = currentFiles[0];
  if (!file) return;

  previewUrl = URL.createObjectURL(file);
  preview.hidden = false;
  fileName.textContent =
    currentFiles.length > 1 ? `${file.name} ve ${currentFiles.length - 1} dosya daha` : file.name;
  const totalSize = currentFiles.reduce((sum, item) => sum + item.size, 0);
  fileMeta.textContent = `${currentFiles.length} dosya - ${formatBytes(totalSize)}`;
  fileListElement.innerHTML = "";
  for (const selectedFile of currentFiles) {
    const item = document.createElement("span");
    item.textContent = selectedFile.name;
    fileListElement.appendChild(item);
  }

  if (file.type.startsWith("image/")) {
    imagePreview.src = previewUrl;
    imagePreview.hidden = false;
  } else if (file.type.startsWith("video/")) {
    videoPreview.src = previewUrl;
    videoPreview.hidden = false;
  }
}

function updatePipelineMode() {
  damageMode.textContent = useDamageModelInput.checked ? "Acik" : "Kapali";
  vehicleMode.textContent = useVehicleClassifierInput.checked ? "Acik" : "Kapali";
}

async function loadHealth() {
  try {
    const response = await fetch("/health");
    const data = await response.json();
    modelFile.textContent = data.model_available ? data.model_path : `${data.model_path} yok`;
    modelStatus.textContent = data.model_available ? "Model hazir" : "Model bekleniyor";
    modelStatus.classList.toggle("ready", data.model_available);
    modelStatus.classList.toggle("missing", !data.model_available);
    damageClasses.textContent = Array.isArray(data.damage_classes)
      ? data.damage_classes.join(", ")
      : "-";
    vehicleModelStatus.textContent = data.vehicle_classifier_available
      ? "Hazir"
      : data.vehicle_classifier_repo || "Bekleniyor";
    keyStatus.textContent = data.gemini_api_configured
      ? "Sunucuda ayarli"
      : "Formdan girilebilir";
  } catch (error) {
    modelStatus.textContent = "Baglanti yok";
    modelStatus.classList.add("missing");
    modelFile.textContent = "Kontrol edilemedi";
  }
}

toggleKey.addEventListener("click", () => {
  const shouldShow = apiKeyInput.type === "password";
  apiKeyInput.type = shouldShow ? "text" : "password";
  toggleKeyIcon.textContent = shouldShow ? "Gizle" : "Goster";
});

fileInput.addEventListener("change", () => {
  addSelectedFiles(fileInput.files);
  updatePreview();
  fileInput.value = "";
});

useDamageModelInput.addEventListener("change", updatePipelineMode);
useVehicleClassifierInput.addEventListener("change", updatePipelineMode);

for (const eventName of ["dragenter", "dragover"]) {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add("dragging");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragging");
  });
}

dropzone.addEventListener("drop", (event) => {
  addSelectedFiles(event.dataTransfer.files);
  updatePreview();
});

clearButton.addEventListener("click", () => {
  reportView.hidden = true;
  emptyState.hidden = false;
  emptyState.textContent = "Bir dosya yukleyip analizi baslattiginda cevap burada gorunecek.";
  resultBox.textContent = "";
  selectedFiles = [];
  resetPreview();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!selectedFiles.length) {
    showMessage("Once bir resim veya video secmelisin.");
    return;
  }

  const body = new FormData();
  for (const file of selectedFiles) {
    body.append("files", file);
  }
  body.append("gemini_api_key", apiKeyInput.value.trim());
  body.append("use_damage_model", useDamageModelInput.checked ? "true" : "false");
  body.append("use_vehicle_classifier", useVehicleClassifierInput.checked ? "true" : "false");

  submitButton.disabled = true;
  submitButton.textContent = "Analiz ediliyor...";
  showMessage("Dosya yukleniyor; hasar modeli, Hugging Face ve Gemini adimlari sirayla calisiyor...");

  try {
    const response = await fetch("/api/v1/process-damage", {
      method: "POST",
      body,
    });
    const data = await response.json();

    if (!response.ok) {
      showResult({
        status: "error",
        detail: data.detail || "Islem tamamlanamadi.",
      });
      return;
    }

    showResult(data);
    loadHealth();
  } catch (error) {
    showResult({
      status: "error",
      detail: "Sunucuya ulasilamadi.",
    });
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Analizi Baslat";
  }
});

updatePipelineMode();
loadHealth();
