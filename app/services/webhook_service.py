import httpx
import os
from typing import Dict, Any
from app.utils.logger import app_logger

class WebhookService:
    def __init__(self):
        self.webhook_url = os.getenv("FACEBOOK_WEBHOOK_URL","https://dungcao1.app.n8n.cloud/webhook/ff25c7f4-0279-4f76-a12a-caecbf188f52")
    
    async def send_facebook_webhook(self, answer: str, sender_id: int, recipient_id: int) -> bool:
        """Send webhook to Facebook with answer and IDs"""
        if not self.webhook_url:
            app_logger.warning("Facebook webhook URL not configured")
            return False
        
        try:
            payload = {
                "answer": answer,
                "sender_id": sender_id,
                "recipient_id": recipient_id
            }
            print(payload)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    headers={
                        "accept": "application/json",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()
                app_logger.info(f"Webhook sent successfully: {response.status_code}")
                return True
                
        except Exception as e:
            app_logger.error(f"Failed to send webhook: {e}")
            return False

webhook_service = WebhookService()