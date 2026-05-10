# Araç Hasar Analiz ve Raporlama API (Vehicle Damage Assessment AI)

Bu proje, araç görselleri ve videoları üzerinden yapay zeka kullanarak **otomatik hasar tespiti**, **marka/model tanıma** ve **maliyet hesaplama** işlemlerini gerçekleştiren tam kapsamlı bir uçtan uca (end-to-end) analiz platformudur.

Kullanıcılar sisteme araç fotoğrafları veya videoları yükleyerek saniyeler içinde onarım tavsiyeleri ve detaylı ekspertiz raporları alabilirler.

## 🚀 Özellikler

- **YOLO ile Yerel Hasar Tespiti**: Gelişmiş YOLO bilgisayarlı görü modeli sayesinde araç üzerindeki çizik, göçük, cam kırığı vb. hasarları yüksek doğrulukla bulur ve görsel üzerinde işaretler.
- **Hugging Face Araç Sınıflandırma**: Yüklenen görselden aracın marka ve modelini otomatik olarak tespit eder.
- **Gemini AI Destekli Raporlama**: Elde edilen tüm verileri (görseller, hasar türleri, marka modeli) harmanlayarak **2026 yılı fiyatlandırmalarına** göre yetkili/özel servis maliyet tahminli, profesyonel bir ekspertiz raporu sunar. (Model görseldeki ekstra hasarları da hesaba katarak maliyete ekler).
- **Modern ve Duyarlı Arayüz**: Gece/Gündüz modu destekli, sürükle-bırak özellikli ve animasyonlu modern bir web arayüzüne (FastAPI + Vanilla JS + CSS) sahiptir.
- **Offline / Local Fallback**: İnternet bağlantısı veya API erişimi olmasa dahi yerel kurallı (rule-based) sistem üzerinden çalışmaya devam ederek temel bir rapor üretir.

## 🛠️ Kullanılan Teknolojiler

- **Backend**: Python, FastAPI
- **Yapay Zeka (Görü)**: Ultralytics YOLO, PyTorch, Timm (Hugging Face)
- **Yapay Zeka (LLM)**: Google Gemini API
- **Frontend**: HTML5, Vanilla JavaScript, CSS3
- **Görüntü İşleme**: OpenCV, NumPy

## 📦 Kurulum

1. Depoyu klonlayın:
   ```bash
   git clone https://github.com/farukdnc27/Vehicle-Damage-Assessment-Classification-project.git
   cd Vehicle-Damage-Assessment-Classification-project
   ```

2. Gerekli kütüphaneleri yükleyin:
   ```bash
   pip install fastapi uvicorn ultralytics opencv-python numpy requests python-multipart timm torch torchvision huggingface_hub pillow
   ```

3. Gerekli Model Dosyalarını Ekleyin:
   - Proje ana dizinine eğitilmiş YOLO hasar modelinizi `best.pt` adıyla yerleştirin.
   - İsteğe bağlı olarak Hugging Face model ağırlığını (`vehicle_classifier.pth`) ana dizine ekleyin. (Eğer eklemezseniz API ilk çalışmasında kendisi internetten indirecektir).

## 🚀 Çalıştırma

API'yi ve web arayüzünü başlatmak için şu komutu çalıştırın:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Ardından tarayıcınızda `http://localhost:8000` adresine giderek uygulamayı kullanabilirsiniz.

## 💡 Kullanım

1. **Görsel Yükleme:** Arayüz üzerinden araç hasar görsellerini sisteme yükleyin.
2. **Ayarlar:** Arayüzdeki anahtarları (switch) kullanarak hasar modelini, marka/model tespitini ve Gemini raporunu isteğe bağlı olarak açıp kapatabilirsiniz. Yetkili servis modunu açarak OEM parça fiyatlarını aktif edebilirsiniz.
3. **Gemini Anahtarı:** Raporlama için bir Gemini API Key girin.
4. **Analiz:** "Analizi Başlat" butonuna tıklayın. Yapay zeka önce hasarları bulup görselde işaretleyecek, ardından aracın markasını tespit edip Gemini'ye yollayarak fiyatlandırılmış final ekspertiz raporunu önünüze getirecektir.
