# Basit FastAPI Tek-Request Projesi

Bu proje FastAPI ile oluşturulmuş, tek endpoint'e (POST /submissions/) sahip basit bir uygulamadır.
Gönderilen veriler SQLite (`data.db`) içine kaydedilir.

İstek gövdesi (JSON):
```json
{
  "name": "İsim Soyisim",
  "email": "ornek@mail.com",
  "company": "Şirket Adı",
  "business_type": "limited_company",
  "message": "Mesajınız"
}
```

İzin verilen business_type değerleri (enum):
- "sole_proprietorship"
- "limited_company"
- "joint_stock"
- "non_profit"
- "other"

Çalıştırma:
1. Sanal ortam oluştur (opsiyonel)
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows

2. Bağımlılıkları yükle:
   pip install -r requirements.txt

3. Uygulamayı çalıştır:
   uvicorn main:app --reload

API dokümantasyonu:
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

Örnek curl:
```bash
curl -X POST "http://127.0.0.1:8000/submissions/" -H "Content-Type: application/json" -d '{
  "name": "Ali Veli",
  "email": "ali@example.com",
  "company": "Örnek A.Ş.",
  "business_type": "limited_company",
  "message": "Merhaba, bilgi almak istiyorum."
}'
```

Notlar:
- Şu an SQLite (`data.db`) kullanılıyor; production için PostgreSQL/MySQL tercih edilebilir.
- Tekrar eden e-posta kontrolü main.py içinde örnek olarak kondu. İstersen bunu kaldırabilirsin.