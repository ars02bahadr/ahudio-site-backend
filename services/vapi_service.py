import httpx
import json
from typing import List, Dict, Optional
from datetime import datetime

VAPI_BASE_URL = "https://api.vapi.ai"
VAPI_TOKEN = "23ef3d6b-4e0a-48cf-8842-2125ced29e44"

class VAPIService:
    def __init__(self):
        self.base_url = VAPI_BASE_URL
        self.token = VAPI_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    async def get_assistants(self) -> List[Dict]:
        """VAPI'den tüm asistanları getir"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/assistant",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_assistant(self, assistant_id: str) -> Dict:
        """VAPI'den belirli bir asistanı getir"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/assistant/{assistant_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def create_assistant(self, data: Dict) -> Dict:
        """VAPI'de yeni asistan oluştur"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/assistant",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            return response.json()
    
    async def update_assistant(self, assistant_id: str, data: Dict) -> Dict:
        """VAPI'de asistanı güncelle (PATCH)"""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/assistant/{assistant_id}",
                headers=self.headers,
                json=data
            )
            if response.status_code >= 400:
                # Daha detaylı hata mesajı için response body'yi ekle
                error_detail = f"{response.status_code} {response.reason_phrase}"
                try:
                    error_body = response.json()
                    # Model hatası için özel mesaj formatla
                    if isinstance(error_body, dict) and "message" in error_body:
                        if isinstance(error_body["message"], list) and len(error_body["message"]) > 0:
                            message = error_body["message"][0]
                            if "must be one of" in message:
                                error_detail = f"{error_detail}\n{message}"
                            else:
                                error_detail = f"{error_detail}\n{error_body}"
                        else:
                            error_detail = f"{error_detail}\n{error_body}"
                    else:
                        error_detail = f"{error_detail}\n{error_body}"
                except:
                    error_detail = f"{error_detail}\nResponse text: {response.text}"
                raise Exception(error_detail)
            return response.json()
    
    async def delete_assistant(self, assistant_id: str) -> None:
        """VAPI'den asistanı sil"""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/assistant/{assistant_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return None
    
    # Phone Number Methods
    async def get_phone_numbers(self) -> List[Dict]:
        """VAPI'den tüm telefon numaralarını getir"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/phone-number",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_phone_number(self, phone_id: str) -> Dict:
        """VAPI'den belirli bir telefon numarasını getir"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/phone-number/{phone_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def create_phone_number(self, data: Dict) -> Dict:
        """VAPI'de yeni telefon numarası oluştur"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/phone-number",
                headers=self.headers,
                json=data
            )
            if response.status_code >= 400:
                error_detail = f"{response.status_code} {response.reason_phrase}"
                try:
                    error_body = response.json()
                    error_detail = f"{error_detail}\nResponse body: {error_body}"
                except:
                    error_detail = f"{error_detail}\nResponse text: {response.text}"
                raise Exception(error_detail)
            return response.json()
    
    async def update_phone_number(self, phone_id: str, data: Dict) -> Dict:
        """VAPI'de telefon numarasını güncelle (PATCH)"""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/phone-number/{phone_id}",
                headers=self.headers,
                json=data
            )
            if response.status_code >= 400:
                error_detail = f"{response.status_code} {response.reason_phrase}"
                try:
                    error_body = response.json()
                    error_detail = f"{error_detail}\nResponse body: {error_body}"
                except:
                    error_detail = f"{error_detail}\nResponse text: {response.text}"
                raise Exception(error_detail)
            return response.json()
    
    async def delete_phone_number(self, phone_id: str) -> None:
        """VAPI'den telefon numarasını sil"""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/phone-number/{phone_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return None
    
    # Call Methods
    async def get_calls(self) -> List[Dict]:
        """VAPI'den tüm çağrıları getir"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/call",
                headers=self.headers
            )
            if response.status_code >= 400:
                error_detail = f"{response.status_code} {response.reason_phrase}"
                try:
                    error_body = response.json()
                    error_detail = f"{error_detail}\n{error_body}"
                except:
                    error_detail = f"{error_detail}\nResponse text: {response.text}"
                raise Exception(error_detail)
            return response.json()
    
    @staticmethod
    def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """ISO formatındaki datetime string'ini parse et"""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except:
            return None

