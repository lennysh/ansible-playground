#!/usr/bin/env python3
# Copyright: (c) 2023, Jordan Borean (@jborean93) — MSDSManagedPassword parsing
# Copyright: (c) 2026, ansible-playground demo — ldap3 retrieval wrapper
# MIT License — see demo-gmsa-winrm/README.md (gist attribution)
#
# Retrieve a gMSA msDS-ManagedPassword blob from AD and derive WinRM NTLM credentials.
# Based on https://gist.github.com/jborean93/7634153074c223cc792ddd04c665db47

from __future__ import annotations

import argparse
import base64
import dataclasses
import datetime
import hashlib
import json
import sys
from typing import Any

import ldap3
from ldap3.core.exceptions import LDAPException


@dataclasses.dataclass(frozen=True)
class MSDSManagedPassword:
    """https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-adts/a9019740-3d73-46ef-a9ae-3ea8eb86ac2e"""

    version: int
    current_password: bytes
    previous_password: bytes
    query_password_interval: datetime.timedelta
    unchanged_password_interval: datetime.timedelta

    @classmethod
    def unpack(cls, data: bytearray | bytes | memoryview) -> MSDSManagedPassword:
        view = memoryview(data)

        version = int.from_bytes(view[:2], byteorder="little", signed=False)
        current_password_offset = int.from_bytes(view[8:10], byteorder="little", signed=False)
        previous_password_offset = int.from_bytes(view[10:12], byteorder="little", signed=False)
        query_password_offset = int.from_bytes(view[12:14], byteorder="little", signed=False)
        unchanged_interval_offset = int.from_bytes(view[14:16], byteorder="little", signed=False)

        current_password = cls._get_null_terminated_string(view, current_password_offset)
        previous_password = cls._get_null_terminated_string(view, previous_password_offset)

        query_password_interval = int.from_bytes(
            view[query_password_offset : query_password_offset + 8],
            byteorder="little",
            signed=False,
        )
        unchanged_password_interval = int.from_bytes(
            view[unchanged_interval_offset : unchanged_interval_offset + 8],
            byteorder="little",
            signed=False,
        )

        return MSDSManagedPassword(
            version=version,
            current_password=current_password,
            previous_password=previous_password,
            query_password_interval=datetime.timedelta(microseconds=query_password_interval / 10),
            unchanged_password_interval=datetime.timedelta(
                microseconds=unchanged_password_interval / 10
            ),
        )

    @classmethod
    def _get_null_terminated_string(cls, view: memoryview, offset: int) -> bytes:
        if offset == 0:
            return b""

        data = view[offset:].tobytes()
        return data[: data.index(b"\x00\x00")]


def md4(data: bytes) -> bytes:
    return hashlib.new("md4", data).digest()


def nt_hash_password(managed_password: bytes) -> str:
    """pyspnego / pywinrm NTLM hash form (empty LM hash + NT hash)."""
    nt_hash = md4(managed_password)
    return f"00000000000000000000000000000000:{base64.b16encode(nt_hash).decode()}"


def bind_user(bind_type: str, domain: str, username: str) -> str:
    if "@" in username:
        return username
    if "\\" in username:
        return username
    if bind_type == "ntlm":
        return f"{domain}\\{username}"
    return username


def fetch_managed_password(
    *,
    server: str,
    port: int,
    use_ssl: bool,
    start_tls: bool,
    bind_type: str,
    domain: str,
    username: str,
    password: str,
    search_base: str,
    sam_account_name: str,
) -> MSDSManagedPassword:
    sam = sam_account_name if sam_account_name.endswith("$") else f"{sam_account_name}$"
    user = bind_user(bind_type, domain, username)

    if bind_type == "ntlm":
        auth = ldap3.NTLM
    elif bind_type == "simple":
        auth = ldap3.SIMPLE
    else:
        raise ValueError(f"Unsupported bind_type: {bind_type}")

    conn = ldap3.Connection(
        ldap3.Server(server, port=port, use_ssl=use_ssl, get_info=ldap3.NONE),
        user=user,
        password=password,
        authentication=auth,
        auto_bind=False,
    )
    try:
        if start_tls and not use_ssl:
            conn.open()
            conn.start_tls()
        if not conn.bind():
            raise LDAPException(conn.result)

        conn.search(
            search_base=search_base,
            search_filter=f"(sAMAccountName={sam})",
            search_scope=ldap3.SUBTREE,
            attributes=["msDS-ManagedPassword", "sAMAccountName", "userPrincipalName"],
        )
        if not conn.entries:
            raise LDAPException(f"No directory object found for sAMAccountName={sam}")

        entry = conn.entries[0]
        blob = entry["msDS-ManagedPassword"].value
        if not blob:
            raise LDAPException(
                f"msDS-ManagedPassword is empty for {sam}. "
                "Ensure the lookup principal is in PrincipalsAllowedToRetrieveManagedPassword."
            )
        return MSDSManagedPassword.unpack(blob)
    finally:
        conn.unbind()


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch gMSA password from Active Directory")
    parser.add_argument("--server", required=True, help="LDAP server hostname or IP")
    parser.add_argument("--port", type=int, default=389)
    parser.add_argument("--use-ssl", action="store_true", help="LDAPS (port 636 typical)")
    parser.add_argument("--start-tls", action="store_true", help="Upgrade ldap:// with StartTLS")
    parser.add_argument("--bind-type", choices=["ntlm", "simple"], default="ntlm")
    parser.add_argument("--domain", required=True, help="NetBIOS or DNS domain for bind")
    parser.add_argument("--username", required=True, help="Lookup account (UPN or sAMAccountName)")
    parser.add_argument("--password", required=True, help="Lookup account password")
    parser.add_argument("--search-base", required=True, help="LDAP search base, e.g. DC=example,DC=com")
    parser.add_argument("--sam-account-name", required=True, help="gMSA name without trailing $")
    parser.add_argument("--realm", required=True, help="Kerberos realm / UPN suffix, e.g. EXAMPLE.COM")
    args = parser.parse_args()

    try:
        managed = fetch_managed_password(
            server=args.server,
            port=args.port,
            use_ssl=args.use_ssl,
            start_tls=args.start_tls,
            bind_type=args.bind_type,
            domain=args.domain,
            username=args.username,
            password=args.password,
            search_base=args.search_base,
            sam_account_name=args.sam_account_name,
        )
        sam = args.sam_account_name if args.sam_account_name.endswith("$") else f"{args.sam_account_name}$"
        upn = f"{sam}@{args.realm}"
        payload: dict[str, Any] = {
            "success": True,
            "sam_account_name": sam,
            "upn": upn,
            "ntlm_password": nt_hash_password(managed.current_password),
            "password_version": managed.version,
        }
        json.dump(payload, sys.stdout)
        return 0
    except Exception as exc:  # noqa: BLE001 — surface LDAP errors to Ansible
        json.dump({"success": False, "error": str(exc)}, sys.stdout)
        return 1


if __name__ == "__main__":
    sys.exit(main())
