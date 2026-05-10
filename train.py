from ultralytics import YOLO

def train_yolo11s_seg():
    model = YOLO("models/yolo11s-seg.pt")

    model.train(
        data="../data1/data.yaml",  # dataset yaml yolun
        epochs=70,               # Eğitim süresi
        imgsz=640,                 # Görüntü boyutu (640x640 önerilir nano için)
        batch=16,                  # RTX 4060 için ideal batch size
        patience=20,               # Early stopping sabrı
        verbose=False,              # Eğitim sırasında detaylı çıktı
        optimizer="AdamW",         # Daha stabil ve iyi sonuçlar için
        lr0=0.001,                 # Başlangıç öğrenme oranı
        lrf=0.01,                  # Öğrenme oranı son değeri (cosine annealing)
        weight_decay=0.001,        # Ağırlık çürümesi (düzenleme)
        cos_lr=True,               # Cosine LR schedule kullan
        augment=True,              # Veri augmentasyonu aktif
        device=0,                  # GPU id (0 = ilk GPU)
        project="..data1/vehicle-damage-assessment",  # Çıktı klasörü
        name="vehicle-damage-assessment",  # Eğitim adı
        cache=False,                # Dataset önbelleğe al
        workers=8                  # Veri yükleyici işçi sayısı (işlemci çekirdeklerine göre ayarla)
    )

if __name__ == "__main__":
    train_yolo11s_seg()