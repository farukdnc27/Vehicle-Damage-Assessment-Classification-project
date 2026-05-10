import base64
import json
import os
import tempfile
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from ultralytics import YOLO


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Arac Hasar Analiz ve Raporlama API")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

MODEL_PATH = Path(os.getenv("MODEL_PATH", BASE_DIR / "best.pt"))
DAMAGE_CLASSES = ["crack", "dent", "glass shatter", "lamp broken", "scratch", "tire flat"]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()
GEMINI_API_URL = os.getenv(
    "GEMINI_API_URL",
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
)
HF_VEHICLE_REPO = os.getenv("HF_VEHICLE_REPO", "Jordo23/vehicle-classifier").strip()
HF_VEHICLE_MODEL_PATH = Path(
    os.getenv("HF_VEHICLE_MODEL_PATH", BASE_DIR / "vehicle_classifier.pth")
)
EXTERNAL_API_TIMEOUT = float(os.getenv("EXTERNAL_API_TIMEOUT", "180"))


@lru_cache(maxsize=1)
def get_model() -> YOLO:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model dosyasi bulunamadi: {MODEL_PATH}. "
            "Arkadasindan gelen best.pt dosyasini proje klasorune koy "
            "veya MODEL_PATH ortam degiskenini ayarla."
        )
    return YOLO(str(MODEL_PATH))


def get_frame_from_video(video_bytes: bytes) -> np.ndarray:
    """Read the first frame from uploaded video bytes."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
        temp_file.write(video_bytes)
        temp_video_path = temp_file.name

    try:
        cap = cv2.VideoCapture(temp_video_path)
        success, frame = cap.read()
        cap.release()
    finally:
        Path(temp_video_path).unlink(missing_ok=True)

    if not success or frame is None:
        raise ValueError("Videodan kare okunamadi.")
    return frame


def get_image_from_bytes(image_bytes: bytes) -> np.ndarray:
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Gorsel dosyasi okunamadi.")
    return frame


def image_to_base64(image_matrix: np.ndarray, max_size: int = 768) -> str:
    h, w = image_matrix.shape[:2]
    if max(h, w) > max_size:
        scale = max_size / max(h, w)
        image_matrix = cv2.resize(image_matrix, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        
    success, buffer = cv2.imencode(".jpg", image_matrix, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
    if not success:
        raise ValueError("Gorsel base64 formatina cevrilemedi.")
    return base64.b64encode(buffer).decode("utf-8")


def run_yolo(frame: np.ndarray) -> list[dict[str, Any]]:
    model = get_model()
    # Güven skorunu 0.1'e düşürerek modelin daha fazla hasarı tespit etmesini sağlıyoruz
    results = model(frame, conf=0.5)
    detections: list[dict[str, Any]] = []

    for result in results:
        has_masks = result.masks is not None
        for i, box in enumerate(result.boxes):
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            class_id = int(box.cls[0].item())
            
            det_data = {
                "hasar_tipi": model.names[class_id],
                "guven_skoru": round(float(box.conf[0].item()), 2),
                "bbox": {
                    "x1": int(x1),
                    "y1": int(y1),
                    "x2": int(x2),
                    "y2": int(y2),
                },
            }
            
            if has_masks and len(result.masks.xy) > i:
                det_data["polygon"] = result.masks.xy[i].tolist()
                
            detections.append(det_data)

    return detections


def run_yolo_safe(frame: np.ndarray) -> dict[str, Any]:
    try:
        return {
            "status": "success",
            "tespitler": run_yolo(frame),
        }
    except FileNotFoundError as exc:
        return {
            "status": "skipped",
            "message": str(exc),
            "tespitler": [],
        }


def parse_vehicle_label(label: str) -> dict[str, str | None]:
    parts = label.rsplit(" ", 1)
    year = parts[1] if len(parts) == 2 and parts[1].isdigit() else None
    make_model = parts[0] if year else label
    make_model_parts = make_model.split(" ", 1)
    make = make_model_parts[0] if make_model_parts else None
    model = make_model_parts[1] if len(make_model_parts) > 1 else None
    return {"make": make, "model": model, "year": year}


@lru_cache(maxsize=1)
def get_vehicle_classifier() -> dict[str, Any]:
    try:
        import timm
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "Hugging Face arac siniflandirici icin timm ve torch gerekiyor. "
            "Kurulum: pip install timm torch torchvision huggingface_hub pillow"
        ) from exc

    model_path = HF_VEHICLE_MODEL_PATH
    if not model_path.exists():
        try:
            from huggingface_hub import hf_hub_download

            downloaded_path = hf_hub_download(
                repo_id=HF_VEHICLE_REPO,
                filename="vehicle_classifier.pth",
            )
            model_path = Path(downloaded_path)
        except Exception as exc:
            raise FileNotFoundError(
                f"Hugging Face arac modeli bulunamadi: {HF_VEHICLE_MODEL_PATH}. "
                f"{HF_VEHICLE_REPO} reposundan vehicle_classifier.pth dosyasini indirip "
                "proje klasorune koy veya HF_VEHICLE_MODEL_PATH ortam degiskenini ayarla."
            ) from exc

    checkpoint = torch.load(model_path, map_location="cpu")
    class_mapping = checkpoint.get("class_mapping")
    if not class_mapping:
        raise RuntimeError("vehicle_classifier.pth icinde class_mapping bulunamadi.")

    model = timm.create_model(
        "efficientnet_b4",
        pretrained=False,
        num_classes=len(class_mapping),
    )
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    return {
        "model": model,
        "class_mapping": class_mapping,
        "torch": torch,
    }


def infer_vehicle_info(frame: np.ndarray) -> dict[str, Any]:
    try:
        classifier = get_vehicle_classifier()
    except (FileNotFoundError, RuntimeError) as exc:
        return {
            "status": "skipped",
            "provider": "huggingface-local",
            "message": str(exc),
            "tahminler": [],
            "en_iyi_tahmin": None,
        }

    model = classifier["model"]
    class_mapping = classifier["class_mapping"]
    torch = classifier["torch"]

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (380, 380), interpolation=cv2.INTER_AREA)
    image_array = resized.astype(np.float32) / 255.0
    image_array = (image_array - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    image_array = image_array.transpose(2, 0, 1)

    input_tensor = torch.from_numpy(image_array).unsqueeze(0).float()
    with torch.no_grad():
        logits = model(input_tensor)
        probs = torch.softmax(logits, dim=1)
        top_probs, top_indices = torch.topk(probs, 5)

    predictions = []
    for prob, index in zip(top_probs[0], top_indices[0]):
        class_id = int(index.item())
        label = class_mapping.get(class_id) or class_mapping.get(str(class_id)) or str(class_id)
        predictions.append(
            {
                "label": label,
                "confidence": round(float(prob.item()), 4),
                **parse_vehicle_label(label),
            }
        )

    return {
        "status": "success",
        "provider": "huggingface-local",
        "repo": HF_VEHICLE_REPO,
        "en_iyi_tahmin": predictions[0] if predictions else None,
        "tahminler": predictions,
    }


def create_local_report(payload: dict[str, Any]) -> dict[str, Any]:
    arac_marka = "Bilinmiyor"
    arac_model = ""
    arac_bilgisi = payload.get("arac_bilgisi", {})
    if arac_bilgisi.get("status") == "success" and arac_bilgisi.get("en_iyi_tahmin"):
        tahmin = arac_bilgisi["en_iyi_tahmin"]
        arac_marka = tahmin.get("make") or tahmin.get("label", "Bilinmiyor")
        arac_model = tahmin.get("model") or ""
    elif arac_bilgisi.get("message") and arac_bilgisi.get("status") != "success":
        arac_marka = "Hata:"
        arac_model = arac_bilgisi["message"]

    hasar_sayilari = {}
    tum_hasarlar = []
    
    for dosya_veri in payload.get("hasar_tespitleri", []):
        if not isinstance(dosya_veri, dict): continue
        for tespit in dosya_veri.get("tespitler", []):
            hasar_tipi = tespit.get("hasar_tipi", "bilinmeyen")
            hasar_sayilari[hasar_tipi] = hasar_sayilari.get(hasar_tipi, 0) + 1
            tum_hasarlar.append(hasar_tipi)

    toplam_hasar = len(tum_hasarlar)
    parca_maliyeti = 0
    iscilik_maliyeti = 0
    fiyat_kalemleri = []
    yetkili_servis_mi = payload.get("yetkili_servis_acik_mi", False)
    
    maliyet_tablosu = {
        "crack": {"parca": 0, "iscilik": 2000},
        "dent": {"parca": 0, "iscilik": 3500},
        "glass shatter": {"parca": 8000, "iscilik": 1500},
        "lamp broken": {"parca": 6000, "iscilik": 1000},
        "scratch": {"parca": 0, "iscilik": 1500},
        "tire flat": {"parca": 4000, "iscilik": 500},
    }
    yetkili_servis_degisim_tablosu = {
        "crack": {"parca": 18000, "iscilik": 7000, "parca_adi": "Hasarli panel/kaporta parcasi"},
        "dent": {"parca": 22000, "iscilik": 8500, "parca_adi": "Gocuklu panel/kaporta parcasi"},
        "glass shatter": {"parca": 18000, "iscilik": 3500, "parca_adi": "Cam parcasi"},
        "lamp broken": {"parca": 16000, "iscilik": 3000, "parca_adi": "Far/stop lamba grubu"},
        "scratch": {"parca": 12000, "iscilik": 6500, "parca_adi": "Cizikli boya/panel parcasi"},
        "tire flat": {"parca": 9500, "iscilik": 1200, "parca_adi": "Lastik"},
    }
    
    degisecek_parcalar = []
    
    for hasar, adet in hasar_sayilari.items():
        aktif_tablo = yetkili_servis_degisim_tablosu if yetkili_servis_mi else maliyet_tablosu
        if hasar in aktif_tablo:
            m = aktif_tablo[hasar]
            kalem_parca = m["parca"] * adet
            kalem_iscilik = m["iscilik"] * adet
            parca_maliyeti += kalem_parca
            iscilik_maliyeti += kalem_iscilik
            fiyat_kalemleri.append(
                {
                    "kalem": m.get("parca_adi", hasar),
                    "adet": adet,
                    "islem": "degisim" if yetkili_servis_mi or hasar in ["glass shatter", "lamp broken", "tire flat"] else "onarim",
                    "parca_maliyeti": kalem_parca,
                    "iscilik_maliyeti": kalem_iscilik,
                    "toplam_maliyet": kalem_parca + kalem_iscilik,
                    "kaynak": "local-yetkili-servis-degisim" if yetkili_servis_mi else "local-sabit-tablo",
                }
            )
            
        if yetkili_servis_mi or hasar in ["glass shatter", "lamp broken", "tire flat"]:
            degisecek_parcalar.append(f"{hasar} değişimi")

    toplam_maliyet = parca_maliyeti + iscilik_maliyeti

    if toplam_hasar == 0:
        hasar_seviyesi = "Hafif"
        hasar_durumu_ozeti = "Görselde belirgin bir hasar tespit edilemedi."
    elif toplam_hasar <= 2 and toplam_maliyet < 30000:
        hasar_seviyesi = "Hafif"
        hasar_durumu_ozeti = "Araçta hafif düzeyde yüzeysel hasarlar mevcut."
    elif toplam_hasar <= 5 and toplam_maliyet < 70000:
        hasar_seviyesi = "Orta"
        hasar_durumu_ozeti = "Araçta orta düzeyde, onarım gerektiren hasarlar bulunmaktadır."
    else:
        hasar_seviyesi = "Agir"
        hasar_durumu_ozeti = "Araçta ağır düzeyde hasar tespit edilmiştir."

    tahmini_sure = "1-2 Gün"
    if hasar_seviyesi == "Orta":
        tahmini_sure = "3-5 Gün"
    elif hasar_seviyesi == "Agir":
        tahmini_sure = "7-14 Gün"

    rapor = {
        "arac_marka": arac_marka,
        "arac_model": arac_model.strip(),
        "hasar_durumu_ozeti": hasar_durumu_ozeti,
        "hasar_seviyesi": hasar_seviyesi,
        "tahmini_maliyet_2026_tl": {
            "parca_maliyeti": parca_maliyeti,
            "iscilik_maliyeti": iscilik_maliyeti,
            "toplam_maliyet": toplam_maliyet
        },
        "fiyat_kalemleri": fiyat_kalemleri,
        "degisecek_parcalar": degisecek_parcalar if degisecek_parcalar else ["Değişecek parça tespiti yapılamadı"],
        "onarim_onerisi": "YOLO modelinin tespitlerine dayalı temel onarım işlemleri önerilmektedir.",
        "tahmini_islem_suresi": tahmini_sure,
        "usta_notu": "Bu rapor, Gemini API kullanılmadan yerel modellerin (YOLO & HuggingFace) sonuçlarına göre otomatik üretilmiş tahmini bir değerlendirmedir.",
        "varsayimlar": [
            "Fiyatlar 2026 yılı ortalama piyasa koşullarına göre varsayılmıştır.",
            "Detaylı ekspertiz gerektiren gizli hasarlar (örn. motor, şasi) değerlendirmeye alınmamıştır."
        ]
    }

    return {
        "status": "success",
        "provider": "local-rule-based",
        "rapor": rapor,
    }


def compact_payload_for_gemini(payload: dict[str, Any]) -> dict[str, Any]:
    compact_damage = []
    for file_damage in payload.get("hasar_tespitleri", []):
        detections = []
        for detection in file_damage.get("tespitler", [])[:20]:
            detections.append(
                {
                    "hasar_tipi": detection.get("hasar_tipi"),
                    "guven_skoru": detection.get("guven_skoru"),
                    "bbox": detection.get("bbox"),
                }
            )
        compact_damage.append(
            {
                "dosya_adi": file_damage.get("dosya_adi"),
                "status": file_damage.get("status"),
                "message": file_damage.get("message"),
                "tespit_sayisi": len(file_damage.get("tespitler", [])),
                "tespitler": detections,
            }
        )

    vehicle_info = payload.get("arac_bilgisi", {})
    compact_vehicle = {
        "status": vehicle_info.get("status"),
        "provider": vehicle_info.get("provider"),
        "message": vehicle_info.get("message"),
        "en_iyi_tahmin": vehicle_info.get("en_iyi_tahmin"),
        "tahminler": vehicle_info.get("tahminler", [])[:3],
    }

    return {
        "hasar_tespitleri": compact_damage,
        "arac_bilgisi": compact_vehicle,
        "islenen_gorsel_sayisi": payload.get("islenen_gorsel_sayisi"),
        "kullanilan_siniflar": payload.get("kullanilan_siniflar"),
        "yetkili_servis_acik_mi": payload.get("yetkili_servis_acik_mi", False),
        "pipeline": payload.get("pipeline"),
    }


def create_report(
    payload: dict[str, Any],
    base64_images: list[str],
    api_key: str | None = None,
) -> dict[str, Any]:
    active_api_key = (api_key or GEMINI_API_KEY).strip()
    if not active_api_key:
        raise HTTPException(
            status_code=400,
            detail="Gemini raporu acik ama Gemini API key girilmedi.",
        )

    yetkili_servis_mi = payload.get("yetkili_servis_acik_mi", False)
    fiyat_tipi = "Yetkili Servis (orijinal yedek parça ve bayi işçiliği)" if yetkili_servis_mi else "Özel Servis / Sanayi (yan sanayi/çıkma parça ve standart işçilik)"
    yetkili_servis_kurali = (
        "Yetkili servis modu acik: fiyat_kalemleri icindeki her hasar/parca kalemini degisim olarak hesapla; "
        "parca_maliyeti OEM/orijinal yeni parca fiyati, iscilik_maliyeti bayi/yetkili servis isciligi olsun. "
        "Tamir fiyatlandirmasi kullanma."
        if yetkili_servis_mi
        else "Ozel servis modu acik: uygunsa onarim, gerekli kalemlerde degisim fiyatlandirmasi kullan."
    )

    compact_payload = compact_payload_for_gemini(payload)
    parts: list[dict[str, Any]] = [
        {
            "text": (
                "Ekteki araç görsellerini (hasarlar önceden işaretlenmiştir), yerel YOLO hasar tespitlerini ve "
                "Hugging Face araç marka/model tahminlerini inceleyerek profesyonel bir hasar raporu oluştur.\n"
                f"Maliyet tahminlerini 2025 yılı Türkiye piyasası {fiyat_tipi} fiyatlarına göre hesapla "
                "fakat raporda 2026 yılı güncel fiyatlarıymış gibi göster.\n"
                f"{yetkili_servis_kurali}\n"
                "Onarım önerilerinde parçaları değerlendirirken: Tamir edilebilecek durumdakiler için 'Tamir edilsin', "
                "tamir edilemeyecek/kurtarılamayacak kadar ağır hasarlı olanlar için 'Yeni parça satın alınsın/değiştirilsin' şeklinde "
                "net tavsiyelerde bulun.\n"
                "Eğer görselleri incelediğinde YOLO tespitlerinin atladığı veya senin daha bariz, güvenilir olarak gördüğün ekstra bir hasar fark edersen, bunu da fiyat kalemlerine ekle ve kalem isminin yanına '(Gemini Görsel Tespiti)' notunu düş.\n"
                "Belirsiz olduğun noktalar için varsayım belirt. "
                f"Bilinen hasar sınıfları: {json.dumps(DAMAGE_CLASSES, ensure_ascii=False)}. "
                f"Pipeline verisi: {json.dumps(compact_payload, ensure_ascii=False)}"
            )
        }
    ]

    for image_base64 in base64_images[:3]:
        parts.append(
            {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": image_base64,
                }
            }
        )

    generation_config = {
        "temperature": 0.2,
        "responseMimeType": "application/json",
        "responseSchema": {
            "type": "OBJECT",
            "properties": {
                "arac_marka": {"type": "STRING"},
                "arac_model": {"type": "STRING"},
                "hasar_durumu_ozeti": {"type": "STRING"},
                "hasar_seviyesi": {
                    "type": "STRING",
                    "enum": ["Hafif", "Orta", "Agir", "Pert"],
                },
                "tahmini_maliyet_2026_tl": {
                    "type": "OBJECT",
                    "properties": {
                        "parca_maliyeti": {"type": "NUMBER"},
                        "iscilik_maliyeti": {"type": "NUMBER"},
                        "toplam_maliyet": {"type": "NUMBER"},
                    },
                    "required": [
                        "parca_maliyeti",
                        "iscilik_maliyeti",
                        "toplam_maliyet",
                    ],
                },
                "degisecek_parcalar": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                },
                "fiyat_kalemleri": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "kalem": {"type": "STRING"},
                            "adet": {"type": "NUMBER"},
                            "islem": {"type": "STRING"},
                            "parca_maliyeti": {"type": "NUMBER"},
                            "iscilik_maliyeti": {"type": "NUMBER"},
                            "toplam_maliyet": {"type": "NUMBER"},
                            "kaynak": {"type": "STRING"},
                        },
                        "required": [
                            "kalem",
                            "adet",
                            "islem",
                            "parca_maliyeti",
                            "iscilik_maliyeti",
                            "toplam_maliyet",
                            "kaynak",
                        ],
                    },
                },
                "onarim_onerisi": {"type": "STRING"},
                "tahmini_islem_suresi": {"type": "STRING"},
                "usta_notu": {"type": "STRING"},
                "varsayimlar": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                },
            },
            "required": [
                "arac_marka",
                "arac_model",
                "hasar_durumu_ozeti",
                "hasar_seviyesi",
                "tahmini_maliyet_2026_tl",
                "fiyat_kalemleri",
                "degisecek_parcalar",
                "onarim_onerisi",
                "tahmini_islem_suresi",
                "usta_notu",
                "varsayimlar",
            ],
        },
    }

    gemini_payload = {
        "contents": [{"parts": parts}],
        "generationConfig": generation_config,
    }

    try:
        response = requests.post(
            GEMINI_API_URL,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": active_api_key,
            },
            json=gemini_payload,
            timeout=EXTERNAL_API_TIMEOUT,
        )
        response.raise_for_status()
        gemini_response = response.json()
        report_text = (
            gemini_response.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )

        return {
            "status": "success",
            "provider": "gemini",
            "rapor": json.loads(report_text),
            "raw_response": gemini_response,
        }
    except requests.exceptions.RequestException as exc:
        error_body = ""
        if exc.response is not None:
            error_body = f" | Cevap: {exc.response.text[:800]}"
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API'ye ulasilamadi: {exc}{error_body}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail="Harici API JSON formatinda cevap donmedi.",
        ) from exc


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model_path": str(MODEL_PATH),
        "model_available": MODEL_PATH.exists(),
        "damage_classes": DAMAGE_CLASSES,
        "gemini_model": GEMINI_MODEL,
        "vehicle_classifier_repo": HF_VEHICLE_REPO,
        "vehicle_classifier_available": HF_VEHICLE_MODEL_PATH.exists(),
        "gemini_api_configured": bool(GEMINI_API_KEY),
    }


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.post("/api/v1/process-damage")
async def process_damage(
    files: list[UploadFile] = File(...),
    gemini_api_key: str | None = Form(default=None),
    use_damage_model: bool = Form(default=True),
    use_vehicle_classifier: bool = Form(default=True),
    use_gemini: bool = Form(default=True),
    use_authorized_service: bool = Form(default=False),
) -> dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="Dosya yuklenmedi.")

    all_damage_data: list[dict[str, Any]] = []
    base64_images: list[str] = []
    annotated_base64_images: list[str] = []
    vehicle_info: dict[str, Any] | None = None
    timings: dict[str, float] = {
        "hasar_modeli_saniye": 0.0,
        "marka_model_saniye": 0.0,
        "gemini_saniye": 0.0,
    }

    for file in files:
        if not file.content_type:
            continue

        file_bytes = await file.read()
        if not file_bytes:
            continue

        try:
            if file.content_type.startswith("video/"):
                frame = get_frame_from_video(file_bytes)
            elif file.content_type.startswith("image/"):
                frame = get_image_from_bytes(file_bytes)
            else:
                continue
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"{file.filename or 'Dosya'} islenemedi: {exc}",
            ) from exc

        image_base64 = image_to_base64(frame)
        base64_images.append(image_base64)

        if use_damage_model:
            step_started_at = time.perf_counter()
            damage_result = run_yolo_safe(frame)
            timings["hasar_modeli_saniye"] += time.perf_counter() - step_started_at
            all_damage_data.append(
                {
                    "dosya_adi": file.filename,
                    **damage_result,
                }
            )
            
            annotated_frame = frame.copy()
            overlay = frame.copy()
            for tespit in damage_result.get("tespitler", []):
                bbox = tespit.get("bbox", {})
                polygon = tespit.get("polygon")
                label = f"{tespit['hasar_tipi']} ({tespit['guven_skoru']})"

                if polygon and len(polygon) > 0:
                    pts = np.array(polygon, np.int32).reshape((-1, 1, 2))
                    cv2.fillPoly(overlay, [pts], (0, 0, 255))
                    cv2.polylines(annotated_frame, [pts], True, (0, 0, 255), 2)
                    if bbox:
                        cv2.putText(annotated_frame, label, (bbox["x1"], max(bbox["y1"] - 10, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                elif bbox:
                    x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(annotated_frame, label, (x1, max(y1 - 10, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            cv2.addWeighted(overlay, 0.4, annotated_frame, 0.6, 0, annotated_frame)
            annotated_base64_images.append(image_to_base64(annotated_frame))
        else:
            annotated_base64_images.append(image_base64)

        if use_vehicle_classifier and vehicle_info is None:
            step_started_at = time.perf_counter()
            vehicle_info = infer_vehicle_info(frame)
            timings["marka_model_saniye"] += time.perf_counter() - step_started_at

    if not base64_images:
        raise HTTPException(
            status_code=400,
            detail="Gecerli resim veya video bulunamadi.",
        )

    if not use_vehicle_classifier:
        vehicle_info = {
            "status": "skipped",
            "message": "Hugging Face marka/model tespiti kullanici tarafindan kapatildi.",
            "tahminler": [],
            "en_iyi_tahmin": None,
        }

    vehicle_info = vehicle_info or {
        "status": "skipped",
        "message": "Hugging Face marka/model tespiti calistirilmadi.",
        "tahminler": [],
        "en_iyi_tahmin": None,
    }

    payload = {
        "hasar_tespitleri": all_damage_data,
        "arac_bilgisi": vehicle_info,
        "islenen_gorsel_sayisi": len(base64_images),
        "kullanilan_siniflar": DAMAGE_CLASSES,
        "yetkili_servis_acik_mi": use_authorized_service,
        "pipeline": {
            "yerel_hasar_modeli_kullanildi": use_damage_model,
            "hf_marka_model_kullanildi": use_vehicle_classifier,
            "gemini_raporlama_istendi": use_gemini,
            "gemini_api_key_var": bool((gemini_api_key or GEMINI_API_KEY).strip()),
            "gemini_api_cagrildi": False,
            "adim_sirasi": [
                "1_yerel_yolo_hasar_modeli",
                "2_huggingface_marka_model_modeli",
                "3_gemini_ai_raporlama_api",
            ],
        },
    }
    if use_gemini:
        try:
            step_started_at = time.perf_counter()
            payload["pipeline"]["gemini_api_cagrildi"] = True
            final_report = create_report(payload, annotated_base64_images, gemini_api_key)
            timings["gemini_saniye"] = time.perf_counter() - step_started_at
        except HTTPException as exc:
            timings["gemini_saniye"] = time.perf_counter() - step_started_at
            final_report = {
                "status": "error",
                "provider": "gemini",
                "message": exc.detail,
                "gemini_payload_ozeti": {
                    "model": GEMINI_MODEL,
                    "gorsel_sayisi": len(annotated_base64_images[:3]),
                    "hasar_dosyasi_sayisi": len(all_damage_data),
                    "arac_bilgisi_status": vehicle_info.get("status"),
                },
                "fallback_rapor": create_local_report(payload)["rapor"],
            }
    else:
        final_report = create_local_report(payload)

    return {
        "status": "success",
        "message": f"{len(base64_images)} gorsel pipeline uzerinden islendi.",
        "pipeline": payload["pipeline"],
        "islenen_gorsel_sayisi": len(base64_images),
        "hasar_tespitleri": all_damage_data,
        "arac_bilgisi": vehicle_info,
        "gemini_raporu": final_report,
        "cizimli_gorseller": annotated_base64_images,
        "sureler": {key: round(value, 2) for key, value in timings.items()},
    }
