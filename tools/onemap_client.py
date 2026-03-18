import os
import requests
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class OneMapClient:
    def __init__(self):
        self.email = os.getenv("ONEMAP_EMAIL")
        self.password = os.getenv("ONEMAP_PASSWORD")
        self.token = None
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"}

    def _get_token(self):
        if not self.token and self.email and self.password:
            try:
                resp = requests.post("https://www.onemap.gov.sg/api/auth/post/getToken", json={
                    "email": self.email,
                    "password": self.password
                }, headers=self.headers)
                if resp.status_code == 200:
                    self.token = resp.json().get("access_token")
                    logging.info("OneMap Token acquired successfully.")
                else:
                    logging.error(f"OneMap Auth Failed: {resp.status_code} - {resp.text}")
            except Exception as e:
                logging.error(f"OneMap Auth Error: {e}")

    def get_planning_area(self, lat: float, lon: float) -> Optional[str]:
        """Resolve Planning Area from coordinates using OneMap API."""
        self._get_token()
        if not self.token:
            return None
        
        try:
            h = self.headers.copy()
            h["Authorization"] = self.token
            
            # Note: Parameter name is 'log' for longitude
            url = f"https://www.onemap.gov.sg/api/public/popapi/getPlanningarea?lat={lat}&log={lon}"
            logging.info(f"Querying OneMap: {url}")
            
            res = requests.get(url, headers=h)

            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("pln_area_n")
                elif isinstance(data, dict):
                    return data.get("pln_area_n")
            else:
                logging.error(f"OneMap Planning Area API failed: {res.status_code} - {res.text}")
        except Exception as e:
            logging.error(f"OneMap Planning Area Error: {e}")
            
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = OneMapClient()
    area = client.get_planning_area(1.2892592, 103.8482726) # Clarke Quay
    print(f"Planning Area: {area}")
