import {chromium} from 'playwright';
import {spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';

// Real browser / DOM tests using only fixture API, NOT live OAuth or ATS.
const web=spawn('python3',['-m','http.server','8791','--directory','.'],{stdio:'ignore'});
const browser=await chromium.launch({headless:true});
const assert=(condition,message)=>{if(!condition)throw Error(message)};
try{
  await delay(700);
  for(const width of [320,375,390,430,768,1440]){
    const page=await browser.newPage({viewport:{width,height:844},isMobile:width<500,hasTouch:width<500});
    const errors=[], requests=[], candidates=[];
    page.on('pageerror',e=>errors.push(e.message));
    page.on('dialog',dialog=>dialog.accept());
    await page.route('**/web-api/**',async route=>{
      const request=route.request(),path=new URL(request.url()).pathname;
      const reply=(data,status=200,headers={})=>route.fulfill({
        status,contentType:'application/json',headers,body:JSON.stringify(data)});
      if(path==='/web-api/me')return reply({authenticated:true,search_profiles:[],jobs:[],preferences:{}});
      if(path==='/web-api/evidence/candidates'&&request.method()==='GET')
        return reply({candidates});
      if(path==='/web-api/evidence/candidates'&&request.method()==='POST'){
        assert(request.headers().origin==='http://127.0.0.1:8791','missing CSRF Origin');
        const payload=request.postDataJSON();
        assert(payload.candidates.length===1,'invalid batch');
        requests.push(payload);
        const item={...payload.candidates[0],id:'eic_'+requests.length,
          status:'needs-review',visibility:'private',approved_evidence_id:null};
        candidates.unshift(item);
        return reply({items:[{created:true,candidate:item}]},201);
      }
      const match=path.match(/^\/web-api\/evidence\/candidates\/(eic_\d+)$/);
      if(match&&request.method()==='PATCH'){
        assert(request.headers().origin==='http://127.0.0.1:8791','missing review Origin');
        const item=candidates.find(x=>x.id===match[1]);
        if(!item)return reply({detail:'Not found'},404);
        const payload=request.postDataJSON();
        item.status=payload.decision==='approve'?'approved-self-reported':'rejected';
        if(payload.claim)item.claim=payload.claim;
        return reply({candidate:item});
      }
      if(match&&request.method()==='DELETE'){
        const i=candidates.findIndex(x=>x.id===match[1]);
        if(i<0)return reply({detail:'Not found'},404);
        candidates.splice(i,1);return reply({deleted:true});
      }
      if(path==='/web-api/evidence/connections')return reply({connections:[]});
      if(path==='/web-api/login')return reply({message:'Check your email'});
      return reply({detail:'Fixture endpoint unavailable'},503);
    });
    await page.route('**/.well-known/oauth-protected-resource/mcp',route=>route.fulfill({
      status:200,contentType:'application/json',
      body:JSON.stringify({resource:'http://127.0.0.1:8791/mcp'})}));
    await page.goto('http://127.0.0.1:8791/webapp/evidence.html',{waitUntil:'domcontentloaded'});
    await page.locator('#project').waitFor();
    assert(await page.locator('.wordmark').textContent()==='rolehint','wordmark not text-only');
    assert(!(await page.locator('#gate').isVisible()),'signed-in user sees unnecessary sign-in');
    assert(await page.locator('#connector-ready').isVisible(),'hosted connection status missing');
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
    assert(overflow<=2,'horizontal overflow '+width+': '+overflow);
    const unlabeled=await page.evaluate(()=>[...document.querySelectorAll('input,textarea,select')]
      .filter(el=>!el.labels?.length&&!el.getAttribute('aria-label')).map(el=>el.id));
    assert(!unlabeled.length,'unlabeled controls '+width+': '+unlabeled.join(','));

    await page.locator('#project').fill('RoleHint');
    await page.locator('#claim').fill('Built a verifiable vacancy review experience');
    await page.locator('#excerpt').fill('The source shows a tested matching journey with manual review of actual listings.');
    await page.locator('#source-ref').fill('product-research.md');
    await page.locator('#save').click();
    await page.getByText('Saved privately. Review before using it.').waitFor();
    assert(requests.length===1,'evidence capture failed '+width);
    assert(new URL(page.url()).search==='','private evidence exposed in URL');
    await page.locator('.card details summary').click();
    assert(await page.locator('.card .excerpt').textContent()==='The source shows a tested matching journey with manual review of actual listings.','source excerpt mismatch');
    await page.getByRole('button',{name:'Approve as self-reported'}).click();
    await page.getByText('Reviewed · self-reported').waitFor();
    assert(candidates[0].status==='approved-self-reported','review state mismatch');
    await page.locator('.card details summary').click();
    await page.getByRole('button',{name:'Delete draft'}).click();
    await page.getByText('No items in this view.').waitFor();

    // Browser-only text file picker never sends data until explicit Save.
    await page.locator('#file').setInputFiles({
      name:'source.md',mimeType:'text/markdown',buffer:Buffer.from('A selected local project note.')});
    await page.waitForFunction(()=>document.querySelector('#excerpt').value.includes('selected local project note'),null,{timeout:5000});
    assert(requests.length===1,'file auto-uploaded without user submission');
    assert(!errors.length,'JS errors '+width+': '+errors.join('; '));
    console.log('PASS Evidence Inbox mobile/browser',width);
    await page.close();
  }
  const guest=await browser.newPage();
  let submitCount=0;
  await guest.route('**/web-api/me',route=>route.fulfill({status:401,contentType:'application/json',body:'{"detail":"Sign in"}'}));
  await guest.route('**/web-api/evidence/candidates',route=>{
    submitCount++;return route.fulfill({status:401,contentType:'application/json',body:'{"detail":"Sign in"}'});
  });
  await guest.goto('http://127.0.0.1:8791/webapp/evidence.html',{waitUntil:'domcontentloaded'});
  await guest.locator('#gate').waitFor({state:'visible'});
  await guest.locator('#project').fill('RoleHint');
  await guest.locator('#claim').fill('Reviewed the first-job experience');
  await guest.locator('#excerpt').fill('A user study recording consistent first-value outcomes.');
  await guest.locator('#source-ref').fill('study.md');
  await guest.locator('#save').click();
  assert(submitCount===0,'guest attempted unsafe cloud upload');
  assert(await guest.locator('#claim').inputValue()==='Reviewed the first-job experience','guest draft lost');
  console.log('PASS Evidence Inbox guest privacy');
  await guest.close();
}finally{
  await browser.close();
  web.kill();
}
console.log('Evidence Inbox fixture browser QA complete; real account E2E still required.');
