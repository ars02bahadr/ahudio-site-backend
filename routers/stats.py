from fastapi import APIRouter, HTTPException, Depends
from decode import verify_token
from services.vapi_service import VAPIService
from schemas import DashboardStats, BasicStats, DetailedStats, CallTypeStats
from datetime import datetime, timedelta, timezone
from typing import List, Dict

router = APIRouter(prefix="/stats", tags=["İstatistikler"])


def calculate_basic_stats(calls: List[Dict]) -> BasicStats:
    """Temel istatistikleri hesapla"""
    total_calls = len(calls)
    successful_calls = 0
    failed_calls = 0
    active_calls = 0
    total_cost = 0.0
    
    for call in calls:
        status = call.get("status", "")
        ended_reason = call.get("endedReason", "")
        cost = call.get("cost", 0) or 0
        
        # Toplam maliyet
        if isinstance(cost, (int, float)):
            total_cost += float(cost)
        
        # Aktif çağrılar
        if status == "in-progress":
            active_calls += 1
        
        # Başarılı çağrılar
        if status == "ended" and (not ended_reason or "error" not in str(ended_reason).lower()):
            successful_calls += 1
        
        # Başarısız çağrılar
        if ended_reason and "error" in str(ended_reason).lower():
            failed_calls += 1
    
    return BasicStats(
        total_calls=total_calls,
        successful_calls=successful_calls,
        failed_calls=failed_calls,
        active_calls=active_calls,
        total_cost=round(total_cost, 2)
    )


def calculate_detailed_stats(calls: List[Dict], successful_calls: int, total_calls: int) -> DetailedStats:
    """Detaylı metrikleri hesapla"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    
    today_calls = 0
    week_calls = 0
    total_duration_seconds = 0
    duration_count = 0
    
    for call in calls:
        created_at_str = call.get("createdAt")
        if not created_at_str:
            continue
        
        try:
            # ISO formatını parse et
            if created_at_str.endswith('Z'):
                created_at_str = created_at_str.replace('Z', '+00:00')
            call_date = datetime.fromisoformat(created_at_str)
            
            # Bugünkü çağrılar
            if call_date >= today_start:
                today_calls += 1
            
            # Bu haftaki çağrılar
            if call_date >= week_start:
                week_calls += 1
            
            # Çağrı süresi hesapla (başarılı çağrılar için)
            status = call.get("status", "")
            ended_reason = call.get("endedReason", "")
            if status == "ended" and (not ended_reason or "error" not in str(ended_reason).lower()):
                # endedAt varsa kullan, yoksa createdAt ve updatedAt farkını al
                ended_at_str = call.get("endedAt") or call.get("updatedAt")
                if ended_at_str:
                    if ended_at_str.endswith('Z'):
                        ended_at_str = ended_at_str.replace('Z', '+00:00')
                    try:
                        ended_at = datetime.fromisoformat(ended_at_str)
                        duration = (ended_at - call_date).total_seconds()
                        if duration > 0:
                            total_duration_seconds += duration
                            duration_count += 1
                    except:
                        pass
        except Exception:
            continue
    
    # Ortalama çağrı süresi
    average_duration = None
    if duration_count > 0:
        avg_seconds = int(total_duration_seconds / duration_count)
        minutes = avg_seconds // 60
        seconds = avg_seconds % 60
        average_duration = f"{minutes:02d}:{seconds:02d}"
    
    # Başarı oranı
    success_rate = 0.0
    if total_calls > 0:
        success_rate = round((successful_calls / total_calls) * 100, 2)
    
    return DetailedStats(
        average_call_duration=average_duration,
        today_calls=today_calls,
        week_calls=week_calls,
        success_rate=success_rate
    )


def calculate_call_type_stats(calls: List[Dict]) -> CallTypeStats:
    """Çağrı türleri istatistiklerini hesapla"""
    web_call = 0
    outbound_phone = 0
    inbound_phone = 0
    
    for call in calls:
        call_type = call.get("type", "")
        if call_type == "webCall":
            web_call += 1
        elif call_type == "outboundPhoneCall":
            outbound_phone += 1
        elif call_type == "inboundPhoneCall":
            inbound_phone += 1
    
    return CallTypeStats(
        web_call=web_call,
        outbound_phone=outbound_phone,
        inbound_phone=inbound_phone
    )


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: str = Depends(verify_token)
):
    """Dashboard istatistiklerini getir - token gerekli"""
    vapi_service = VAPIService()
    
    try:
        calls = await vapi_service.get_calls()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VAPI'den çağrı verileri alınamadı: {str(e)}")
    
    # Temel istatistikler
    basic_stats = calculate_basic_stats(calls)
    
    # Detaylı metrikler
    detailed_stats = calculate_detailed_stats(calls, basic_stats.successful_calls, basic_stats.total_calls)
    
    # Çağrı türleri
    call_type_stats = calculate_call_type_stats(calls)
    
    return DashboardStats(
        basic_stats=basic_stats,
        detailed_stats=detailed_stats,
        call_type_stats=call_type_stats
    )

