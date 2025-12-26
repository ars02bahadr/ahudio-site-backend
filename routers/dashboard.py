"""
Dashboard Router - Müşteri Odaklı Dashboard API'leri
Overview, Calls, Leads ve Assistant ayarları için endpoint'ler
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
import schemas
import models
from database import get_db
from decode import verify_token
from services.vapi_service import VAPIService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ==================== SCHEMAS ====================

class CallSummary(BaseModel):
    """Çağrı özeti"""
    id: str
    type: str  # inboundPhoneCall, outboundPhoneCall, webCall
    status: str
    duration_seconds: Optional[int] = None
    duration_formatted: Optional[str] = None  # "MM:SS" formatı
    cost: Optional[float] = None
    created_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    customer_phone: Optional[str] = None  # Masked: +90 5** *** **34
    summary: Optional[str] = None  # Konuşma özeti
    ended_reason: Optional[str] = None


class CallDetail(CallSummary):
    """Çağrı detayı - transcript içerir"""
    transcript: Optional[str] = None
    messages: Optional[List[dict]] = None
    analysis: Optional[dict] = None


class OverviewStats(BaseModel):
    """Overview istatistikleri"""
    # Ana metrikler
    total_calls: int
    successful_calls: int
    failed_calls: int
    active_calls: int
    total_cost: float
    
    # Zaman bazlı metrikler
    today_calls: int
    week_calls: int
    month_calls: int
    success_rate: float
    
    # Ortalama süre
    average_duration: Optional[str] = None  # "MM:SS"
    
    # Çağrı türleri
    inbound_calls: int
    outbound_calls: int
    web_calls: int


class DailyCallData(BaseModel):
    """Günlük çağrı verisi - grafik için"""
    date: str  # "2024-01-15"
    total: int
    successful: int
    failed: int


class WeeklyChartData(BaseModel):
    """Haftalık grafik verisi"""
    daily_data: List[DailyCallData]


class RecentCall(BaseModel):
    """Son konuşma özeti"""
    id: str
    type: str
    customer_phone: Optional[str] = None
    duration_formatted: Optional[str] = None
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    sentiment: Optional[str] = None  # positive, negative, neutral


class OverviewResponse(BaseModel):
    """Overview endpoint yanıtı"""
    stats: OverviewStats
    chart_data: WeeklyChartData
    recent_calls: List[RecentCall]


# Voice modelleri
class VoiceOption(BaseModel):
    """Ses modeli seçeneği"""
    id: str
    name: str
    gender: str  # male, female
    language: str
    preview_url: Optional[str] = None
    provider: str = "elevenlabs"
    description: Optional[str] = None


class VoiceOptionsResponse(BaseModel):
    """Ses modelleri listesi"""
    voices: List[VoiceOption]


# Asistan ayarları
class AssistantSettings(BaseModel):
    """Asistan davranış ayarları"""
    voice_id: Optional[str] = None
    flexibility: int = 50  # 0-100 (temperature mapping)
    humor: int = 30  # 0-100
    goal_focus: int = 50  # 0-100


class AssistantSettingsUpdate(BaseModel):
    """Asistan ayarları güncelleme"""
    voice_id: Optional[str] = None
    flexibility: Optional[int] = None  # 0-100
    humor: Optional[int] = None  # 0-100
    goal_focus: Optional[int] = None  # 0-100


class ExamplePhrase(BaseModel):
    """Örnek cümle"""
    humor_level: int
    goal_focus_level: int
    phrase: str


class AssistantSettingsResponse(BaseModel):
    """Asistan ayarları yanıtı"""
    current_settings: AssistantSettings
    voice_options: List[VoiceOption]
    flexibility_examples: List[str]
    humor_examples: List[ExamplePhrase]
    goal_focus_examples: List[ExamplePhrase]


# ==================== HELPER FUNCTIONS ====================

def mask_phone_number(phone: Optional[str]) -> Optional[str]:
    """Telefon numarasını maskele: +90 5** *** **34"""
    if not phone:
        return None
    
    # Sadece rakamları al
    digits = ''.join(filter(str.isdigit, phone))
    
    if len(digits) < 4:
        return "***"
    
    # Son 2 ve ilk 3-4 rakamı göster, ortayı maskele
    if len(digits) >= 10:
        # +90 5XX XXX XX34 formatı
        prefix = digits[:4] if digits.startswith('90') else digits[:3]
        suffix = digits[-2:]
        masked = f"+{prefix[0:2]} {prefix[2]}** *** **{suffix}"
        return masked
    else:
        return f"***{digits[-2:]}"


def format_duration(seconds: Optional[int]) -> Optional[str]:
    """Saniyeyi MM:SS formatına çevir"""
    if seconds is None or seconds < 0:
        return None
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def calculate_duration_seconds(start: datetime, end: datetime) -> int:
    """İki tarih arasındaki farkı saniye olarak hesapla"""
    if not start or not end:
        return 0
    diff = (end - start).total_seconds()
    return max(0, int(diff))


def get_sentiment_from_analysis(analysis: Optional[dict]) -> Optional[str]:
    """Analysis'ten sentiment çıkar"""
    if not analysis:
        return None
    return analysis.get("sentiment", analysis.get("successEvaluation"))


def generate_humor_examples(level: int) -> List[ExamplePhrase]:
    """Humor seviyesine göre örnek cümleler"""
    examples = [
        ExamplePhrase(humor_level=0, goal_focus_level=50, phrase="Randevunuz 15:00 için onaylandı. Başka bir konuda yardımcı olabilir miyim?"),
        ExamplePhrase(humor_level=30, goal_focus_level=50, phrase="Harika, randevunuz tamam! 15:00'te görüşmek üzere. Bir şey daha var mı sizin için yapabileceğim?"),
        ExamplePhrase(humor_level=50, goal_focus_level=50, phrase="Süper, randevunuz hazır! Sizi 15:00'te bekliyoruz, gecikmeyin ha! 😊 Başka nasıl yardımcı olabilirim?"),
        ExamplePhrase(humor_level=70, goal_focus_level=50, phrase="Tamam, not aldım! 15:00'te buluşuyoruz, kahvenizi hazırlarım! Bir isteğiniz daha var mı?"),
        ExamplePhrase(humor_level=100, goal_focus_level=50, phrase="Harikasınız! Randevunuz hazır, 15:00'te parti başlıyor! 🎉 Hadi bakalım, başka ne güzellikler yapabiliriz?"),
    ]
    return examples


def generate_goal_focus_examples(level: int) -> List[ExamplePhrase]:
    """Goal focus seviyesine göre örnek cümleler"""
    examples = [
        ExamplePhrase(humor_level=30, goal_focus_level=0, phrase="Anladım, düşünmeniz gerekiyor. İstediğiniz zaman bizi arayabilirsiniz."),
        ExamplePhrase(humor_level=30, goal_focus_level=30, phrase="Tabii, karar vermek için zaman alın. Ancak bu hafta özel bir kampanyamız var, bilginize."),
        ExamplePhrase(humor_level=30, goal_focus_level=50, phrase="Anlıyorum düşünmeniz gerektiğini. Şu anki kampanya cumaya kadar geçerli, kaçırmamanızı öneririm."),
        ExamplePhrase(humor_level=30, goal_focus_level=70, phrase="Düşünmenizi anlıyorum ama bu fırsat gerçekten kaçmaz. Size özel %20 indirim sunabilirim, ne dersiniz?"),
        ExamplePhrase(humor_level=30, goal_focus_level=100, phrase="Bu fırsatı bugün değerlendirmenizi şiddetle tavsiye ederim! Yarın bu fiyatlar geçerli olmayacak. Hemen randevunuzu oluşturalım mı?"),
    ]
    return examples


def generate_flexibility_examples() -> List[str]:
    """Flexibility (temperature) örnekleri"""
    return [
        "0-20: Çok katı - Sadece belirlenen konular hakkında konuşur, sapma yapmaz",
        "20-40: Düşük esneklik - Çoğunlukla konuda kalır, minimal sapmalar",
        "40-60: Orta - Gerektiğinde konudan sapabilir ama ana hedefe döner",
        "60-80: Esnek - Müşteri sohbetine ayak uydurur, doğal akış",
        "80-100: Çok esnek - Serbest sohbet, müşteri yönlendirir"
    ]


def map_flexibility_to_temperature(flexibility: int) -> float:
    """Flexibility değerini (0-100) temperature değerine (0.0-1.0) çevir"""
    return round(flexibility / 100, 2)


def map_temperature_to_flexibility(temperature: float) -> int:
    """Temperature değerini (0.0-1.0) flexibility değerine (0-100) çevir"""
    return int(temperature * 100)


# ==================== ENDPOINTS ====================

# OVERVIEW ENDPOINTS

@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """
    Dashboard overview - Temel istatistikler, grafikler ve son konuşmalar
    Token gerektirir
    """
    vapi_service = VAPIService()
    
    try:
        calls = await vapi_service.get_calls()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Çağrı verileri alınamadı: {str(e)}")
    
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)
    
    # İstatistikleri hesapla
    total_calls = len(calls)
    successful_calls = 0
    failed_calls = 0
    active_calls = 0
    total_cost = 0.0
    today_calls = 0
    week_calls = 0
    month_calls = 0
    inbound_calls = 0
    outbound_calls = 0
    web_calls = 0
    total_duration = 0
    duration_count = 0
    
    # Günlük veriler (son 7 gün)
    daily_data = {}
    for i in range(7):
        day = (today_start - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_data[day] = {"total": 0, "successful": 0, "failed": 0}
    
    # Son çağrılar
    recent_calls_raw = []
    
    for call in calls:
        status = call.get("status", "")
        ended_reason = call.get("endedReason", "")
        cost = call.get("cost", 0) or 0
        call_type = call.get("type", "")
        created_at_str = call.get("createdAt")
        
        # Maliyet
        if isinstance(cost, (int, float)):
            total_cost += float(cost)
        
        # Durumlar
        if status == "in-progress":
            active_calls += 1
        
        if status == "ended" and (not ended_reason or "error" not in str(ended_reason).lower()):
            successful_calls += 1
        
        if ended_reason and "error" in str(ended_reason).lower():
            failed_calls += 1
        
        # Çağrı türleri
        if call_type == "inboundPhoneCall":
            inbound_calls += 1
        elif call_type == "outboundPhoneCall":
            outbound_calls += 1
        elif call_type == "webCall":
            web_calls += 1
        
        # Tarih bazlı hesaplamalar
        if created_at_str:
            try:
                if created_at_str.endswith('Z'):
                    created_at_str = created_at_str.replace('Z', '+00:00')
                call_date = datetime.fromisoformat(created_at_str)
                
                if call_date >= today_start:
                    today_calls += 1
                if call_date >= week_start:
                    week_calls += 1
                if call_date >= month_start:
                    month_calls += 1
                
                # Günlük veri
                day_key = call_date.strftime("%Y-%m-%d")
                if day_key in daily_data:
                    daily_data[day_key]["total"] += 1
                    if status == "ended" and (not ended_reason or "error" not in str(ended_reason).lower()):
                        daily_data[day_key]["successful"] += 1
                    if ended_reason and "error" in str(ended_reason).lower():
                        daily_data[day_key]["failed"] += 1
                
                # Süre hesabı
                ended_at_str = call.get("endedAt") or call.get("updatedAt")
                if ended_at_str and status == "ended":
                    if ended_at_str.endswith('Z'):
                        ended_at_str = ended_at_str.replace('Z', '+00:00')
                    ended_at = datetime.fromisoformat(ended_at_str)
                    duration = (ended_at - call_date).total_seconds()
                    if duration > 0:
                        total_duration += duration
                        duration_count += 1
                
                # Son çağrılar için
                recent_calls_raw.append({
                    "call": call,
                    "created_at": call_date
                })
            except:
                pass
    
    # Ortalama süre
    average_duration = None
    if duration_count > 0:
        avg_seconds = int(total_duration / duration_count)
        average_duration = format_duration(avg_seconds)
    
    # Başarı oranı
    success_rate = round((successful_calls / total_calls * 100), 2) if total_calls > 0 else 0.0
    
    # Stats objesi
    stats = OverviewStats(
        total_calls=total_calls,
        successful_calls=successful_calls,
        failed_calls=failed_calls,
        active_calls=active_calls,
        total_cost=round(total_cost, 2),
        today_calls=today_calls,
        week_calls=week_calls,
        month_calls=month_calls,
        success_rate=success_rate,
        average_duration=average_duration,
        inbound_calls=inbound_calls,
        outbound_calls=outbound_calls,
        web_calls=web_calls
    )
    
    # Grafik verisi
    chart_data = WeeklyChartData(
        daily_data=[
            DailyCallData(
                date=date,
                total=data["total"],
                successful=data["successful"],
                failed=data["failed"]
            )
            for date, data in sorted(daily_data.items())
        ]
    )
    
    # Son 5 çağrı
    recent_calls_raw.sort(key=lambda x: x["created_at"], reverse=True)
    recent_calls = []
    for item in recent_calls_raw[:5]:
        call = item["call"]
        created_at = item["created_at"]
        
        # Süre hesapla
        duration_formatted = None
        ended_at_str = call.get("endedAt") or call.get("updatedAt")
        if ended_at_str:
            try:
                if ended_at_str.endswith('Z'):
                    ended_at_str = ended_at_str.replace('Z', '+00:00')
                ended_at = datetime.fromisoformat(ended_at_str)
                duration = int((ended_at - created_at).total_seconds())
                if duration > 0:
                    duration_formatted = format_duration(duration)
            except:
                pass
        
        # Telefon numarası (maskelenmiş)
        customer = call.get("customer", {})
        customer_phone = mask_phone_number(customer.get("number"))
        
        recent_calls.append(RecentCall(
            id=call.get("id", ""),
            type=call.get("type", ""),
            customer_phone=customer_phone,
            duration_formatted=duration_formatted,
            summary=call.get("summary"),
            created_at=created_at,
            sentiment=get_sentiment_from_analysis(call.get("analysis"))
        ))
    
    return OverviewResponse(
        stats=stats,
        chart_data=chart_data,
        recent_calls=recent_calls
    )


# CALLS ENDPOINTS

@router.get("/calls", response_model=List[CallSummary])
async def get_all_calls(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    call_type: Optional[str] = Query(None, description="inboundPhoneCall, outboundPhoneCall, webCall"),
    status: Optional[str] = Query(None, description="ended, in-progress"),
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """
    Tüm çağrıları listele - Token gerektirir
    Telefon numaraları maskelenir
    """
    vapi_service = VAPIService()
    
    try:
        calls = await vapi_service.get_calls()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Çağrı verileri alınamadı: {str(e)}")
    
    # Filtreleme
    filtered_calls = calls
    if call_type:
        filtered_calls = [c for c in filtered_calls if c.get("type") == call_type]
    if status:
        filtered_calls = [c for c in filtered_calls if c.get("status") == status]
    
    # Sıralama (en yeni önce)
    filtered_calls.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
    
    # Sayfalama
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paged_calls = filtered_calls[start_idx:end_idx]
    
    result = []
    for call in paged_calls:
        created_at = None
        ended_at = None
        duration_seconds = None
        duration_formatted = None
        
        created_at_str = call.get("createdAt")
        if created_at_str:
            try:
                if created_at_str.endswith('Z'):
                    created_at_str = created_at_str.replace('Z', '+00:00')
                created_at = datetime.fromisoformat(created_at_str)
            except:
                pass
        
        ended_at_str = call.get("endedAt") or call.get("updatedAt")
        if ended_at_str and call.get("status") == "ended":
            try:
                if ended_at_str.endswith('Z'):
                    ended_at_str = ended_at_str.replace('Z', '+00:00')
                ended_at = datetime.fromisoformat(ended_at_str)
                
                if created_at:
                    duration_seconds = calculate_duration_seconds(created_at, ended_at)
                    duration_formatted = format_duration(duration_seconds)
            except:
                pass
        
        # Telefon numarası (maskelenmiş)
        customer = call.get("customer", {})
        customer_phone = mask_phone_number(customer.get("number"))
        
        result.append(CallSummary(
            id=call.get("id", ""),
            type=call.get("type", ""),
            status=call.get("status", ""),
            duration_seconds=duration_seconds,
            duration_formatted=duration_formatted,
            cost=call.get("cost"),
            created_at=created_at,
            ended_at=ended_at,
            customer_phone=customer_phone,
            summary=call.get("summary"),
            ended_reason=call.get("endedReason")
        ))
    
    return result


@router.get("/calls/{call_id}", response_model=CallDetail)
async def get_call_detail(
    call_id: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """
    Tek bir çağrının detaylarını getir - Token gerektirir
    Transcript ve analiz bilgilerini içerir
    """
    vapi_service = VAPIService()
    
    try:
        # VAPI'den tüm çağrıları çek ve ID'ye göre filtrele
        calls = await vapi_service.get_calls()
        call = next((c for c in calls if c.get("id") == call_id), None)
        
        if not call:
            raise HTTPException(status_code=404, detail="Çağrı bulunamadı")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Çağrı verisi alınamadı: {str(e)}")
    
    created_at = None
    ended_at = None
    duration_seconds = None
    duration_formatted = None
    
    created_at_str = call.get("createdAt")
    if created_at_str:
        try:
            if created_at_str.endswith('Z'):
                created_at_str = created_at_str.replace('Z', '+00:00')
            created_at = datetime.fromisoformat(created_at_str)
        except:
            pass
    
    ended_at_str = call.get("endedAt") or call.get("updatedAt")
    if ended_at_str and call.get("status") == "ended":
        try:
            if ended_at_str.endswith('Z'):
                ended_at_str = ended_at_str.replace('Z', '+00:00')
            ended_at = datetime.fromisoformat(ended_at_str)
            
            if created_at:
                duration_seconds = calculate_duration_seconds(created_at, ended_at)
                duration_formatted = format_duration(duration_seconds)
        except:
            pass
    
    # Telefon numarası (maskelenmiş)
    customer = call.get("customer", {})
    customer_phone = mask_phone_number(customer.get("number"))
    
    return CallDetail(
        id=call.get("id", ""),
        type=call.get("type", ""),
        status=call.get("status", ""),
        duration_seconds=duration_seconds,
        duration_formatted=duration_formatted,
        cost=call.get("cost"),
        created_at=created_at,
        ended_at=ended_at,
        customer_phone=customer_phone,
        summary=call.get("summary"),
        ended_reason=call.get("endedReason"),
        transcript=call.get("transcript"),
        messages=call.get("messages"),
        analysis=call.get("analysis")
    )


# ASSISTANT SETTINGS ENDPOINTS

# Sabit ses modelleri - ElevenLabs'ten
VOICE_OPTIONS = [
    VoiceOption(
        id="EXAVITQu4vr4xnSDxMaL",
        name="Bella",
        gender="female",
        language="tr-TR",
        preview_url="/static/voices/bella_preview.wav",
        provider="elevenlabs",
        description="Sıcak ve samimi kadın sesi"
    ),
    VoiceOption(
        id="jsCqWAovK2LkecY7zXl4",
        name="Freya",
        gender="female",
        language="tr-TR",
        preview_url="/static/voices/freya_preview.wav",
        provider="elevenlabs",
        description="Profesyonel ve güven veren kadın sesi"
    ),
    VoiceOption(
        id="TX3LPaxmHKxFdv7VOQHJ",
        name="Liam",
        gender="male",
        language="tr-TR",
        preview_url="/static/voices/liam_preview.wav",
        provider="elevenlabs",
        description="Güçlü ve ikna edici erkek sesi"
    ),
    VoiceOption(
        id="pNInz6obpgDQGcFmaJgB",
        name="Adam",
        gender="male",
        language="tr-TR",
        preview_url="/static/voices/adam_preview.wav",
        provider="elevenlabs",
        description="Samimi ve rahat erkek sesi"
    ),
]


@router.get("/voices", response_model=VoiceOptionsResponse)
async def get_voice_options(
    current_user: str = Depends(verify_token)
):
    """
    Mevcut ses modellerini listele - Token gerektirir
    Preview URL'leri ile birlikte döner
    """
    return VoiceOptionsResponse(voices=VOICE_OPTIONS)


@router.get("/assistant/settings", response_model=AssistantSettingsResponse)
async def get_assistant_settings(
    assistant_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """
    Asistan ayarlarını getir - Token gerektirir
    Ses, flexibility, humor ve goal_focus değerlerini içerir
    """
    assistant = db.query(models.Assistant).filter(models.Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Asistan bulunamadı")
    
    # Voice bilgisini al
    voice = db.query(models.Voice).filter(models.Voice.assistant_id == assistant_id).first()
    current_voice_id = voice.voice_id if voice else None
    
    # Model bilgisinden temperature'ı al
    flexibility = 50  # default
    if assistant.model_data:
        try:
            model_data = json.loads(assistant.model_data)
            temperature = model_data.get("temperature", 0.5)
            flexibility = map_temperature_to_flexibility(temperature)
        except:
            pass
    
    # Humor ve goal_focus değerlerini DB'den al
    humor = assistant.humor if assistant.humor is not None else 30
    goal_focus = assistant.goal_focus if assistant.goal_focus is not None else 50
    
    current_settings = AssistantSettings(
        voice_id=current_voice_id,
        flexibility=flexibility,
        humor=humor,
        goal_focus=goal_focus
    )
    
    return AssistantSettingsResponse(
        current_settings=current_settings,
        voice_options=VOICE_OPTIONS,
        flexibility_examples=generate_flexibility_examples(),
        humor_examples=generate_humor_examples(humor),
        goal_focus_examples=generate_goal_focus_examples(goal_focus)
    )


@router.patch("/assistant/settings")
async def update_assistant_settings(
    assistant_id: int,
    settings: AssistantSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(verify_token)
):
    """
    Asistan ayarlarını güncelle - Token gerektirir
    
    - voice_id: ElevenLabs ses ID'si
    - flexibility: 0-100 arası (temperature'a map edilir)
    - humor: 0-100 arası (system prompt'a eklenir)
    - goal_focus: 0-100 arası (system prompt'a eklenir)
    """
    assistant = db.query(models.Assistant).filter(models.Assistant.id == assistant_id).first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Asistan bulunamadı")
    
    vapi_service = VAPIService()
    vapi_data = {}
    
    # Voice güncelleme
    if settings.voice_id is not None:
        # Voice ID'nin geçerli olduğunu kontrol et
        valid_voice = next((v for v in VOICE_OPTIONS if v.id == settings.voice_id), None)
        if not valid_voice:
            raise HTTPException(status_code=400, detail="Geçersiz ses modeli ID'si")
        
        # VAPI'ye gönder
        vapi_data["voice"] = {
            "voiceId": settings.voice_id,
            "provider": "elevenlabs"
        }
    
    # Flexibility (temperature) güncelleme
    if settings.flexibility is not None:
        if not 0 <= settings.flexibility <= 100:
            raise HTTPException(status_code=400, detail="Flexibility 0-100 arasında olmalı")
        
        temperature = map_flexibility_to_temperature(settings.flexibility)
        
        # Mevcut model bilgisini al
        if assistant.model_data:
            try:
                model_data = json.loads(assistant.model_data)
            except:
                model_data = {}
        else:
            model_data = {"model": "gpt-4o-mini", "provider": "openai"}
        
        model_data["temperature"] = temperature
        
        vapi_data["model"] = {
            "model": model_data.get("model", "gpt-4o-mini"),
            "provider": model_data.get("provider", "openai"),
            "temperature": temperature,
            "messages": model_data.get("messages", [])
        }
    
    # Humor ve Goal Focus (system prompt'a ekle)
    if settings.humor is not None or settings.goal_focus is not None:
        if settings.humor is not None and not 0 <= settings.humor <= 100:
            raise HTTPException(status_code=400, detail="Humor 0-100 arasında olmalı")
        if settings.goal_focus is not None and not 0 <= settings.goal_focus <= 100:
            raise HTTPException(status_code=400, detail="Goal Focus 0-100 arasında olmalı")
        
        # Mevcut model ve system prompt'u al
        if assistant.model_data:
            try:
                model_data = json.loads(assistant.model_data)
            except:
                model_data = {"model": "gpt-4o-mini", "provider": "openai"}
        else:
            model_data = {"model": "gpt-4o-mini", "provider": "openai"}
        
        messages = model_data.get("messages", [])
        
        # System message'ı bul veya oluştur
        system_msg_idx = None
        for i, msg in enumerate(messages):
            if msg.get("role") == "system":
                system_msg_idx = i
                break
        
        # Davranış parametrelerini prompt'a ekle
        behavior_text = "\n\n--- Davranış Parametreleri ---"
        if settings.humor is not None:
            humor_desc = "çok ciddi" if settings.humor < 20 else "ciddi" if settings.humor < 40 else "dengeli" if settings.humor < 60 else "samimi ve eğlenceli" if settings.humor < 80 else "çok eğlenceli ve playful"
            behavior_text += f"\nKonuşma tarzın: {humor_desc} (0-100 ölçeğinde {settings.humor} seviyesinde). "
        
        if settings.goal_focus is not None:
            goal_desc = "rahat, baskısız" if settings.goal_focus < 20 else "hafif yönlendirici" if settings.goal_focus < 40 else "dengeli ikna edici" if settings.goal_focus < 60 else "kararlı ve ikna edici" if settings.goal_focus < 80 else "çok ısrarcı ve hedef odaklı"
            behavior_text += f"\nSatış/ikna tarzın: {goal_desc} (0-100 ölçeğinde {settings.goal_focus} seviyesinde)."
        
        if system_msg_idx is not None:
            # Eski davranış parametrelerini temizle
            current_content = messages[system_msg_idx].get("content", "")
            if "--- Davranış Parametreleri ---" in current_content:
                current_content = current_content.split("--- Davranış Parametreleri ---")[0].strip()
            messages[system_msg_idx]["content"] = current_content + behavior_text
        else:
            messages.insert(0, {"role": "system", "content": behavior_text.strip()})
        
        if "model" not in vapi_data:
            vapi_data["model"] = {
                "model": model_data.get("model", "gpt-4o-mini"),
                "provider": model_data.get("provider", "openai"),
                "temperature": model_data.get("temperature", 0.5),
                "messages": messages
            }
        else:
            vapi_data["model"]["messages"] = messages
    
    # VAPI'ye gönder
    if vapi_data:
        try:
            await vapi_service.update_assistant(assistant.vapi_id, vapi_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"VAPI güncelleme hatası: {str(e)}")
        
        # Local DB'yi güncelle
        if "voice" in vapi_data:
            voice = db.query(models.Voice).filter(models.Voice.assistant_id == assistant_id).first()
            if voice:
                voice.voice_id = settings.voice_id
            else:
                new_voice = models.Voice(
                    assistant_id=assistant_id,
                    voice_id=settings.voice_id,
                    provider="elevenlabs"
                )
                db.add(new_voice)
        
        if "model" in vapi_data:
            assistant.model_data = json.dumps(vapi_data["model"])
        
        # Humor ve goal_focus'u DB'ye kaydet
        if settings.humor is not None:
            assistant.humor = settings.humor
        if settings.goal_focus is not None:
            assistant.goal_focus = settings.goal_focus
        
        db.commit()
    
    return {"status": "success", "message": "Asistan ayarları güncellendi"}
