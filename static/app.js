/* =========================================================
   GECE/GÜNDÜZ MODU (THEME) YÖNETİMİ
========================================================= */
const themeToggle = document.getElementById("themeToggle");
const sunIcon = document.getElementById("sunIcon");
const moonIcon = document.getElementById("moonIcon");

// Temayı değiştirme ve localStorage'a kaydetme fonksiyonu
function setTheme(themeName) {
  document.documentElement.setAttribute("data-theme", themeName);
  localStorage.setItem("app_theme", themeName);
  
  if (themeName === "light") {
    sunIcon.style.display = "none";
    moonIcon.style.display = "block"; // Gece moduna geçiş ikonunu göster
  } else {
    sunIcon.style.display = "block";  // Gündüz moduna geçiş ikonunu göster
    moonIcon.style.display = "none";
  }
}

// Sayfa yüklendiğinde hafızadan veya işletim sisteminden temayı bul
const savedTheme = localStorage.getItem("app_theme");
const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;

if (savedTheme) {
  setTheme(savedTheme);
} else if (prefersDark) {
  setTheme("dark");
} else {
  setTheme("light");
}

// Butona tıklandığında temaları değiştir
themeToggle.addEventListener("click", () => {
  const currentTheme = document.documentElement.getAttribute("data-theme");
  setTheme(currentTheme === "dark" ? "light" : "dark");
});

/* =========================================================
   VAR OLAN HASAR ANALİZİ UYGULAMA MANTIĞI
========================================================= */

const form = document.querySelector("#damageForm");
const apiKeyInput = document.querySelector("#apiKey");
const useDamageModelInput = document.querySelector("#useDamageModel");
const useVehicleClassifierInput = document.querySelector("#useVehicleClassifier");
const useGeminiInput = document.querySelector("#useGemini");
const useAuthorizedServiceInput = document.querySelector("#useAuthorizedService");
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
const resultStatus = document.querySelector("#resultStatus");
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
const priceItemsList = document.querySelector("#priceItemsList");
const expertNote = document.querySelector("#expertNote");
const assumptionsList = document.querySelector("#assumptionsList");
const imageGallery = document.querySelector("#imageGallery");
const imageGallerySection = document.querySelector("#imageGallerySection");
const modelStatus = document.querySelector("#modelStatus");
const modelFile = document.querySelector("#modelFile");
const damageMode = document.querySelector("#damageMode");
const vehicleMode = document.querySelector("#vehicleMode");
const geminiMode = document.querySelector("#geminiMode");
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

function fillPriceItems(element, items) {
  element.innerHTML = "";
  if (!Array.isArray(items) || !items.length) {
    const empty = document.createElement("div");
    empty.className = "muted-text";
    empty.textContent = "Kalem bazli fiyat bulunamadi.";
    element.appendChild(empty);
    return;
  }

  for (const item of items) {
    const row = document.createElement("div");
    row.className = "price-item";
    const left = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = item.kalem || "Kalem";
    const meta = document.createElement("span");
    meta.textContent = `${item.adet || 1} adet - ${item.islem || "islem"} - ${item.kaynak || "api"}`;
    left.appendChild(title);
    left.appendChild(meta);

    const values = document.createElement("div");
    values.className = "price-values";
    const part = document.createElement("span");
    part.textContent = `Parca: ${formatMoney(item.parca_maliyeti)}`;
    const labor = document.createElement("span");
    labor.textContent = `Iscilik: ${formatMoney(item.iscilik_maliyeti)}`;
    const total = document.createElement("strong");
    total.textContent = formatMoney(item.toplam_maliyet);
    values.appendChild(part);
    values.appendChild(labor);
    values.appendChild(total);

    row.appendChild(left);
    row.appendChild(values);
    element.appendChild(row);
  }
}

function getReport(data) {
  return (
    data?.gemini_raporu?.rapor ||
    data?.gemini_sonucu?.rapor ||
    null
  );
}

function showResult(data) {
  const report = getReport(data);
  emptyState.hidden = true;
  reportView.hidden = false;
  resultBox.textContent = JSON.stringify(data, null, 2);

  if (data.cizimli_gorseller && data.cizimli_gorseller.length > 0) {
    imageGallerySection.hidden = false;
    imageGallery.innerHTML = "";
    data.cizimli_gorseller.forEach((base64, index) => {
      const card = document.createElement("div");
      card.style.minWidth = "280px";
      card.style.flexShrink = "0";
      card.style.border = "1px solid var(--border-color)";
      card.style.borderRadius = "8px";
      card.style.overflow = "hidden";
      card.style.display = "flex";
      card.style.flexDirection = "column";
      card.style.backgroundColor = "var(--panel-bg)";
      card.style.scrollSnapAlign = "start";

      const img = document.createElement("img");
      img.src = `data:image/jpeg;base64,${base64}`;
      img.style.width = "100%";
      img.style.maxHeight = "220px";
      img.style.objectFit = "cover";
      img.style.backgroundColor = "#000";

      const infoBox = document.createElement("div");
      infoBox.style.padding = "10px";
      infoBox.style.fontSize = "13px";
      infoBox.style.borderTop = "1px solid var(--border-color)";
      
      const tespitVerisi = data.hasar_tespitleri ? data.hasar_tespitleri[index] : null;
      if (tespitVerisi && tespitVerisi.tespitler && tespitVerisi.tespitler.length > 0) {
        const title = document.createElement("strong");
        title.textContent = "Tespitler:";
        title.style.display = "block";
        title.style.marginBottom = "5px";
        infoBox.appendChild(title);

        tespitVerisi.tespitler.forEach(t => {
          const item = document.createElement("div");
          item.textContent = `- ${t.hasar_tipi} (Güven: %${Math.round(t.guven_skoru * 100)})`;
          infoBox.appendChild(item);
        });
      } else {
        const item = document.createElement("div");
        item.textContent = "Hasar tespit edilemedi.";
        item.style.color = "var(--text-muted)";
        infoBox.appendChild(item);
      }

      card.appendChild(img);
      card.appendChild(infoBox);
      imageGallery.appendChild(card);
    });
  } else {
    imageGallerySection.hidden = true;
    imageGallery.innerHTML = "";
  }


  if (!report) {
    setText(vehicleTitle, "Rapor oluşmadı");
    setText(severityBadge, data?.gemini_raporu?.status || "Atlandı");
    setText(totalCost, "-");
    setText(costBreakdown, data?.gemini_raporu?.message || "Gemini raporu bulunamadı.");
    setText(
      damageSummary,
      data?.gemini_raporu?.fallback_rapor
        ? "Gemini API hata verdi; yerel fallback rapor teknik JSON içinde duruyor."
        : "Geliştirici Formatı (JSON) bölümünden cevabı inceleyebilirsin."
    );
    setText(repairTime, "-");
    setText(imageCount, data?.message || "-");
    setText(repairAdvice, "-");
    fillChipList(partsList, []);
    fillPriceItems(priceItemsList, []);
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
    `Parça: ${formatMoney(cost.parca_maliyeti)} | İşçilik: ${formatMoney(cost.iscilik_maliyeti)}`
  );
  setText(damageSummary, report.hasar_durumu_ozeti);
  setText(repairTime, report.tahmini_islem_suresi);
  setText(imageCount, String(data?.islenen_gorsel_sayisi || "-"));
  setText(repairAdvice, report.onarim_onerisi);
  fillChipList(partsList, report.degisecek_parcalar);
  fillPriceItems(priceItemsList, report.fiyat_kalemleri);
  setText(expertNote, report.usta_notu);
  fillCleanList(assumptionsList, report.varsayimlar);
}

function showMessage(message) {
  emptyState.hidden = true;
  reportView.hidden = true;
  emptyState.hidden = false;
  emptyState.textContent = message;
}

function setResultStatus(message = "") {
  resultStatus.hidden = !message;
  resultStatus.textContent = message;
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
  geminiMode.textContent = useGeminiInput.checked ? "Acik" : "Kapali";
  apiKeyInput.disabled = !useGeminiInput.checked;
  toggleKey.disabled = !useGeminiInput.checked;
}

async function loadHealth() {
  try {
    const response = await fetch("/health");
    const data = await response.json();
    modelFile.textContent = data.model_available ? data.model_path : `${data.model_path} yok`;
    modelStatus.textContent = data.model_available ? "Model hazır" : "Model bekleniyor";
    modelStatus.classList.toggle("ready", data.model_available);
    modelStatus.classList.toggle("missing", !data.model_available);
    damageClasses.textContent = Array.isArray(data.damage_classes)
      ? data.damage_classes.join(", ")
      : "-";
    vehicleModelStatus.textContent = data.vehicle_classifier_available
      ? "Hazır"
      : data.vehicle_classifier_repo || "Bekleniyor";
    keyStatus.textContent = data.gemini_api_configured
      ? "Sunucuda ayarlı"
      : "Formdan girilebilir";
  } catch (error) {
    modelStatus.textContent = "Bağlantı yok";
    modelStatus.classList.add("missing");
    modelFile.textContent = "Kontrol edilemedi";
  }
}

toggleKey.addEventListener("click", () => {
  const shouldShow = apiKeyInput.type === "password";
  apiKeyInput.type = shouldShow ? "text" : "password";
  toggleKeyIcon.textContent = shouldShow ? "Gizle" : "Göster";
});

fileInput.addEventListener("change", () => {
  addSelectedFiles(fileInput.files);
  updatePreview();
  fileInput.value = "";
});

useDamageModelInput.addEventListener("change", updatePipelineMode);
useVehicleClassifierInput.addEventListener("change", updatePipelineMode);
useGeminiInput.addEventListener("change", updatePipelineMode);

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
  emptyState.textContent = "Bir dosya yükleyip analizi başlattığında sonuçlar burada görüntülenecektir.";
  setResultStatus("");
  resultBox.textContent = "";
  selectedFiles = [];
  resetPreview();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!selectedFiles.length) {
    showMessage("Önce bir resim veya video seçmelisin.");
    return;
  }

  if (useGeminiInput.checked && !apiKeyInput.value.trim()) {
    showMessage("Gemini Raporu acik. AI API'ye gitmesi icin Gemini API Key girmelisin.");
    return;
  }

  const body = new FormData();
  for (const file of selectedFiles) {
    body.append("files", file);
  }
  body.append("gemini_api_key", apiKeyInput.value.trim());
  body.append("use_damage_model", useDamageModelInput.checked ? "true" : "false");
  body.append("use_vehicle_classifier", useVehicleClassifierInput.checked ? "true" : "false");
  body.append("use_gemini", useGeminiInput.checked ? "true" : "false");
  body.append("use_authorized_service", useAuthorizedServiceInput.checked ? "true" : "false");

  submitButton.disabled = true;
  submitButton.textContent = "Analiz ediliyor...";
  setResultStatus("Analiz suruyor...");

  try {
    const response = await fetch("/api/v1/process-damage", {
      method: "POST",
      body,
    });
    const data = await response.json();

    if (!response.ok) {
      showResult({
        status: "error",
        detail: data.detail || "İşlem tamamlanamadı.",
      });
      return;
    }

    showResult(data);
    setResultStatus("Tamamlandi");
    loadHealth();
  } catch (error) {
    showResult({
      status: "error",
      detail: "Sunucuya ulaşılamadı.",
    });
    setResultStatus("Hata");
  } finally {
    submitButton.disabled = false;
    submitButton.innerHTML = `<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path><path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg> Analizi Başlat`;
  }
});

updatePipelineMode();
loadHealth();
