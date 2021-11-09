#!/usr/bin/env python3
"""Canary PoC"""

import os
import sys
import json
import secrets
import contextlib
from typing import Any, Dict, Generator, Set

import requests

try:
    from ansible.module_utils import canarytools # type: ignore
except ModuleNotFoundError:
    import canarytools # type: ignore

def class_attributes(cls: type) -> Set[str]:
    """Return all public attributes of a class"""
    return set(getattr(cls, x) for x in dir(cls) if x[0] != "_")

class CanaryAPI:
    """Make direct API calls without the console"""

    def __init__(self, domain: str, api_token: str) -> None:
        self.console = canarytools.Console(domain, api_token)
        self._auth_token = self.console.api_key
        self.url = f"https://{self.console.domain}.canary.tools"
        self.path = "/api/v1/canarytoken/"

    def to_token_object(self, data: Dict[str, Any]) -> canarytools.CanaryToken:
        """Unify API responses by wrapping the JSON in this"""
        return canarytools.CanaryToken(self.console, data)

    def _get(self, path: str, params: Dict[str, Any], check: bool = True) -> requests.Response:
        """GET"""
        path = self.path + path
        response = requests.get(self.url + path, params)
        if check:
            response.raise_for_status()
        return response

    def _post(self, path: str, data: Dict[str, Any], check: bool = True) -> requests.Response:
        """POST"""
        path = self.path + path
        response = requests.post(self.url + path, data)
        if check:
            response.raise_for_status()
        return response

    def _delete(self, path: str, data: Dict[str, Any], check: bool = True) -> requests.Response:
        """DELETE"""
        path = self.path + path
        response = requests.delete(self.url + path, data=data)
        if check:
            response.raise_for_status()
        return response

    def list(self) -> requests.Response:
        """Get a list of token kinds that can be created"""
        path = "/api/v1/canarytokens/list" # note the different path
        response = requests.get(self.url + path,
                                {"auth_token": self._auth_token})
        response.raise_for_status()
        return response

    def fetch(self, token_id: str) -> dict:
        """Fetch token metadata"""
        params = {"auth_token": self._auth_token,
                  "canarytoken": token_id}
        return self._get("fetch", params).json()

    def download(self, token_id: str) -> requests.Response:
        """Get a token"""
        params = {"auth_token": self._auth_token,
                  "canarytoken": token_id}
        return self._get("download", params)

    def create(self, **kwargs: Any) -> canarytools.CanaryToken:
        """Create via direct API call"""
        params = {"auth_token": self._auth_token}
        params = {**params, **kwargs}
        return self.to_token_object(self._post("create", data=params).json()["canarytoken"])

    def destroy(self, token_id: str) -> None:
        """Destroy via direct API call"""
        params = {"auth_token": self._auth_token,
                  "canarytoken": token_id}
        response_dict = self._post("delete", params).json()
        if response_dict["result"] != "success":
            raise RuntimeError(response_dict["result"])

    def create_factory(self, memo: str) -> dict:
        """Create a token factory"""
        params = {"auth_token": self._auth_token, "memo": memo}
        return self._post("create_factory", data=params).json()

    def destroy_factory(self, factory_auth: str) -> requests.Response:
        """Destroy a token factory"""
        params = {"auth_token": self._auth_token,
                  "factory_auth": factory_auth}
        return self._delete("delete_factory", data=params)

    def print_token_data(self, token: canarytools.CanaryToken) -> None:
        """Dump a bunch of data about a given token"""
        print(token)
        metadata_response = self.fetch(token.canarytoken)
        print(json.dumps(metadata_response, indent=2))

    @contextlib.contextmanager
    def managed_token(self, **kwargs: Any) -> Generator[canarytools.CanaryToken, None, None]:
        """Destroy a token on exit, likely only useful for testing"""
        token = self.create(**kwargs)
        try:
            yield token
        finally:
            token.delete()
            print(f"Token {token.canarytoken}/{token.memo} destroyed",
                  file=sys.stderr)

def generate_token(canary: CanaryAPI, token_spec: Dict[str, Any],
                   ephemeral: bool = False) -> canarytools.CanaryToken:
    """Generate a token and return it"""
    memo = token_spec["memo"]
    kind = token_spec["kind"]

    if kind not in class_attributes(canarytools.CanaryTokenKinds):
        raise RuntimeError(f"Unknown token kind {kind}")

    parameters = dict()
    if token_spec.get("flock_id"):
        parameters["flock_id"] = token_spec["flock_id"]

    if kind in (canarytools.CanaryTokenKinds.SQL,
                canarytools.CanaryTokenKinds.SVN):
        raise RuntimeError(f"{kind} token is deprecated")

    if kind in (canarytools.CanaryTokenKinds.FASTREDIRECT,
                canarytools.CanaryTokenKinds.SLOWREDIRECT):
        parameters["browser_redirect_url"] = token_spec["browser_redirect_url"]
    if kind == canarytools.CanaryTokenKinds.CLONED_WEB:
        parameters["cloned_web"] = token_spec["cloned_web"]
    if kind == canarytools.CanaryTokenKinds.WEB_IMAGE:
        parameters["web_image"] = token_spec["web_image"]
        parameters["mimetype"] = token_spec["mimetype"]

    if not ephemeral:
        return canary.create(memo=memo, kind=kind, **parameters)
    with canary.managed_token(memo=memo, kind=kind, **parameters) as token:
        canary.print_token_data(token)
        return token

def main() -> None:
    """Entry point"""
    canary = CanaryAPI(os.environ["CANARY_DOMAIN"],
                       os.environ["CANARY_API_TOKEN"])

    session_string = secrets.token_hex(3)

    for kind in sorted(class_attributes(canarytools.CanaryTokenKinds)):
        token_spec = {"memo": f"poc-test-{kind}-{session_string}",
                      "kind": kind,
                      "browser_redirect_url": "https://example.com",
                      "cloned_web": "www.example.com"}

        if kind in (canarytools.CanaryTokenKinds.SQL,
                    canarytools.CanaryTokenKinds.SVN,
                    canarytools.CanaryTokenKinds.AWSS3,
                    canarytools.CanaryTokenKinds.WEB_IMAGE):
            print(f"Skipping {kind} token", file=sys.stderr)
            continue

        print(f"Generating {kind} token...")
        generate_token(canary, token_spec, ephemeral=True)

if __name__ == "__main__":
    main()
