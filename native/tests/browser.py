"""Full local native Chromium QA at the actual project-prefixed /js/ path."""
from __future__ import annotations

import json
import re
import statistics
import sys
import threading
import time
import traceback
import urllib.parse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.progress import decode_snapshot, encode_snapshot, hydrate_snapshot, create_option_order
from app.content import ROUNDS
from app.engine import METRIC_LABELS, apply_results, summarize_results  # noqa: E402

NATIVE = ROOT / "native"
RESULTS = NATIVE / "test-results"
PREFIX = "/filing-day-decisions/js/"
RESULTS.mkdir(exist_ok=True)
ORACLE = json.loads((NATIVE / "tests/python-oracles.json").read_text())
LEGACY = json.loads((NATIVE / "tests/legacy-links.json").read_text())
checks, requests, external, errors, console_errors = [], [], [], [], []


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        requests.append(path)
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        elif path.startswith(PREFIX):
            self.path = path[len(PREFIX) - 1:]
            super().do_GET()
        else:
            self.send_error(404)


def passed(name):
    checks.append({"name": name, "status": "passed"})
    print("PASSED:", name, flush=True)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(NATIVE / "dist")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = "http://127.0.0.1:" + str(server.server_port)
    url = origin + PREFIX
    result = {"url": url, "conditions": "Actual native Chromium at the project-prefixed /js/ path; external traffic blocked."}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path="/usr/bin/chromium", headless=True,
            proxy={"server": "http://127.0.0.1:9", "bypass": "127.0.0.1,localhost"})
        def attach(context):
            def route(route):
                if route.request.url.startswith(origin):
                    route.continue_()
                else:
                    external.append(route.request.url)
                    route.abort()
            context.route("**/*", route)
            def events(page):
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            context.on("page", events)
        context = browser.new_context(viewport={"width": 1280, "height": 960})
        attach(context)
        page = context.new_page()
        def loaded(view=None):
            page.wait_for_function("document.documentElement.dataset.ready==='true'&&document.documentElement.dataset.saving==='false'")
            if view is not None:
                page.wait_for_function("v=>document.documentElement.dataset.view===String(v)", arg=view)
            expect(page).to_have_title("Filing Day Decisions")
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            assert not re.search(r"\b(?:pilot|preview|test(?:ing)?\s+(?:app|version|site))\b", page.locator("body").inner_text(), re.I)
        def go(address=url, view=None):
            page.goto(address, wait_until="networkidle")
            loaded(view)
        def state():
            return decode_snapshot(urllib.parse.parse_qs(urllib.parse.urlsplit(page.url).query)["progress"][0])
        def button(label):
            page.get_by_role("button", name=label, exact=True).click()
            loaded()
        def shot(name):
            page.screenshot(path=str(RESULTS / (name + ".png")), full_page=True)
        def choose(question, wrong=False):
            answer = next(index for index, option in enumerate(question["options"]) if bool(option["correct"]) != wrong)
            page.locator('input[name="' + question["id"] + '"][value="' + str(answer) + '"]').check()
            loaded()
        def gauges(view):
            saved = state()
            hydrated = hydrate_snapshot(saved)
            if view == 7:
                expected = hydrated["metrics"]
            elif saved["round_submitted"] or view < saved["round_index"] + 1:
                slug = ROUNDS[view - 1]["slug"]
                expected = apply_results(hydrated["round_baselines"][slug],
                    [item for item in hydrated["responses"] if item["round_slug"] == slug])
            else:
                expected = hydrated["metrics"]
            for key, label in METRIC_LABELS.items():
                expect(page.get_by_role("progressbar", name=label, exact=True)).to_have_attribute("aria-valuenow", str(expected[key]))
        try:
            go(view=0)
            expect(page.get_by_role("button", name="Back", exact=True)).to_be_disabled()
            expect(page.get_by_role("button", name="Forward", exact=True)).to_be_disabled()
            shot("welcome-desktop")
            button("Begin the filing review")
            loaded(1)
            button("Submit this round")
            expect(page.get_by_role("alert")).to_contain_text("Make a decision for every item")
            first = ROUNDS[0]["questions"][0]
            choose(first, True)
            draft_url = page.url
            before = state()
            button("Back")
            loaded(0)
            expect(page.locator("#lesson input,#lesson button")).to_have_count(0)
            assert state() == before
            button("Forward")
            loaded(1)
            expect(page.get_by_role("button", name="Forward", exact=True)).to_be_disabled()
            page.reload()
            loaded(1)
            assert page.url == draft_url
            assert state() == before
            expected_order = create_option_order(before["order_seed"])[first["id"]]
            assert page.locator('input[name="' + first["id"] + '"]').evaluate_all("items=>items.map(item=>Number(item.value))") == expected_order
            passed("Initial validation, wrong draft, readonly welcome, Forward stopping, refresh and exact Python option order")

            for index, round_data in enumerate(ROUNDS):
                loaded(index + 1)
                for question in round_data["questions"]:
                    choose(question, index == 0 and question["id"] == first["id"])
                gauges(index + 1)
                button("Submit this round")
                expect(page.get_by_role("button", name="Submit this round", exact=True)).to_have_count(0)
                assert state()["round_submitted"] is True
                gauges(index + 1)
                round_before = state()
                expect(page.get_by_role("button", name="Forward", exact=True)).to_be_disabled()
                if index % 2 == 0:
                    button("Reveal answer")
                    expect(page.locator(".revealed-answer")).to_contain_text(round_data["reflection_answer"])
                    assert round_data["slug"] in state()["revealed"]
                    page.reload()
                    loaded(index + 1)
                    expect(page.locator(".revealed-answer")).to_contain_text(round_data["reflection_answer"])
                    assert state()["results"] == round_before["results"]
                if index == 0:
                    shot("feedback-desktop")
                button("Open the final review" if index == 5 else "Continue to the next round")
            loaded(7)
            expect(page.locator(".debrief-hero")).to_contain_text("18 of 19 strongest decisions · 95%")
            gauges(7)
            assert summarize_results(hydrate_snapshot(state())["responses"])["correct"] == 18
            completed_url = page.url
            result["completion_bookmark"] = completed_url
            shot("completed-desktop")
            for summary in page.locator("#lesson details summary").all():
                summary.click()
            expect(page.locator("#lesson")).to_contain_text("Your decision:")
            expect(page.locator("#lesson")).to_contain_text("Stronger choice:")
            passed("All six rounds and nineteen decisions, wrong-answer feedback, selective reveals, exact gauges and 18/19 completion")

            before = state()
            for view in range(6, -1, -1):
                button("Back")
                loaded(view)
                assert state() == before
                expect(page.locator("#lesson input,#lesson select,#lesson textarea,#lesson button")).to_have_count(0)
                expect(page.get_by_role("button", name="Reveal answer", exact=True)).to_have_count(0)
                if view:
                    gauges(view)
                    expected_reveal = ROUNDS[view - 1]["slug"] in before["revealed"]
                    expect(page.locator(".revealed-answer")).to_have_count(int(expected_reveal))
                if view == 2:
                    shot("readonly-unrevealed-desktop")
            forward = page.get_by_role("button", name="Forward", exact=True)
            forward.focus()
            page.keyboard.press("Tab")
            page.keyboard.press("Shift+Tab")
            expect(forward).to_be_focused()
            assert forward.evaluate("e=>e.matches(':focus-visible')&&getComputedStyle(e).outlineWidth==='2px'")
            page.keyboard.press("Enter")
            loaded(1)
            for view in range(2, 8):
                button("Forward")
                loaded(view)
                assert state() == before
            expect(forward).to_be_disabled()
            go(completed_url.replace("view=7", "view=2"), 2)
            page.reload()
            loaded(2)
            expect(page.locator(".revealed-answer")).to_have_count(0)
            assert state() == before
            go(completed_url.replace("view=7", "view=999"), 7)
            assert state() == before
            passed("Every page readonly, no new reveals, historical gauges, repeated Back/Forward, keyboard and saved review positions")

            for width in (900, 390):
                page.set_viewport_size({"width": width, "height": 844})
                go(completed_url, 7)
                gauges(7)
                shot("completed-" + str(width))
                for label in ("Back", "Forward"):
                    box = page.get_by_role("button", name=label, exact=True).bounding_box()
                    assert box["width"] >= 44 and box["height"] >= 44
                    assert box["x"] + box["width"] <= width
                go(completed_url.replace("view=7", "view=2"), 2)
                shot("readonly-unrevealed-" + str(width))
            page.set_viewport_size({"width": 1280, "height": 960})
            go(completed_url, 7)
            button("Start over")
            loaded(1)
            assert state()["page"] == "round" and state()["results"] == {} and state()["revealed"] == []
            gauges(1)
            independent = browser.new_context()
            attach(independent)
            other = independent.new_page()
            other.goto(url, wait_until="networkidle")
            other.wait_for_function("document.documentElement.dataset.ready==='true'")
            assert other.locator("html").get_attribute("data-reached") == "0"
            go(completed_url, 7)
            assert other.locator("html").get_attribute("data-reached") == "0"
            independent.close()
            passed("1280/900/390px layouts, 44px arrows, original Start over to round one, old bookmarks and independent sessions")

            for fixture in [*LEGACY, *ORACLE["snapshots"]]:
                saved = fixture["snapshot"]
                view = 0 if saved["page"] == "welcome" else 7 if saved["page"] == "debrief" else saved["round_index"] + 1
                address = url + "?progress=" + fixture["token"] + "&view=" + str(view) + "&tag=a%20b&tag=c%2Fd#saved"
                go(address, view)
                assert state() == saved
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(page.url).query)
                assert query["tag"] == ["a b", "c/d"]
                assert urllib.parse.urlsplit(page.url).fragment == "saved"
                if view and view != 7:
                    gauges(view)
            go(url + "?progress=bad!&view=999", 0)
            expect(page.locator("#lesson")).to_contain_text("This saved link could not be restored")
            passed("All original submitted/unsubmitted/revealed legacy links, native links, extra query values and malformed tokens")

            for wrong, expected in ((False, 19), (True, 0)):
                go(view=0)
                button("Begin the filing review")
                for index, round_data in enumerate(ROUNDS):
                    for question in round_data["questions"]:
                        choose(question, wrong)
                    button("Submit this round")
                    gauges(index + 1)
                    button("Open the final review" if index == 5 else "Continue to the next round")
                loaded(7)
                expect(page.locator(".debrief-hero")).to_contain_text(str(expected) + " of 19")
                assert summarize_results(hydrate_snapshot(state())["responses"])["correct"] == expected
            passed("Two further full lesson routes: 19/19 and 0/19, including sequential gauge saturation")

            snapshot = json.loads(json.dumps(LEGACY[7]["snapshot"]))
            count = 0
            for round_data in ROUNDS:
                for question in round_data["questions"]:
                    if count < 5:
                        answer = next(index for index, option in enumerate(question["options"]) if not option["correct"])
                        snapshot["choices"][question["id"]] = snapshot["results"][question["id"]] = answer
                    count += 1
            go(url + "?progress=" + encode_snapshot(snapshot), 7)
            expect(page.locator(".debrief-hero")).to_contain_text("Promising draft")
            passed("All three original debrief outcome variants and finalized branding")

            times = []
            for _ in range(5):
                cold = browser.new_context()
                attach(cold)
                fresh = cold.new_page()
                session = cold.new_cdp_session(fresh)
                session.send("Network.enable")
                session.send("Network.setCacheDisabled", {"cacheDisabled": True})
                fresh.goto(url, wait_until="networkidle")
                fresh.wait_for_function("document.documentElement.dataset.ready==='true'")
                times.append(fresh.evaluate("performance.getEntriesByName('filing-ready')[0].startTime"))
                cold.close()
            result["cold_initialization_ms"] = {"samples": times, "median": statistics.median(times),
                "conditions": "Five cache-disabled fresh Chromium contexts on local loopback; no hosted-speed or capacity claim."}
            assert external == errors == console_errors == []
            assert not any(path.endswith((".py", ".wasm", ".whl")) or "/vendor/" in path or "/_stcore/" in path for path in requests)
            passed("Five local cold initializations and zero external, runtime/package, server, page-error or console-error traffic")
        except Exception:
            checks.append({"name": "Browser walkthrough", "status": "failed", "error": traceback.format_exc()})
            page.screenshot(path=str(RESULTS / "failure.png"), full_page=True)
            result["body_on_failure"] = page.locator("body").inner_text()
        browser.close()
    server.shutdown()
    result.update(checks=checks,requests=sorted(set(requests)),external_requests=external,page_errors=errors,console_errors=console_errors,
        downloads="Not applicable: the original Filing Day Decisions lesson defines no download or dataframe.")
    (RESULTS / "browser-results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k:v for k,v in result.items() if k not in ("body_on_failure","completion_bookmark")},indent=2),flush=True)
    return int(any(check["status"] == "failed" for check in checks))


if __name__ == "__main__":
    raise SystemExit(main())
