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
            response.raise_for_status()
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
            response.raise_for_status()
            return response.json()
    
    async def update_phone_number(self, phone_id: str, data: Dict) -> Dict:
        """VAPI'de telefon numarasını güncelle (PATCH)"""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/phone-number/{phone_id}",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
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
    
    @staticmethod
    def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        """ISO formatındaki datetime string'ini parse et"""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except:
            return None

