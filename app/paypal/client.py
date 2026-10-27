import os

import httpx
from dotenv import load_dotenv


class PayPalClient:
    def __init__(self):
        load_dotenv()
        self.client_id = os.getenv("PAYPAL_CLIENT_ID")
        self.client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
        self.base_url = os.getenv(
            "PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com"
        ).rstrip("/")

    def get_access_token(self):
        """Request an OAuth client-credentials token from PayPal."""
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "PayPal credentials are missing. Set PAYPAL_CLIENT_ID and "
                "PAYPAL_CLIENT_SECRET in the environment or .env file."
            )

        url = f"{self.base_url}/v1/oauth2/token"

        try:
            response = httpx.post(
                url,
                auth=(self.client_id, self.client_secret),
                headers={
                    "Accept": "application/json",
                    "Accept-Language": "en_US",
                },
                data={"grant_type": "client_credentials"},
                timeout=20.0,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            detail = self._error_detail(error.response)
            raise RuntimeError(
                "PayPal OAuth request failed "
                f"(HTTP {error.response.status_code}): {detail}"
            ) from None
        except httpx.RequestError as error:
            raise RuntimeError(
                "Could not connect to PayPal OAuth endpoint "
                f"({error.__class__.__name__}). Check the network and "
                "PAYPAL_BASE_URL."
            ) from None

        try:
            data = response.json()
        except ValueError:
            raise RuntimeError("PayPal OAuth returned invalid JSON.") from None

        access_token = data.get("access_token") if isinstance(data, dict) else None
        if not access_token:
            raise RuntimeError(
                "PayPal OAuth response did not include an access token."
            )

        return access_token

    def _error_detail(self, response):
        """Return a short PayPal error message with configured credentials redacted."""
        try:
            payload = response.json()
        except ValueError:
            payload = {}

        if isinstance(payload, dict):
            detail = payload.get("error_description") or payload.get("message") or payload.get("error")
        else:
            detail = None

        if not detail:
            detail = "PayPal rejected the OAuth request."

        detail = str(detail)
        for credential in (self.client_secret, self.client_id):
            if credential:
                detail = detail.replace(credential, "[REDACTED]")
        return detail
