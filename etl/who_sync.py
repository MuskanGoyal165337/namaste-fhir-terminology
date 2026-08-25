import os
import time
import logging
from typing import Dict, List, Any, Optional
import httpx

logger = logging.getLogger("ayush_emr.etl.who_sync")

class WHOAPIError(Exception):
    """Custom exception for WHO ICD-11 API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}

class MockWHOProvider:
    """Mock provider for testing WHO ICD-11 sync offline without external network dependency."""

    def __init__(self):
        self.mock_token = "mock_who_bearer_token_xyz123"
        self.mock_concepts = [
            {
                "code": "TM2.001",
                "title": "Cough in Traditional Medicine",
                "definition": "Traditional medicine diagnostic category for cough conditions.",
                "system_uri": "http://id.who.int/icd/release/11/2024-01/mms",
                "release_date": "2024-01-15"
            },
            {
                "code": "TM2.002",
                "title": "Fever in Traditional Medicine",
                "definition": "Traditional medicine diagnostic category for febrile conditions.",
                "system_uri": "http://id.who.int/icd/release/11/2024-01/mms",
                "release_date": "2024-01-15"
            },
            {
                "code": "TM2.003",
                "title": "Diarrhea in Traditional Medicine",
                "definition": "Traditional medicine diagnostic category for diarrheal conditions.",
                "system_uri": "http://id.who.int/icd/release/11/2024-01/mms",
                "release_date": "2024-01-15"
            }
        ]

    def get_token(self) -> str:
        return "mock_who_bearer_token_xyz123"

    def fetch_tm2_catalog(self, release_id: str = "2024-01") -> Dict[str, Any]:
        return {
            "release_id": release_id,
            "version": "2024-01",
            "concept_count": len(self.mock_concepts),
            "concepts": self.mock_concepts
        }

    def fetch_delta_updates(self, since_version: str) -> Dict[str, Any]:
        return {
            "since_version": since_version,
            "current_version": "2024-01",
            "has_changes": True,
            "updated_concepts": self.mock_concepts[:1],
            "deleted_codes": []
        }


class WHOICDClient:
    """
    REST adapter for WHO ICD-11 MMS API integration.
    Supports OAuth 2.0, retry logic, rate limit handling, and delta synchronization.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        timeout: float = 10.0,
        max_retries: int = 3,
        use_mock: Optional[bool] = None
    ):
        self.base_url = base_url or os.getenv("WHO_API_URL", "https://id.who.int/icd/release/11/mms")
        self.token_url = token_url or os.getenv("WHO_TOKEN_URL", "https://icdaccessmanagement.who.int/connect/token")
        self.client_id = client_id if client_id is not None else os.getenv("WHO_CLIENT_ID", "")
        self.client_secret = client_secret if client_secret is not None else os.getenv("WHO_CLIENT_SECRET", "")
        self.timeout = timeout
        self.max_retries = max_retries
        if use_mock is not None:
            self.use_mock = use_mock
        else:
            self.use_mock = os.getenv("WHO_USE_MOCK", "true").lower() == "true"
        self._token: Optional[str] = None
        self._token_expiry: float = 0.0
        self.mock_provider = MockWHOProvider() if self.use_mock else None

    def authenticate(self) -> str:
        """Obtains OAuth 2.0 Bearer token using client_credentials grant."""
        if self.use_mock:
            self._token = self.mock_provider.get_token()
            return self._token

        if self._token and time.time() < self._token_expiry:
            return self._token

        if not self.client_id or not self.client_secret:
            raise WHOAPIError("WHO Client ID and Client Secret must be configured in environment.")

        data = {
            "grant_type": "client_credentials",
            "scope": "icdapi_access"
        }
        auth = (self.client_id, self.client_secret)

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.token_url, data=data, auth=auth)
                if response.status_code != 200:
                    raise WHOAPIError(
                        f"Authentication failed: {response.text}",
                        status_code=response.status_code
                    )
                payload = response.json()
                self._token = payload.get("access_token")
                expires_in = payload.get("expires_in", 3600)
                self._token_expiry = time.time() + expires_in - 60
                return self._token
        except httpx.HTTPError as e:
            raise WHOAPIError(f"Network error during WHO authentication: {e}")

    def _send_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Sends authenticated HTTP request with retry logic and 429 rate limit backoff."""
        if self.use_mock:
            if "tm2" in endpoint:
                return self.mock_provider.fetch_tm2_catalog()
            return {"status": "ok"}

        token = self.authenticate()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Accept-Language": "en",
            "API-Version": "v2"
        }
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.request(method, url, headers=headers, params=params)

                    # Handle Rate Limiting (HTTP 429)
                    if response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", 2))
                        logger.warning(f"WHO API rate limited (429). Retrying in {retry_after}s...")
                        time.sleep(retry_after)
                        continue

                    if response.status_code >= 400:
                        raise WHOAPIError(
                            f"WHO API request failed: {response.text}",
                            status_code=response.status_code
                        )

                    return response.json()
            except httpx.HTTPError as e:
                if attempt == self.max_retries:
                    raise WHOAPIError(f"Failed to connect to WHO API after {self.max_retries} attempts: {e}")
                time.sleep(1.0 * attempt)

        raise WHOAPIError("Exhausted retries without response.")

    def fetch_tm2_chapter(self, release_id: str = "2024-01") -> Dict[str, Any]:
        """Fetches ICD-11 Traditional Medicine Module 2 concepts."""
        if self.use_mock:
            return self.mock_provider.fetch_tm2_catalog(release_id=release_id)

        endpoint = f"/{release_id}/mms/chapter/tm2"
        return self._send_request("GET", endpoint)

    def fetch_delta_sync(self, since_version: str) -> Dict[str, Any]:
        """Fetches incremental updates released after since_version."""
        if self.use_mock:
            return self.mock_provider.fetch_delta_updates(since_version)

        endpoint = "/delta"
        return self._send_request("GET", endpoint, params={"since": since_version})
