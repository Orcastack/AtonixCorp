"""HTTP client for the AtonixCorp Developer Console Integration (DCI) API."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, BinaryIO
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SANDBOX_URL = "http://localhost:8000"
PRODUCTION_URL = "https://api.atonixcorp.com"


class AtonixCorpError(RuntimeError):
    """An API response that cannot be safely retried without user action."""

    def __init__(self, message: str, *, status_code: int | None = None, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


@dataclass(frozen=True)
class Credentials:
    access_token: str | None = None
    api_key: str | None = None

    def headers(self) -> dict[str, str]:
        if self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}
        if self.api_key:
            return {"X-API-Key": self.api_key}
        return {}


class AtonixCorpClient:
    """Secure DCI client with sandbox-first defaults and JSON error envelopes."""

    def __init__(self, *, base_url: str = SANDBOX_URL, credentials: Credentials | None = None, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.credentials = credentials or Credentials()
        self.timeout = timeout

    @classmethod
    def sandbox(cls, **kwargs):
        return cls(base_url=SANDBOX_URL, **kwargs)

    def with_access_token(self, access_token: str):
        return type(self)(base_url=self.base_url, credentials=Credentials(access_token=access_token), timeout=self.timeout)

    def login(self, *, api_key: str, organization_id: str) -> dict[str, Any]:
        payload = self.request("POST", "/auth/cli-login", json_body={"api_key": api_key, "organization_id": organization_id}, authenticated=False)
        self.credentials = Credentials(access_token=payload["access_token"])
        return payload

    def request(self, method: str, path: str, *, json_body: dict | None = None, query: dict | None = None, headers: dict | None = None, body: bytes | None = None, authenticated: bool = True) -> Any:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query, doseq=True)}"
        request_headers = {"Accept": "application/json", **(headers or {})}
        if authenticated:
            request_headers.update(self.credentials.headers())
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        request = Request(url, data=body, headers=request_headers, method=method.upper())
        try:
            with urlopen(request, timeout=self.timeout) as response:
                content = response.read()
                return self._decode(content, response.headers.get("Content-Type", ""))
        except HTTPError as error:
            content = error.read()
            details = self._decode(content, error.headers.get("Content-Type", ""))
            if isinstance(details, dict):
                envelope = details.get("error", details)
                message = envelope.get("message") or envelope.get("detail") or "AtonixCorp API request failed."
            else:
                message = "AtonixCorp API request failed."
            raise AtonixCorpError(message, status_code=error.code, details=details) from error
        except URLError as error:
            raise AtonixCorpError("Unable to reach the AtonixCorp API. Check the sandbox URL and network connection.") from error

    @staticmethod
    def _decode(content: bytes, content_type: str) -> Any:
        if not content:
            return None
        if "json" in content_type:
            return json.loads(content.decode("utf-8"))
        try:
            return json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return content

    # Enterprise entity and department operations.
    def create_entity(self, payload: dict) -> dict:
        return self.request("POST", "/api/entities/", json_body=payload)

    def list_entities(self, organization_id: int | None = None) -> Any:
        return self.request("GET", "/api/entities/", query={"organization_id": organization_id} if organization_id else None)

    def create_department(self, entity_id: int, payload: dict) -> dict:
        return self.request("POST", "/api/entity-departments/", json_body={"entity": entity_id, **payload})

    def update_department(self, department_id: int, payload: dict) -> dict:
        return self.request("PATCH", f"/api/entity-departments/{department_id}/", json_body=payload)

    def delete_department(self, department_id: int) -> None:
        self.request("DELETE", f"/api/entity-departments/{department_id}/")

    # Workspace, collaboration, and encrypted file operations.
    def create_workspace(self, payload: dict) -> dict:
        return self.request("POST", "/api/v1/workspaces", json_body=payload)

    def create_workspace_department(self, workspace_id: str, payload: dict) -> dict:
        return self.request("POST", f"/api/v1/workspaces/{workspace_id}/departments", json_body=payload)

    def schedule_meeting(self, workspace_id: str, payload: dict) -> dict:
        return self.request("POST", f"/api/v1/workspaces/{workspace_id}/meetings", json_body=payload)

    def upload_file(self, workspace_id: str, file_name: str, content: bytes, mime_type: str = "application/octet-stream", folder_id: str | None = None) -> dict:
        boundary = "atonixcorp-sdk-upload"
        fields = [
            ("content", file_name, mime_type, content),
            ("mime_type", None, None, mime_type.encode("utf-8")),
        ]
        if folder_id:
            fields.append(("folder_id", None, None, folder_id.encode("utf-8")))
        body = b"".join(self._multipart_part(boundary, *field) for field in fields) + f"--{boundary}--\r\n".encode()
        return self.request("POST", f"/api/v1/workspaces/{workspace_id}/files", body=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})

    @staticmethod
    def _multipart_part(boundary: str, field: str, filename: str | None, content_type: str | None, value: bytes) -> bytes:
        disposition = f'Content-Disposition: form-data; name="{field}"'
        if filename:
            disposition += f'; filename="{filename}"'
        content_header = f"\r\nContent-Type: {content_type}" if content_type else ""
        return f"--{boundary}\r\n{disposition}{content_header}\r\n\r\n".encode() + value + b"\r\n"

    def download_file(self, workspace_id: str, file_id: str) -> bytes:
        result = self.request("GET", f"/api/v1/workspaces/{workspace_id}/files/{file_id}")
        if not isinstance(result, bytes):
            raise AtonixCorpError("File download did not return binary content.")
        return result

    # Equity registry endpoints are scoped to their enterprise entity.
    def create_shareholder(self, entity_id: int, payload: dict) -> dict:
        return self.request("POST", f"/api/entities/{entity_id}/equity/shareholders", json_body=payload)

    def allocate_equity(self, entity_id: int, payload: dict) -> dict:
        return self.request("POST", f"/api/entities/{entity_id}/equity/holdings", json_body=payload)
