"""UI fixture regression only. Live server journey is tested separately."""
from playwright.sync_api import sync_playwright
import json,threading,http.server
server=http.server.ThreadingHTTPServer(('127.0.0.1',8790),http.server.SimpleHTTPRequestHandler)
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--no-zygote','--single-process'])
 for width in (390,1440):
  page=browser.new_page(viewport={'width':width,'height':900})
  searches=[]
  cv='Product Manager with research, analytics and roadmap ownership. Led customer discovery and onboarding.'
  def route(r):
   path=r.request.url.split('/web-api/')[1]
   if path=='me':return r.fulfill(status=401,json={'detail':'Please sign in'})
   if path=='auth-status':return r.fulfill(json={'telegram_login_available':True,'email_login_available':False})
   if path=='anonymous/cv-analysis':return r.fulfill(json={'text':cv,'evidence':[{'evidence':cv}],'insights':[],'suggested_roles':['Product Manager']})
   if path=='anonymous/matches':
    searches.append(r.request.post_data_json)
    return r.fulfill(json={'jobs':[{'title':'Product Manager','company':'QA only','location':'Remote','url':'https://example.com/qa-only','fit':{'label':'Some CV evidence','matched_terms':['research'],'unconfirmed_terms':['sql'],'note':'Keyword signals only'}}]})
   return r.fulfill(status=404,json={})
  page.route('**/web-api/**',route)
  page.goto('http://127.0.0.1:8790/webapp/')
  page.locator('#cv-input').set_input_files({'name':'cv.txt','mimeType':'text/plain','buffer':cv.encode()})
  page.locator('#anon-results').wait_for(state='visible')
  page.locator('#anon-cv-text').fill(cv+' SQL reporting.')
  page.locator('#role-first button').click()
  page.locator('.match-badge').wait_for()
  assert 'SQL reporting' in searches[-1]['cv_terms']
  page.get_by_role('button',name='Prepare this application').click()
  page.locator('#draft-cv').fill(cv+' SQL reporting.')
  page.locator('#draft-motivation').fill('I want to improve access to education.')
  page.locator('#draft-gap-context').fill('I am developing SQL skills; I have not used SQL professionally.')
  page.locator('#draft-build-letter').click()
  assert 'I want to improve access' in page.locator('#draft-letter').input_value()
  assert 'not used SQL professionally' in page.locator('#draft-letter').input_value()
  page.locator('#draft-approve').check()
  with page.expect_download() as d:page.locator('#draft-download-cv').click()
  assert d.value.suggested_filename.endswith('.txt')
  page.locator('#draft-back').click()
  page.locator('#jobs-back').click()
  page.locator('#cv-input').set_input_files({'name':'invalid.jpg','mimeType':'image/jpeg','buffer':b'bad'})
  page.locator('#role-first button').click()
  page.wait_for_function("document.querySelector('#jobs-status').textContent.includes('live-source')")
  assert searches[-1]['cv_terms']=='','failed replacement leaked old CV context'
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+2')
  page.close()
 browser.close()
server.shutdown()
print('PASS: CV review, badges, per-job drafts, truthful gap context, exports, stale-CV clearing at 390/1440')
