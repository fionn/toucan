#!/usr/bin/env python3
"""Module for deploying canary tokens"""

import base64

# pylint: disable=import-error
import requests
from ansible.module_utils.basic import AnsibleModule # type: ignore
from ansible.module_utils import canary_core # type: ignore

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community"
}

DOCUMENTATION = """
---
module: canarytoken

short_description: Deploy canary tokens

version_added: "2.9"

description:
    - Deploy canary tokens on remote machines and register them with the canary console.

options:
    console:
        description: >
            Dictionary containing "domain" and "api_token" keys as strings.
            "domain" is the subdomain in <domain>.canary.tools.
            "api_token" is the token to authenticate to the associated console.domain.
        required: true
    token:
        description: >
            Dictionary containing "memo" and "kind" keys as strings,
            as well as other parameters specific to the kind of token.
        required: true
    persistent:
        description:
            - Keep the token registered in the console instead of immediately deleting it.
        required: false
        default: true
    fail:
        description:
            - Fail the deployment.
        required: false
        default: false
    old_token:
        description:
            - A dictionary containing key "content" with token_id to be deleted.
        required: false
    destroy_only:
        description:
            - Destroy the old token and don't deploy anything.
        required: false
        default: false

author: FF
"""

EXAMPLES = """
# basic deployment
- name: Generate tokens
    delegate_to: localhost
    canarytoken:
        console:
            domain: "{{ vars.console_domain }}"
            api_token: "{{ vars.console_api_token }}"
        persistent: false
        fail: false
        token:
            memo: "pdf-test-token-{{ inventory_hostname }}"
            kind: "pdf-acrobat-reader"
    register: result
- name: Deploy tokens
    copy:
        content: "{{ result.token.object }}"
        dest: /tmp/secret.pdf
        mode: 0644
"""

RETURN = """
token:
    description: >
        Dictionary, possibly empty if token failed to deploy,
        otherwise containing "object" (the raw token object)
        and "params" (the token input parameters)
    type: dict
    returned: always
"""

def modify_state(module: AnsibleModule, result: dict) -> dict:
    """Actual logic goes here"""

    canary = canary_core.CanaryAPI(**module.params["console"])

    try:
        old_token_id = base64.b64decode(module.params["old_token"]["content"],
                                        validate=True).decode("utf8")
        canary.destroy(old_token_id)
        result["msg"] += "Old token deleted from console"
    except (KeyError, requests.HTTPError, RuntimeError) as ex:
        result["msg"] += f"Failed to destroy old token {old_token_id}: {ex}"
        if module.params["destroy_only"]:
            module.fail_json(**result)
            return result

    if module.params["destroy_only"]:
        return result

    token_spec = module.params["token"]
    try:
        token = canary_core.generate_token(canary, token_spec)
        token_object = canary.download(token.canarytoken).content
        result["token"]["object"] = token_object
        result["token"]["params"] = module.params["token"]
        result["token"]["id"] = token.canarytoken
        result["changed"] = True
        if not module.params["persistent"]:
            token.delete()
            result["msg"] += f"New token {token.canarytoken} deleted from console"
    except Exception as ex: # pylint: disable=broad-except
        try:
            token.delete()
        except UnboundLocalError:
            pass
        result["msg"] = str(ex)
        module.fail_json(**result)

    return result

def run_module() -> None:
    """Entry point"""

    fields = {
        "console": {"required": True, "type": dict},
        "token": {"required": True, "type": dict},
        "persistent": {"default": True, "type": bool},
        "fail": {"default": False, "type": bool},
        "old_token": {"default": {}, "type": dict},
        "destroy_only": {"default": False, "type": bool}
    }

    result = {
        "changed": False,
        "msg": "",
        "token": {},
    }

    module = AnsibleModule(argument_spec=fields, supports_check_mode=True)

    if module.params["fail"]:
        result["msg"] = "You requested this to fail"
        module.fail_json(**result)

    if module.check_mode:
        module.exit_json(**result)

    result = modify_state(module, result)

    module.exit_json(**result)

if __name__ == "__main__":
    run_module()
