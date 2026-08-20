"""Design audit driver — logs in under each role and crawls routes.

Outputs to /root/workspace/ai-tutor/docs/design-audit-2026-08-20/.
Read-only — does NOT touch the backend or production data.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from playwright.sync_api import (
    Page,
    Playwright,
    Request,
    Response,
    TimeoutError as PWTimeoutError,
    sync_playwright,
)

BASE = "https://school.431a.ru"
OUT = Path("/root/workspace/ai-tutor/docs/design-audit-2026-08-20")
DOM_DIR = OUT / "dom"
SHOTS_DIR = OUT / "screenshots"
DOM_DIR.mkdir(parents=True, exist_ok=True)
SHOTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------- per-role route maps --------------------------------------------
LOGIN_PATH = "/login"

ROLE_ROUTES: dict[str, list[str]] = {
    "anon": [
        "/login",
        "/register",
        "/forgot-password",
        "/welcome",
    ],
    "student": [  # kirill@example.com
        "/subjects",
        "/diagnostic",
        "/link-parent",
    ],
    "parent": [  # parent-e2e@example.com
        "/parents",
    ],
    "teacher": [  # teacher-ui@example.com
        "/teacher",
        "/teacher/generate",
    ],
    "admin": [  # admin@example.com
        "/admin",
    ],
}

CRED = {
    "student": ("kirill@example.com", "Kirill2026!"),
    "parent": ("parent-e2e@example.com", "Kirill2026!"),
    "teacher": ("teacher-ui@example.com", "Kirill2026!"),
    "admin": ("admin@example.com", "Kirill2026!"),
}

# ---------- helpers ---------------------------------------------------------

def slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._/-]+", "-", s).strip("-")
    return s.replace("/", "_")[:140]


def dump_page(page: Page, role: str, label: str) -> Path:
    """Snapshot DOM state to JSON."""
    data = page.evaluate(
        """() => {
          const sel = 'button, a, [role=button], input, textarea, select, h1, h2, h3, h4, h5, h6, [class*=card], [role=alert]';
          const nodes = Array.from(document.querySelectorAll(sel))
            .map((n, i) => {
              const cs = getComputedStyle(n);
              return {
                i, tag: n.tagName,
                role: n.getAttribute('role'),
                aria: n.getAttribute('aria-label'),
                cls: (n.className || '').toString().slice(0, 140),
                txt: (n.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 180),
                disabled: n.disabled || false,
                bg: cs.backgroundColor,
                color: cs.color,
                fs: cs.fontSize,
                visible: cs.display !== 'none' && cs.visibility !== 'hidden',
              };
            });
          const cs = getComputedStyle(document.body);
          return {
            url: location.href,
            title: document.title,
            vw: innerWidth, vh: innerHeight,
            docHeight: document.documentElement.scrollHeight,
            scrollY: window.scrollY,
            bodyBg: cs.backgroundColor,
            bodyColor: cs.color,
            bodyFont: cs.fontFamily,
            htmlBg: getComputedStyle(document.documentElement).backgroundColor,
            cards: document.querySelectorAll('[class*="card"], article, section').length,
            buttons: document.querySelectorAll('button, a[href], [role=button]').length,
            inputs: document.querySelectorAll('input, textarea, select').length,
            headings: document.querySelectorAll('h1,h2,h3,h4,h5,h6').length,
            images: document.querySelectorAll('img').length,
            errors: Array.from(document.querySelectorAll('[role=alert], [class*=error], [class*=Error]'))
              .map((n,i)=>({i, cls: (n.className||'').toString().slice(0,160), txt: n.textContent.trim().slice(0, 240)})),
            nodes,
          };
        }"""
    )
    name = f"{role}__{slug(label)}.json"
    p = DOM_DIR / name
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return p


def screenshot(page: Page, role: str, label: str, full: bool = True) -> Path:
    name = f"{role}__{slug(label)}.png"
    p = SHOTS_DIR / name
    try:
        page.screenshot(path=str(p), full_page=full, animations="disabled")
    except Exception as e:  # noqa: BLE001
        print(f"  ! screenshot failed: {e}")
    return p


def login(page: Page, email: str, password: str) -> None:
    page.goto(f"{BASE}{LOGIN_PATH}", wait_until="domcontentloaded")
    # If already logged-in, /login redirects. Force re-auth:
    page.wait_for_load_state("networkidle", timeout=15000)
    page.fill('input[type="email"], input[name="email"], input[name="username"]', email)
    page.fill('input[type="password"], input[name="password"]', password)
    # Submit
    btn = page.query_selector('button[type="submit"], form button')
    if not btn:
        raise RuntimeError("submit button not found on /login")
    btn.click()
    page.wait_for_load_state("networkidle", timeout=20000)


def logout(page: Page) -> None:
    # Hard reset: clear cookies + storage and go /login
    try:
        page.evaluate(
            "() => { try { localStorage.clear(); sessionStorage.clear(); } catch (e) {} }"
        )
        page.context.clear_cookies()
    except Exception:
        pass
    page.goto(f"{BASE}{LOGIN_PATH}", wait_until="domcontentloaded")


def crawl(pw: Playwright) -> None:
    browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        device_scale_factor=1,
        ignore_https_errors=True,
        locale="ru-RU",
    )

    def shoot_summary(role: str, label: str, note: str = "") -> None:
        pass

    # ANON first
    anon_page = context.new_page()
    print("# ANON")
    for route in ROLE_ROUTES["anon"]:
        try:
            anon_page.goto(f"{BASE}{route}", wait_until="domcontentloaded", timeout=20000)
            anon_page.wait_for_load_state("networkidle", timeout=10000)
            d = dump_page(anon_page, "anon", route)
            s = screenshot(anon_page, "anon", route)
            print(f"  /{route.lstrip('/')}  dom={d.name}  shot={s.name}")
        except Exception as e:  # noqa: BLE001
            print(f"  /{route.lstrip('/')}  ERROR: {e}")
    anon_page.close()

    # Roles — separate context per role for clean cookies
    for role, email_pw in CRED.items():
        email, pw = email_pw
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
            ignore_https_errors=True,
            locale="ru-RU",
        )
        page = ctx.new_page()
        label = f"{role}-login"
        try:
            login(page, email, pw)
            d = dump_page(page, role, "00-after-login")
            s = screenshot(page, role, "00-after-login")
            print(f"# {role.upper()}  login OK  -> land on {page.url}  dom={d.name}")
        except Exception as e:  # noqa: BLE001
            print(f"# {role.upper()}  LOGIN FAIL: {e}")
            d = dump_page(page, role, "00-login-fail")
            ctx.close()
            continue

        # Crawl roles routes
        for route in ROLE_ROUTES[role]:
            try:
                page.goto(f"{BASE}{route}", wait_until="domcontentloaded", timeout=20000)
                page.wait_for_load_state("networkidle", timeout=10000)
                d = dump_page(page, role, route)
                s = screenshot(page, role, route)
                print(f"  {role} /{route.lstrip('/')}  ok  ({page.url})")
            except Exception as e:  # noqa: BLE001
                print(f"  {role} /{route.lstrip('/')}  ERROR: {e}")

        # Mobile preview on the role's primary page
        mobile = ctx.new_page() if False else page  # reuse, just resize
        try:
            page.set_viewport_size({"width": 390, "height": 844})
            primary = ROLE_ROUTES[role][0]
            page.goto(f"{BASE}{primary}", wait_until="domcontentloaded", timeout=20000)
            page.wait_for_load_state("networkidle", timeout=10000)
            dump_page(page, role, f"mobile-{primary}")
            screenshot(page, role, f"mobile-{primary}")
        except Exception as e:  # noqa: BLE001
            print(f"  {role} mobile preview ERROR: {e}")
        finally:
            page.set_viewport_size({"width": 1440, "height": 900})
            ctx.close()

    context.close()
    browser.close()


if __name__ == "__main__":
    with sync_playwright() as pw:
        crawl(pw)
    print("\nDONE.")
