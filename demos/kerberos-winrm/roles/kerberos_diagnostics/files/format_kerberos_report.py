#!/usr/bin/env python3
"""Format raw kerberos_diagnostics EE log into a readable report."""

from __future__ import annotations

import argparse
import re
import sys
from typing import List, Optional, Tuple

WIDTH = 78
BAR = "=" * WIDTH
THIN = "-" * WIDTH
DOTS = "." * 18

MARK_BEFORE = "========== SNAPSHOT: BEFORE =========="
MARK_KINIT = "========== KINIT =========="
MARK_AFTER = "========== SNAPSHOT: AFTER =========="
MARK_START = re.compile(r"^=== EE KERBEROS DIAGNOSTICS START \((.+)\) ===\s*$")
HEADER = re.compile(r"^--- (.+?) ---\s*$")
BANNER = re.compile(r"^={3,}.+={3,}\s*$")


def split_major(raw: str) -> Tuple[str, str, str, str, Optional[str]]:
    started = None
    for line in raw.splitlines():
        m = MARK_START.match(line)
        if m:
            started = m.group(1)
            break

    env, before, kinit, after = raw, "", "", ""
    if MARK_BEFORE in raw:
        env, rest = raw.split(MARK_BEFORE, 1)
        before = rest
        if MARK_KINIT in before:
            before, kinit = before.split(MARK_KINIT, 1)
        elif MARK_AFTER in before:
            before, after = before.split(MARK_AFTER, 1)
            after = MARK_AFTER + after
        if MARK_AFTER in kinit:
            kinit, after_tail = kinit.split(MARK_AFTER, 1)
            after = MARK_AFTER + after_tail
    if MARK_KINIT in raw and not kinit:
        _, kinit = raw.split(MARK_KINIT, 1)
        kinit = MARK_KINIT + kinit
        if MARK_AFTER in kinit:
            kinit, after_tail = kinit.split(MARK_AFTER, 1)
            after = MARK_AFTER + after_tail

    return env, before, kinit, after, started


def parse_subsections(block: str) -> List[Tuple[str, List[str]]]:
    sections: List[Tuple[str, List[str]]] = []
    current_title = ""
    current_lines: List[str] = []

    for line in block.splitlines():
        if BANNER.match(line):
            continue
        hm = HEADER.match(line)
        if hm:
            if current_title or current_lines:
                sections.append((current_title, current_lines))
            current_title = hm.group(1).strip()
            current_lines = []
            continue
        if line.strip() == "" and not current_lines and not current_title:
            continue
        current_lines.append(line)

    if current_title or current_lines:
        sections.append((current_title, current_lines))
    return sections


def indent_block(lines: List[str], prefix: str = "      ") -> List[str]:
    out: List[str] = []
    for line in lines:
        if line.strip() == "":
            out.append("")
        else:
            out.append(prefix + line.rstrip())
    return out


def is_krb5_conf(lines: List[str]) -> bool:
    text = "\n".join(lines)
    return "[libdefaults]" in text and "[realms]" in text


def format_krb5_deploy(title: str, lines: List[str]) -> List[str]:
    out: List[str] = ["", f"  {title}", f"  {DOTS}"]
    path = "/etc/krb5.conf"
    m = re.search(r"deployed to (\S+)", title)
    if m:
        path = m.group(1)
    if is_krb5_conf(lines):
        out.append(f"      Path: {path}")
        out.append("")
        out.append("      Configuration:")
        out.extend(indent_block(lines, "          "))
    else:
        out.extend(indent_block(lines))
    return out


def format_krb5_path(lines: List[str]) -> List[str]:
    out = ["", "  krb5.conf on disk", f"  {DOTS}"]
    for line in lines:
        s = line.strip()
        if s.startswith("File:"):
            out.append(f"      {s}")
        elif s.startswith("-rw"):
            out.append(f"      Permissions: {s}")
        else:
            out.append(f"      {s}")
    return out


def format_dns_srv(title: str, lines: List[str]) -> List[str]:
    query = title.replace("DNS SRV Lookup:", "").strip()
    out = ["", f"  DNS SRV  {query}", f"  {DOTS}"]
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("WARNING:"):
            out.append(f"      [FAIL]  {s}")
        else:
            out.append(f"      [ OK ]  {s}")
    if len(out) == 3:
        out.append("      [FAIL]  no answers")
    return out


def format_kdc_connectivity(lines: List[str]) -> List[str]:
    out = ["", "  KDC connectivity (TCP/88)", f"  {DOTS}"]
    host = ""
    for line in lines:
        s = line.strip()
        if not s or s.startswith("Traceback") or s.startswith("File ") or s.startswith("socket."):
            continue
        if s.startswith("Testing connection to"):
            host = s.replace("Testing connection to ", "").replace("...", "")
            continue
        if s.startswith("SUCCESS:"):
            out.append(f"      [ OK ]  {s.replace('SUCCESS: ', '')}")
        elif s.startswith("FAILED:"):
            out.append(f"      [FAIL]  {s.replace('FAILED: ', '')}")
        else:
            out.append(f"      {s}")
    if host and len(out) == 3:
        out.append(f"      [FAIL]  cannot reach {host}")
    return out


def format_kinit_result(title: str, lines: List[str]) -> List[str]:
    out = ["", "  kinit result", f"  {DOTS}"]
    m = re.search(r"kinit (.+?) \(rc=(\d+)\)", title)
    if m:
        principal, rc = m.group(1), m.group(2)
        status = "[ OK ]" if rc == "0" else "[FAIL]"
        out.append(f"      Principal: {principal}")
        out.append(f"      Result:    {status}  rc={rc}")
    body: List[str] = []
    for line in lines:
        s = line.strip()
        if s.startswith("kinit stderr:"):
            out.append(f"      Error:     {s.replace('kinit stderr: ', '')}")
        elif s.startswith("kinit failed"):
            continue
        else:
            body.append(line)
    if body:
        out.append("")
        out.append("      Ticket cache after kinit:")
        out.extend(indent_block(body, "          "))
    return out


def format_klist_block(title: str, lines: List[str]) -> List[str]:
    if title.startswith("klist after kinit"):
        label = "Tickets after kinit"
    elif "BEFORE" in title:
        label = "Tickets before kinit"
    elif "AFTER" in title:
        label = "Tickets after win_ping"
    else:
        label = "Tickets"
    out = ["", f"  {label.strip()}", f"  {DOTS}"]
    if not lines or all("No credentials cache" in ln for ln in lines):
        out.append("      (empty — no tickets in cache)")
        for line in lines:
            if line.strip():
                out.append(f"      {line.strip()}")
    else:
        out.extend(indent_block(lines, "      "))
    return out


def format_cache_inspection(title: str, lines: List[str]) -> List[str]:
    phase = "before" if "BEFORE" in title else "after" if "AFTER" in title else ""
    heading = f"  Credential cache ({phase})" if phase else "  Credential cache"
    out = ["", heading, f"  {DOTS}"]
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("ls:"):
            out.append(f"      [ -- ]  cache file does not exist yet")
        elif s.startswith("-rw"):
            out.append(f"      [ OK ]  {s}")
        else:
            out.append(f"      {s}")
    return out


def format_generic(title: str, lines: List[str]) -> List[str]:
    nice = title
    replacements = {
        "Container System Time (UTC)": "System time (UTC)",
        "Kerberos Environment Variables": "Kerberos environment variables",
        "Kerberos Env Variables (BEFORE)": "Kerberos environment (before)",
        "Kerberos Env Variables (AFTER)": "Kerberos environment (after)",
        "klist after kinit": "Tickets after kinit",
    }
    for old, new in replacements.items():
        if title.startswith(old):
            nice = new
            break
    out = ["", f"  {nice}", f"  {DOTS}"]
    if not lines:
        out.append("      (no output)")
    else:
        out.extend(indent_block(lines))
    return out


def format_subsection(title: str, lines: List[str]) -> List[str]:
    if title.startswith("krb5.conf deployed"):
        return format_krb5_deploy(title, lines)
    if title.startswith("krb5.conf path") or title.startswith("krb5.conf Path"):
        return format_krb5_path(lines)
    if title.startswith("DNS SRV Lookup:"):
        return format_dns_srv(title, lines)
    if title.startswith("KDC Network Connectivity"):
        return format_kdc_connectivity(lines)
    if title.startswith("kinit ") and "(rc=" in title:
        return format_kinit_result(title, lines)
    if "klist Output" in title:
        return format_klist_block(title, lines)
    if "KRB5CCNAME Cache" in title or "Inspecting KRB5CCNAME" in title:
        return format_cache_inspection(title, lines)
    if title.startswith("klist after kinit"):
        return format_klist_block(title, lines)
    return format_generic(title, lines)


def format_section_body(block: str, drop_banners: bool = True) -> List[str]:
    if not block.strip():
        return ["      (no data captured)"]
    out: List[str] = []
    for title, lines in parse_subsections(block):
        if drop_banners and title.startswith("SNAPSHOT:"):
            ts_lines = [ln for ln in lines if ln.strip()]
            if ts_lines:
                out.extend(format_generic("Captured at (UTC)", ts_lines))
            continue
        if not title and lines and all(re.match(r"^\w{3} ", ln.strip()) for ln in lines if ln.strip()):
            # Bare timestamp line(s) before first --- header in snapshot sections
            out.extend(format_generic("Captured at (UTC)", lines))
            continue
        if not title and not lines:
            continue
        if not title:
            out.extend(indent_block(lines, "      "))
            continue
        out.extend(format_subsection(title, lines))
    return out


def build_summary(raw: str, srv_count: int) -> List[str]:
    srv_warn = sum(1 for ln in raw.splitlines() if "WARNING: no SRV answers" in ln)
    kdc_ok = sum(1 for ln in raw.splitlines() if ln.strip().startswith("SUCCESS: Connected"))
    kdc_fail = sum(1 for ln in raw.splitlines() if ln.strip().startswith("FAILED: Cannot reach"))
    kinit_m = re.search(r"--- kinit .+ \(rc=(\d+)\)", raw)
    kinit_rc = kinit_m.group(1) if kinit_m else None
    kinit_err = ""
    for ln in raw.splitlines():
        if ln.startswith("kinit stderr:"):
            kinit_err = ln.replace("kinit stderr: ", "")
            break

    out = ["", THIN, " SUMMARY", THIN]
    if srv_warn:
        out.append(f"  [FAIL]  DNS SRV             {srv_warn}/{srv_count or srv_warn} lookups returned no answers")
    elif srv_count:
        out.append(f"  [ OK ]  DNS SRV             {srv_count}/{srv_count} lookups answered")
    if kdc_fail:
        out.append(f"  [FAIL]  KDC port 88         {kdc_fail} target(s) unreachable")
    elif kdc_ok:
        out.append(f"  [ OK ]  KDC port 88         {kdc_ok} target(s) reachable")
    if kinit_rc == "0":
        out.append("  [ OK ]  kinit               TGT obtained")
    elif kinit_rc:
        msg = f"  [FAIL]  kinit               rc={kinit_rc}"
        if kinit_err:
            msg += f" — {kinit_err}"
        out.append(msg)
    else:
        out.append("  [ -- ]  kinit               not run")
    if MARK_AFTER in raw:
        out.append("  [ OK ]  AFTER snapshot      win_ping completed (section 4)")
    else:
        out.append("  [ -- ]  AFTER snapshot      play stopped before win_ping")
    return out


def format_report(raw: str, realm: str, domain: str, srv_count: int) -> str:
    env, before, kinit, after, started = split_major(raw)
    lines: List[str] = [
        "",
        BAR,
        " KERBEROS WINRM — DIAGNOSTIC REPORT",
        BAR,
        f"  Generated : {started or 'unknown'}",
        f"  Realm     : {realm or 'unknown'}",
        f"  Domain    : {domain or 'unknown'}",
    ]
    lines.extend(build_summary(raw, srv_count))

    sections = [
        ("1. ENVIRONMENT & KRB5.CONF", env),
        ("2. TICKET CACHE — BEFORE kinit", before if MARK_BEFORE in raw else ""),
        ("3. KINIT", kinit if MARK_KINIT in raw else ""),
        ("4. TICKET CACHE — AFTER win_ping", after if MARK_AFTER in raw else ""),
    ]
    for heading, body in sections:
        if not body.strip() and not heading.startswith("1."):
            continue
        lines.extend(["", BAR, f" {heading}", BAR])
        lines.extend(format_section_body(body))

    lines.extend(["", BAR, " END OF REPORT", BAR, ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--realm", default="unknown")
    parser.add_argument("--domain", default="unknown")
    parser.add_argument("--srv-count", type=int, default=0)
    args = parser.parse_args()
    raw = sys.stdin.read()
    sys.stdout.write(format_report(raw, args.realm, args.domain, args.srv_count))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
