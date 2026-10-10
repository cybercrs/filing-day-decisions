"""Actual Chromium/Wasm lesson walkthrough. External requests are blocked."""
from __future__ import annotations
import argparse
import json
import threading
import time
import traceback
import urllib.parse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


class Walkthrough:
    def __init__(self, page, results, result_dir):
        self.page, self.results, self.directory = page, results, result_dir
        self.runs = 0
        def completed(message):
            if message.text.startswith("BROWSER_VERSIONS="):
                self.runs += 1
        page.on("console", completed)

    def query(self):
        return {k:v[0] for k,v in urllib.parse.parse_qs(urllib.parse.urlsplit(self.page.url).query).items()}

    def idle(self):
        self.page.wait_for_timeout(100)
        self.page.locator('[data-test-script-state="notRunning"]').wait_for(timeout=30000)
        assert self.page.locator('[data-testid="stException"]').count() == 0

    def wait_run(self, previous):
        deadline = time.monotonic() + 45
        while self.runs <= previous and time.monotonic() < deadline:
            self.page.wait_for_timeout(50)
        assert self.runs > previous, "Python rerun did not finish"
        self.idle()

    def loaded(self):
        self.page.bring_to_front()
        try:
            self.page.get_by_role('button', name='Back', exact=True).wait_for(timeout=120000)
        except Exception:
            retry = self.page.get_by_role('button', name='Retry loading', exact=True)
            if retry.is_visible():
                address = self.page.url
                self.results.setdefault('startup_retries', []).append({'url':address, 'notice':self.page.locator('#startup-message').inner_text()})
                retry.click()
                self.page.wait_for_load_state('domcontentloaded')
                assert self.page.url == address, 'Retry changed the saved address'
                self.page.get_by_role('button', name='Back', exact=True).wait_for(timeout=120000)
            else:
                self.results.setdefault('startup_failures', []).append({'url':self.page.url, 'body':self.page.locator('body').inner_text()})
                raise
        self.idle()

    def view(self, index):
        self.page.wait_for_function('(v)=>new URLSearchParams(location.search).get("view")===String(v)', arg=index, timeout=30000)
        self.idle()
        assert self.query()['view'] == str(index)

    def click(self, label, sidebar=False):
        self.page.bring_to_front()
        loc = self.page.locator('[data-testid="stSidebar"]' if sidebar else '[data-testid="stMain"]')
        previous = self.runs
        loc.get_by_role('button', name=label, exact=True).click()
        self.wait_run(previous)

    def changed(self, url):
        self.page.wait_for_function('(url)=>location.href!==url', arg=url, timeout=30000)
        self.idle()

    def select(self, key, value):
        combobox = self.page.locator(f'[class~="st-key-{key}"]').get_by_role('combobox')
        if self.page.locator(f'[class~="st-key-{key}"] [data-baseweb=select]').inner_text().strip() == value:
            return
        previous = self.runs
        previous_url = self.page.url
        combobox.click()
        self.page.get_by_role('option', name=value, exact=True).click()
        self.wait_run(previous)
        self.changed(previous_url)

    def radio(self, key, value):
        loc = self.page.locator(f'[class~="st-key-{key}"]')
        radio = loc.get_by_role('radio', name=value.replace(r'\$', '$'), exact=True)
        if radio.is_checked():
            return
        previous = self.runs
        previous_url = self.page.url
        radio.locator('xpath=ancestor::label').click()
        self.wait_run(previous)
        self.changed(previous_url)

    def many(self, key, values):
        loc = self.page.locator(f'[class~="st-key-{key}"]')
        for value in values:
            previous = self.runs
            previous_url = self.page.url
            loc.get_by_role('combobox').click()
            self.page.get_by_role('option', name=value, exact=True).click()
            self.wait_run(previous)
            self.changed(previous_url)
        self.page.keyboard.press('Escape')

    def number(self, key, value):
        loc = self.page.locator(f'[class~="st-key-{key}"]').get_by_role('spinbutton')
        previous = self.runs
        previous_url = self.page.url
        loc.fill(str(value))
        loc.press('Tab')
        self.wait_run(previous)
        self.changed(previous_url)

    def disabled(self, label):
        expect(self.page.get_by_role('button', name=label, exact=True)).to_be_disabled()

    def text(self, value):
        expect(self.page.locator('body')).to_contain_text(value, timeout=30000)

    def shot(self, name):
        self.page.screenshot(path=str(self.directory / (name + '.png')), full_page=True)

    def passed(self, label):
        self.results['checks'].append({'name':label,'status':'passed'})
        print('PASSED:', label, flush=True)

    def review(self, current, repeats=2):
        snapshot = {k:v for k,v in self.query().items() if k != 'view'}
        for _ in range(repeats):
            self.click('Back'); self.view(current-1)
            self.text('Review only. Return to your current page to continue the activity.')
            expect(self.page.locator('[data-testid="stMain"] [data-testid="stButton"]').get_by_role('button')).to_have_count(2)
            assert self.page.get_by_role('radio').count() == 0
            assert self.page.get_by_role('combobox').count() == 0
            assert self.page.get_by_role('spinbutton').count() == 0
            assert self.page.locator('[data-testid=stTextArea] textarea').count() == 0
            assert {k:v for k,v in self.query().items() if k != 'view'} == snapshot, {'before':snapshot,'after':self.query()}
            self.click('Forward'); self.view(current)
            assert {k:v for k,v in self.query().items() if k != 'view'} == snapshot, {'before':snapshot,'after':self.query()}
            self.disabled('Forward')
        self.passed('Read-only repeat review leaves progress, answers and scores unchanged')

    def refresh_review(self, current):
        snapshot = {k:v for k,v in self.query().items() if k != 'view'}
        self.click('Back'); self.view(current-1)
        bookmark = self.page.url
        self.page.reload(wait_until='domcontentloaded'); self.loaded(); self.view(current-1)
        assert {k:v for k,v in self.query().items() if k != 'view'} == snapshot, {'before':snapshot,'after':self.query()}
        clone=self.page.context.new_page()
        test=Walkthrough(clone,self.results,self.directory)
        clone.goto(bookmark,wait_until='domcontentloaded'); test.loaded(); test.view(current-1)
        assert {k:v for k,v in test.query().items() if k != 'view'} == snapshot
        test.click('Forward'); test.view(current)
        clone.goto(urllib.parse.urlunsplit(urllib.parse.urlsplit(clone.url)._replace(query=urllib.parse.urlencode({**test.query(),'view':'999'}))), wait_until='domcontentloaded')
        test.loaded(); test.view(current); test.disabled('Forward')
        assert {k:v for k,v in test.query().items() if k != 'view'} == snapshot
        clone.close()
        self.click('Forward'); self.view(current)
        self.passed('Review refresh, bookmark and future-view rejection preserve canonical work')

    def layout(self, kind):
        nav=self.page.locator('.st-key-browser_navigation')
        boxes=[nav.get_by_role('button',name=name,exact=True).bounding_box() for name in ('Back','Forward')]
        assert all(box and 44<=box['width']<=45 and 44<=box['height']<=45 for box in boxes), boxes
        assert abs(boxes[0]['y']-boxes[1]['y'])<=1, boxes
        assert 0<boxes[1]['x']-boxes[0]['x']<=60, boxes
        main=self.page.locator('.block-container').bounding_box()
        assert boxes[0]['x']>main['x']+main['width']/2, (main, boxes)
        assert self.page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        self.results.setdefault('navigation_layout',{})[kind]=boxes
        self.shot(kind)

    def finish(self, current, start, reset, sidebar):
        self.shot('completed')
        final_query={k:v for k,v in self.query().items() if k!='view'}
        bookmark=self.page.url
        self.results['completion_bookmark'] = bookmark
        for index in range(current-1,-1,-1):
            self.click('Back'); self.view(index)
            expect(self.page.locator('[data-testid="stMain"] [data-testid="stButton"]').get_by_role('button')).to_have_count(2)
            assert {k:v for k,v in self.query().items() if k!='view'}==final_query
        self.shot('readonly')
        forward=self.page.get_by_role('button',name='Forward',exact=True)
        forward.focus()
        self.page.keyboard.press('Tab')
        self.page.keyboard.press('Shift+Tab')
        expect(forward).to_be_focused()
        assert forward.evaluate("e=>e.matches(':focus-visible')")
        assert forward.evaluate('e=>getComputedStyle(e).outlineWidth')=='2px'
        self.page.keyboard.press('Enter'); self.view(1)
        for index in range(2,current+1):
            self.click('Forward'); self.view(index)
            assert {k:v for k,v in self.query().items() if k!='view'}==final_query
        self.disabled('Forward')
        self.page.reload(wait_until='domcontentloaded');self.loaded();self.view(current)
        assert {k:v for k,v in self.query().items() if k!='view'}==final_query
        self.passed('Complete lesson, every reached review page, keyboard focus and refresh')
        clean=self.page.context.new_page();t=Walkthrough(clean,self.results,self.directory)
        clean.goto(self.results['url'],wait_until='domcontentloaded');t.loaded();t.view(0)
        assert t.query()['progress']!=final_query['progress']
        clean.close()
        other_context = self.page.context.browser.new_context()
        other = other_context.new_page(); independent = Walkthrough(other, self.results, self.directory)
        other.goto(self.results['url'], wait_until='domcontentloaded'); independent.loaded(); independent.view(0)
        assert independent.query()['progress'] != final_query['progress']
        other.goto(bookmark, wait_until='domcontentloaded'); independent.loaded(); independent.view(current)
        assert {k:v for k,v in independent.query().items() if k!='view'} == final_query
        other_context.close()
        self.click(reset,sidebar);self.view(start)
        assert self.query()['progress']!=final_query['progress']
        self.page.reload(wait_until='domcontentloaded');self.loaded();self.view(start)
        self.passed('Independent tab and reset replace progress without changing old bookmarks')
        self.page.set_viewport_size({'width':390,'height':844})
        if start==0:
            self.click(START);self.view(1)
        self.layout('narrow')
        self.passed('Narrow viewport: accessible boxed 44px arrows aligned at upper right')
        self.page.set_viewport_size({'width':1280,'height':900})
        self.page.goto(self.results['url']+'/classroom/',wait_until='domcontentloaded');self.loaded();self.view(0)
        self.click(START);self.view(1)
        self.page.reload(wait_until='domcontentloaded');self.loaded();self.view(1)
        assert urllib.parse.urlsplit(self.page.url).path=='/classroom/'
        self.passed('Subdirectory paths, runtime assets and refresh')
        self.page.goto(self.results['url'] + '/?progress=invalid-token&view=999', wait_until='domcontentloaded')
        self.loaded(); self.view(0); self.disabled('Forward')
        self.passed('Malformed progress and future view reset to a fresh lesson')
        recovery = self.page.context.new_page()
        saved_address = self.results['url']+'/?'+urllib.parse.urlsplit(bookmark).query+'&retry-test=1'
        recovery.goto(saved_address, wait_until='domcontentloaded')
        retry_button = recovery.get_by_role('button', name='Retry loading', exact=True)
        expect(retry_button).to_be_visible(timeout=30000)
        expect(recovery.locator('#startup-message')).to_contain_text('Work saved in this address will be kept')
        assert recovery.url == saved_address
        assert retry_button.bounding_box()['height'] >= 44
        recovery.set_viewport_size({'width':390,'height':844})
        assert recovery.evaluate('document.documentElement.scrollWidth<=innerWidth')
        recovery.screenshot(path=str(self.directory/'loading-recovery.png'))
        retry_button.focus(); retry_button.press('Enter')
        recovery.wait_for_load_state('domcontentloaded')
        assert recovery.url == saved_address
        recovered = Walkthrough(recovery,self.results,self.directory)
        recovered.loaded(); recovered.view(current)
        assert recovered.query()['progress'] == final_query['progress']
        expect(recovery.locator('#startup-notice')).to_be_hidden()
        recovery.close()
        self.passed('Visible loading error and keyboard Retry retain the exact completed bookmark')


from app.content import ROUNDS
START='Begin the filing review'


def lesson(h):
    h.click(START);h.view(1)
    h.click('Submit this round');h.text('Make a decision for every item')
    q=ROUNDS[0]['questions'][0]
    h.radio('answer-'+q['id'],q['options'][0]['text'])
    h.review(1);h.refresh_review(1)
    expect(h.page.locator('[class~="st-key-answer-' + q['id'] + '"]').get_by_role('radio', name=q['options'][0]['text'], exact=True)).to_be_checked()
    for index,r in enumerate(ROUNDS):
        for j,q in enumerate(r['questions']):
            correct=next(o for o in q['options'] if o['correct'])
            choice=next(o for o in q['options'] if not o['correct']) if index==0 and j==0 else correct
            h.radio('answer-'+q['id'],choice['text'])
        h.click('Submit this round');h.text('Round complete:');h.disabled('Forward')
        # Submission locks the round; review must not create a new reveal.
        h.review(index+1,1)
        if index==1:
            assert h.page.locator('.revealed-answer').count()==0
            h.click('Back');h.view(index)
            assert h.page.get_by_role('button',name='Reveal answer',exact=True).count()==0
            h.click('Forward');h.view(index+1)
            assert h.page.locator('.revealed-answer').count()==0
            h.click('Reveal answer');h.page.locator('.revealed-answer').wait_for();h.idle()
        h.click('Open the final review' if index==len(ROUNDS)-1 else 'Continue to the next round')
        h.view(index+2)
    h.text('Filing review complete')
    h.passed('Six rounds, 19 decisions, wrong-answer scoring and reveal discipline')
    h.finish(len(ROUNDS)+1,1,'Start over',False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist',type=Path,default=ROOT/'browser/dist')
    parser.add_argument('--results',type=Path,default=ROOT/'browser/test-results')
    args=parser.parse_args();args.results.mkdir(parents=True,exist_ok=True)
    requests=[]
    fault_state={'used':False}
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            requests.append(self.path)
            if self.path.startswith('/classroom/'):
                self.path=self.path[len('/classroom'):]
            if self.path=='/favicon.ico':
                self.send_response(204);self.end_headers()
            elif self.path=='/app.json' and 'retry-test=1' in self.headers.get('Referer','') and not fault_state['used']:
                # An invalid 200 JSON response exercises the bootstrap catch
                # without creating an unrelated network/console error.
                fault_state['used']=True
                self.send_response(200);self.send_header('Content-Type','application/json')
                self.send_header('Content-Length','1');self.end_headers();self.wfile.write(b'{')
            elif self.path=='/app.json':
                config=json.loads((args.dist/'app.json').read_text())
                config['files']['browser/app.py']+='\nimport sys,json,pyodide\nprint("BROWSER_VERSIONS="+json.dumps({"python":sys.version.split()[0],"streamlit":st.__version__,"pyodide":pyodide.__version__}))\n'
                payload=json.dumps(config).encode();self.send_response(200)
                self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
            else:super().do_GET()
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(args.dist)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    results={'url':f'http://127.0.0.1:{server.server_port}','transport':'actual local static stlite/Wasm; external requests blocked','checks':[],'page_errors':[],'console_errors':[],'external_requests':[]}
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--disable-background-timer-throttling','--disable-backgrounding-occluded-windows','--disable-renderer-backgrounding'],proxy={'server':'http://127.0.0.1:9','bypass':'127.0.0.1,localhost'})
        context=browser.new_context(viewport={'width':1280,'height':900})
        context.on('request',lambda r:results['external_requests'].append(r.url) if r.url.startswith('http') and not r.url.startswith(results['url']) else None)
        page=context.new_page()
        page.on('pageerror',lambda e:results['page_errors'].append(str(e)))
        def console(message):
            if message.text.startswith('BROWSER_VERSIONS='):results['runtime']=json.loads(message.text.split('=',1)[1])
            if message.type=='error':results['console_errors'].append(message.text)
        page.on('console',console)
        def new_tab(tab):
            tab.on('pageerror',lambda e:results['page_errors'].append(str(e)))
            tab.on('console',console)
        context.on('page',new_tab)
        h=Walkthrough(page,results,args.results)
        try:
            start=time.monotonic();page.goto(results['url'],wait_until='domcontentloaded');h.loaded();h.view(0)
            results['initial_render_seconds']=round(time.monotonic()-start,2)
            assert results['runtime']['streamlit']=='1.57.0' and results['runtime']['pyodide']=='0.29.3'
            h.disabled('Back');h.disabled('Forward');h.layout('desktop')
            h.passed('Actual stlite/Streamlit/Pyodide runtime and initial navigation')
            lesson(h)
            assert not results['page_errors'],results['page_errors']
            assert not results['console_errors'],results['console_errors']
            assert not results['external_requests'],results['external_requests']
            assert not any(r.startswith('/_stcore/') for r in requests)
            h.passed('No external requests, server connection or runtime errors')
        except Exception:
            results['checks'].append({'name':'Walkthrough stopped','status':'failed','error':traceback.format_exc()})
            results['body_on_failure']=page.locator('body').inner_text();h.shot('failure')
        browser.close()
    server.shutdown();results['static_requests']=sorted(set(requests))
    (args.results/'browser-results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps({k:v for k,v in results.items() if k not in ('static_requests','body_on_failure')},indent=2),flush=True)
    return int(any(c['status']=='failed' for c in results['checks']))


if __name__=='__main__':
    raise SystemExit(main())
