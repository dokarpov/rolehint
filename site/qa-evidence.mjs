import {chromium,webkit} from 'playwright';
import {spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
import {readFile} from 'node:fs/promises';

const server=spawn('python3',['-m','http.server','8791','--directory','.'],{stdio:'ignore'});
const engine=process.env.ROLEHINT_BROWSER_ENGINE==='webkit'?'webkit':'chromium';
const browser=await (engine==='webkit'?webkit:chromium).launch({headless:true});
const base='http://127.0.0.1:8791';
const assert=(value,message)=>{if(!value)throw Error(message)};

async function setup(page,authenticated,candidates=[],requests=[]){
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('dialog',dialog=>dialog.accept());
  await page.route('**/.well-known/oauth-protected-resource/mcp',route=>route.fulfill({
    status:200,contentType:'application/json',body:JSON.stringify({resource:base+'/mcp'})}));
  await page.route('**/web-api/**',async route=>{
    const request=route.request(),path=new URL(request.url()).pathname;
    const method=request.method();
    const respond=(data,status=200)=>route.fulfill({
      status,contentType:'application/json',body:JSON.stringify(data)});
    if(path==='/web-api/auth-status')return respond({email_login_available:authenticated});
    if(path==='/web-api/me')
      return authenticated?respond({authenticated:true}):respond({detail:'Please sign in'},401);
    if(path==='/web-api/evidence/candidates'&&method==='GET')
      return authenticated?respond({candidates}):respond({detail:'Please sign in'},401);
    if(path==='/web-api/evidence/candidates'&&method==='POST'){
      assert(authenticated,'guest attempted cloud save');
      assert(request.headers().origin===base,'missing same-origin protection');
      const data=request.postDataJSON();
      assert(data.candidates.length===1,'one candidate required');
      const item={...data.candidates[0],id:'eic_'+(requests.length+1),status:'needs-review',
        visibility:'private',approved_evidence_id:null};
      requests.push(item);candidates.unshift(item);
      return respond({items:[{created:true,candidate:item}]},201);
    }
    const match=path.match(/^\/web-api\/evidence\/candidates\/(eic_\d+)$/);
    if(match&&method==='PATCH'){
      assert(request.headers().origin===base,'review missing origin');
      const item=candidates.find(value=>value.id===match[1]);
      if(!item)return respond({detail:'Not found'},404);
      const payload=request.postDataJSON();
      item.status=payload.decision==='approve'?'approved-self-reported':'rejected';
      if(payload.claim)item.claim=payload.claim;
      return respond({candidate:item});
    }
    if(match&&method==='DELETE'){
      const idx=candidates.findIndex(value=>value.id===match[1]);
      if(idx>=0)candidates.splice(idx,1);
      return respond({deleted:true});
    }
    if(path==='/web-api/evidence/connections')return respond({connections:[]});
    if(path==='/web-api/login')return respond({message:'Check your email'});
    return respond({detail:'Fixture endpoint unavailable'},503);
  });
  return errors;
}

async function fillSource(page,excerpt){
  await page.locator('#excerpt').fill(excerpt);
  assert(await page.locator('#continue').isEnabled(),'Continue did not unlock after adding source');
  await page.locator('#continue').click();
  await page.locator('#claim-step').waitFor({state:'visible'});
  assert(!(await page.locator('#source-editor').isVisible()),'source editor did not collapse');
  assert(await page.locator('#source-summary').isVisible(),'source summary was not shown');
}

try{
  await delay(700);
  for(const width of [320,375,390,430,768,1440]){
    const page=await browser.newPage({
      viewport:{width,height:844},isMobile:width<500,hasTouch:width<500,acceptDownloads:true
    });
    const candidates=[],requests=[];
    const errors=await setup(page,true,candidates,requests);
    await page.goto(base+'/webapp/evidence.html',{waitUntil:'domcontentloaded'});
    await page.locator('#source-step').waitFor({state:'visible'});
    await page.locator('#review-section').waitFor({state:'visible'});
    assert((await page.locator('.wordmark').innerText())==='rolehint','wordmark not text-only');
    assert(!(await page.locator('#claim-step').isVisible()),'claim form appears before source');
    assert(!(await page.locator('#source-details').isVisible()),'advanced fields appear immediately');
    assert(!(await page.locator('#gate').isVisible()),'authenticated account sees login wall');
    assert(!(await page.locator('#connections-panel').evaluate(el=>el.open)),'connector is expanded by default');
    assert(await page.locator('#continue').isDisabled(),'Continue active without a source');
    let overflow=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
    assert(overflow<=2,'horizontal overflow at '+width+': '+overflow);
    await fillSource(page,'A source log describes the results of a manually reviewed vacancy verification test.');
    assert(!(await page.locator('#source-kind').isVisible()),'optional source metadata is exposed');
    assert(!(await page.locator('#boundary').isVisible()),'optional claim boundary is exposed');
    assert(await page.locator('#save').isVisible(),'primary signed-in save action missing');
    await page.locator('#project').fill('RoleHint');
    await page.locator('#claim').fill('Built the reviewed vacancy verification workflow');
    await page.locator('#source-ref').fill('research-notes.md');
    await page.locator('#save').click();
    await page.getByText('Saved privately. Review the new claim.').waitFor();
    assert(requests.length===1,'source was not saved once');
    assert(await page.locator('#claim-step').isHidden(),'claim step did not reset after save');
    assert(await page.locator('#source-editor').isVisible(),'source did not reset after save');
    assert((await page.locator('.card').count())===1,'review inbox missing saved candidate');
    await page.locator('.card details summary').click();
    assert((await page.locator('.card .excerpt').innerText()).includes('A source log describes'),'source excerpt not available on request');
    await page.getByRole('button',{name:'Approve as self-reported'}).click();
    await page.locator('.card .pill.approved').waitFor({state:'visible'});
    await page.locator('.card details summary').click();
    await page.getByRole('button',{name:'Delete evidence'}).click();
    await page.getByText(/No saved evidence yet/).waitFor();
    await page.locator('#file').setInputFiles({
      name:'notes.md',mimeType:'text/markdown',buffer:Buffer.from('A new selected local source note.')
    });
    await page.waitForFunction(()=>document.getElementById('excerpt').value.includes('new selected local source note'));
    assert(requests.length===1,'file picker auto-uploaded without review');
    assert(errors.length===0,'JavaScript errors at '+width+': '+errors.join('; '));
    console.log('PASS progressive evidence flow',engine,width);
    await page.close();
  }

  const guest=await browser.newPage({
    viewport:{width:390,height:844},isMobile:true,hasTouch:true,acceptDownloads:true
  });
  const errors=await setup(guest,false);
  await guest.goto(base+'/webapp/evidence.html',{waitUntil:'domcontentloaded'});
  await guest.locator('#continue').waitFor({state:'visible'});
  assert(!(await guest.locator('#gate').isVisible()),'guest sees unavailable login before choosing source');
  assert(!(await guest.locator('#review-section').isVisible()),'guest sees empty private inbox');
  assert(!(await guest.locator('#connections-panel').isVisible()),'guest sees connector settings');
  await fillSource(guest,'A written source states the research and review steps for the experience.');
  await guest.locator('#gate').waitFor({state:'visible'});
  await guest.getByText('Online saving is unavailable here').waitFor();
  assert(!(await guest.locator('#login-controls').isVisible()),'unconfigured email login offered');
  assert(!(await guest.locator('#save').isVisible()),'unavailable cloud save is primary');
  assert(await guest.locator('#export-local').isVisible(),'offline primary download unavailable');
  await guest.locator('#project').fill('RoleHint');
  await guest.locator('#claim').fill('Reviewed the onboarding experience');
  await guest.locator('#source-ref').fill('ux-review.md');
  const event=guest.waitForEvent('download');
  await guest.locator('#export-local').click();
  const download=await event;
  const raw=await readFile(await download.path(),'utf8');
  const draft=JSON.parse(raw);
  assert(draft.format==='rolehint-evidence-draft','invalid draft format');
  assert(draft.visibility==='private'&&draft.status==='needs-review','draft claims verified status');
  assert(draft.candidate.claim==='Reviewed the onboarding experience','draft lost contribution');
  await guest.locator('#edit-source').click();
  await guest.locator('#excerpt').fill('');
  await guest.locator('#file').setInputFiles({
    name:'rolehint-private-evidence-draft.json',mimeType:'application/json',buffer:Buffer.from(raw)
  });
  await guest.getByText(/Draft restored/).waitFor();
  assert(await guest.locator('#claim').inputValue()==='Reviewed the onboarding experience','import lost claim');
  assert(await guest.locator('#project').inputValue()==='RoleHint','import lost project');
  assert(errors.length===0,'guest JS errors: '+errors.join('; '));
  console.log('PASS progressive guest/offline source capture and portable draft',engine);
  await guest.close();
}finally{
  await browser.close();
  server.kill();
}
console.log('Evidence Inbox fixture QA passed in '+engine+'; real account and physical iPhone acceptance still required.');
