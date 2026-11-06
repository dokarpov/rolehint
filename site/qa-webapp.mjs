import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { setTimeout as delay } from 'node:timers/promises';

// Fixture-only UI regression. This does not prove live ATS or real authentication.
const server=spawn('python3',['-m','http.server','8789','--directory','.'],{stdio:'ignore'});
const browser=await chromium.launch({headless:true});
const assert=(condition,message)=>{if(!condition)throw Error(message)};
const fixture={source:'ashby',url:'https://jobs.ashbyhq.com/example/open123',
  title:'Senior Product Manager',company:'Example',location:'Remote Europe',
  fit:{label:'Role-only match',matched_terms:[],unconfirmed_terms:[],
    note:'Eligibility and CV fit unverified.'}};
try{
  await delay(950);
  for(const width of [320,375,390,430,768,1440]){
    const page=await browser.newPage({viewport:{width,height:844},isMobile:width<500,hasTouch:width<500});
    const errors=[],searches=[];
    let authenticated=false,profileUnavailable=false;
    page.on('pageerror',e=>errors.push(e.message));
    page.on('popup',async p=>{try{await p.close()}catch{}});
    await page.route('**/web-api/**',async route=>{
      const req=route.request(),path=new URL(req.url()).pathname;
      const respond=(data,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(data)});
      if(path==='/web-api/me'){
        if(profileUnavailable)return respond({detail:'Temporary upstream failure'},503);
        return authenticated
          ?respond({authenticated:true,preferences:{remote_only:false,salary_floor_annual:0},search_profiles:[],jobs:[],free_used:0,free_limit:10})
          :respond({detail:'Please sign in'},401);
      }
      if(path==='/web-api/auth-status')return respond({email_login_available:false,telegram_login_available:true});
      if(path==='/web-api/anonymous/cv-analysis')return respond({
        saved:false,evidence:[{evidence:'Product management, research and delivery outcomes.'}],
        insights:[{message:'Review extracted achievements before using them.'}],
        suggested_roles:['Senior Product Manager']});
      if(path==='/web-api/anonymous/matches'){
        assert(req.method()==='POST','matching must use POST');
        assert(new URL(req.url()).search==='','CV query-string exposure at '+width);
        searches.push(req.postDataJSON());
        return respond({jobs:[fixture],sources_available:true,count:1,limit:10});
      }
      if(path==='/web-api/telegram/begin')return respond({url:'https://t.me/rolehint_test_bot?start=sample'});
      if(path==='/web-api/telegram/complete'){authenticated=true;return respond({ok:true})}
      if(path==='/web-api/release-state')return respond({contractor_only:false,opportunities:[],application_history:[]});
      if(path==='/web-api/cv')return respond({uploaded:false});
      return respond({detail:'Fixture intentionally unavailable'},503);
    });
    await page.goto('http://127.0.0.1:8789/webapp/',{waitUntil:'domcontentloaded'});
    await page.locator('#start-screen').waitFor({state:'visible'});
    assert(await page.getByRole('heading',{name:/Better applications/i}).isVisible(),'missing current hero at '+width);
    assert(!(await page.locator('#auth-zone').isVisible()),'authentication before value at '+width);
    const unlabeled=await page.evaluate(()=>[...document.querySelectorAll('input,textarea,select')]
      .filter(x=>!x.labels?.length&&!x.getAttribute('aria-label')).map(x=>x.id||x.tagName));
    assert(!unlabeled.length,'unlabeled controls '+width+': '+unlabeled.join(','));
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
    assert(overflow<=2,'horizontal overflow '+width+': '+overflow);
    await page.locator('#first-role').fill('Senior Product Manager');
    await page.locator('#role-first button[type=submit]').click();
    await page.locator('.job-card').first().waitFor();
    assert(searches.length===1&&searches[0].cv_terms==='','role-only search leaked context at '+width);
    assert(await page.locator('.job-card a[href="https://jobs.ashbyhq.com/example/open123"]').count()===1,'missing ATS URL');
    await page.locator('#jobs-back').click();
    await page.locator('#cv-input').setInputFiles({
      name:'example.txt',mimeType:'text/plain',
      buffer:Buffer.from('Product manager with research, delivery and business outcomes. '.repeat(4))});
    await page.locator('#anon-results').waitFor({state:'visible'});
    assert(await page.locator('#start-screen').isVisible(),'CV review auto-skipped at '+width);
    assert(searches.length===1,'CV triggered an unapproved automatic search at '+width);
    assert(await page.locator('#first-role').inputValue()==='Senior Product Manager','role suggestion missing');
    await page.locator('#role-first button[type=submit]').click();
    await page.locator('.job-card').first().waitFor();
    assert(searches.length===2&&searches[1].cv_terms.length>0,'CV context not provided to private POST');
    await page.locator('#jobs-back').click();
    await page.locator('#anon-discard').click();
    await page.locator('#role-first button[type=submit]').click();
    await page.locator('.job-card').first().waitFor();
    assert(searches.length===3&&searches[2].cv_terms==='','discarded CV reused at '+width);
    await page.locator('#jobs-notify').click();
    assert(await page.locator('#auth-zone').isVisible(),'optional authentication unavailable at '+width);
    assert(await page.locator('#email-button').isDisabled(),'unconfigured email was enabled');
    assert(await page.locator('#telegram-begin').isEnabled(),'configured Telegram option incorrectly disabled');
    await page.locator('#telegram-begin').click();
    await page.locator('#telegram-code-zone').waitFor({state:'visible'});
    await page.locator('#telegram-code').fill('12345678');
    await page.locator('#telegram-complete button[type=submit]').click();
    await page.locator('#member').waitFor({state:'visible'});
    await page.locator('#target-role').fill('RoleHint account retry fixture');
    profileUnavailable=true;
    await page.evaluate(()=>window.refresh());
    assert(await page.locator('#member').isVisible(),'503 incorrectly logged out a real user at '+width);
    assert(!(await page.locator('#guest').isVisible()),'503 incorrectly exposed guest state at '+width);
    assert(await page.locator('#retry-workspace').isVisible(),'503 did not show connection Retry at '+width);
    assert(await page.locator('#target-role').inputValue()==='RoleHint account retry fixture',
      '503 discarded unsaved role at '+width);
    const errorOverflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
    assert(errorOverflow<=2,'retry state horizontal overflow at '+width+': '+errorOverflow);
    profileUnavailable=false;
    await page.locator('#retry-workspace').click();
    await page.locator('#retry-workspace').waitFor({state:'hidden'});
    assert(await page.locator('#member').isVisible(),'successful retry did not recover member view');
    assert(await page.locator('#target-role').inputValue()==='RoleHint account retry fixture',
      'retry discarded unsaved role at '+width);
    authenticated=false;
    await page.evaluate(()=>window.refresh());
    assert(!(await page.locator('#member').isVisible()),'real 401 did not end session');
    assert(await page.locator('#guest').isVisible(),'real 401 did not show guest');
    assert(!(await page.locator('#retry-workspace').isVisible()),'real logout shows stale retry control');
    assert(!errors.length,'page exceptions '+width+': '+errors.join(' | '));
    console.log('PASS fixture UX',width);
    await page.close();
  }
  // When neither transport is configured, neither sign-in option is
  // advertised as usable. Anonymous discovery remains available.
  const noProvider=await browser.newPage({viewport:{width:390,height:844}});
  await noProvider.route('**/web-api/auth-status',route=>route.fulfill({
    status:200,contentType:'application/json',
    body:'{"email_login_available":false,"telegram_login_available":false}'}));
  await noProvider.route('**/web-api/me',route=>route.fulfill({
    status:401,contentType:'application/json',body:'{"detail":"Sign in"}'}));
  await noProvider.goto('http://127.0.0.1:8789/webapp/',{waitUntil:'domcontentloaded'});
  await noProvider.locator('#auth-zone').waitFor({state:'hidden'});
  await noProvider.locator('#jobs-notify').count();
  await noProvider.waitForFunction(()=>
    document.getElementById('telegram-begin').disabled &&
    document.getElementById('email-button').disabled);
  assert(await noProvider.locator('#start-screen').isVisible(),
    'anonymous first value blocked by unconfigured sign-in providers');
  await noProvider.close();
}finally{await browser.close();server.kill()}
console.log('Current RoleHint webapp fixture smoke passed; live end-to-end remains required.');
