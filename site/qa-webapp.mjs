import {chromium} from 'playwright';
import {spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
const server=spawn('python3',['-m','http.server','8789','--directory','.'],{stdio:'ignore'});
const browser=await chromium.launch({headless:true});
try{
  await delay(900);
  for(const width of [320,375,390,768,1440]){
    const page=await browser.newPage({viewport:{width,height:780},isMobile:width<500,hasTouch:width<500});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));let telegramAuthenticated=false;
    await page.route('**/web-api/**',async route=>{
      const url=new URL(route.request().url());
      const pathname=url.pathname;
      const respond=data=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(data)});
      if(pathname.endsWith('/me')) return telegramAuthenticated?respond({authenticated:true,preferences:{remote_only:false,salary_floor_annual:0},search_profiles:[],jobs:[],free_used:0,free_limit:10}):route.fulfill({status:401,contentType:'application/json',body:'{"detail":"Please sign in"}'});
      if(pathname.endsWith('/telegram/begin'))return respond({url:'https://t.me/rolehint_test_bot?start=web_sample',message:'Open Telegram'});
      if(pathname.endsWith('/telegram/complete')){telegramAuthenticated=true;return respond({ok:true})}
      if(pathname.endsWith('/cv'))return respond({uploaded:false});
      if(pathname.endsWith('/release-state'))return respond({contractor_only:false,opportunities:[],application_history:[]});
      if(pathname.endsWith('/auth-status')) return respond({email_login_available:false});
      return route.fulfill({status:503,contentType:'application/json',body:'{"detail":"Unavailable"}'});
    });
    await page.goto('http://127.0.0.1:8789/webapp/',{waitUntil:'networkidle'});
    if(!(await page.getByRole('heading',{name:/Find work worth/}).isVisible()))throw Error('missing hero '+width);
    const unlabeled=await page.evaluate(()=>[...document.querySelectorAll('input,textarea,select')].filter(x=>!x.labels?.length && !x.getAttribute('aria-label')).map(x=>x.id||x.tagName));
    if(unlabeled.length)throw Error('Unlabeled form fields '+width+': '+unlabeled.join(','));
    if((await page.locator('h1').count())!==2)throw Error('Expected separate guest and account headings for conditional views '+width);

    const docWidth=await page.evaluate(()=>document.documentElement.scrollWidth);
    if(docWidth>width+2)throw Error('horizontal overflow '+width+' '+docWidth);
    await page.locator('#first-role').fill('Senior Product Manager');
    await page.getByRole('button',{name:'Continue with this role'}).click();
    if(!(await page.locator('#auth-zone').isVisible()))throw Error('no auth transition '+width);
    if(!(await page.locator('#email-button').isDisabled()))throw Error('unconfigured login should be disabled '+width);
    if((await page.evaluate(()=>sessionStorage.getItem('rolehint_intended_role')))!=='Senior Product Manager')throw Error('role not persisted '+width);
    page.on('popup',async p=>{try{await p.close()}catch{}});
    await page.getByRole('button',{name:'Sign in with Telegram'}).click();
    await page.locator('#telegram-code-zone').waitFor({state:'visible',timeout:5000});
    await page.locator('#telegram-code').fill('12345678');
    await page.getByRole('button',{name:'Complete sign-in'}).click();
    await page.locator('#member').waitFor({state:'visible',timeout:5000});
    if((await page.locator('#target-role').inputValue())!=='Senior Product Manager')throw Error('intended role lost on login '+width);
    if(errors.length)throw Error('page errors '+width+': '+errors.join('; '));
    await page.close();
    console.log('PASS anonymous mobile-first role/auth gate',width);
  }
  for(const width of [390,1280]){const page=await browser.newPage({viewport:{width,height:844}});
  await page.route('**/web-api/**',async route=>{
    const u=route.request().url();let body={};
    if(u.endsWith('/me'))body={authenticated:true,preferences:{remote_only:true,salary_floor_annual:85000},search_profiles:[{query:'Product Manager'}],jobs:[{job_id:'ashby:123',title:'Product Manager',company:'Example employer',source_url:'https://jobs.example.org/123'}],free_used:1,free_limit:10};
    else if(u.endsWith('/auth-status'))body={email_login_available:false};
    else if(u.endsWith('/release-state'))body={contractor_only:true,opportunities:[],application_history:[]};
    else if(u.endsWith('/cv'))body={uploaded:false};
    else if(u.endsWith('/review'))body={job_id:'ashby:123',title:'Product Manager',company:'Example employer',requirements:[{label:'product strategy',mustHave:true}],proposal:{interview_risks:[]},final_action:'VERIFY_FIRST',contractor_status:'unconfirmed',freshness:'Employer source refreshed',constraints:{}};
    else if(u.endsWith('/pack'))body={data:{role:{company:'Example employer',title:'Product Manager'},positioning:'',recruiter_note:'',proof_cards:[],short_answers:[],interview_risks:[]}};
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
  });
  await page.goto('http://127.0.0.1:8789/webapp/',{waitUntil:'networkidle'});
  if(!(await page.getByRole('heading',{name:'Your opportunities'}).isVisible()))throw Error('member workspace absent');
  if(!(await page.getByText('1 of 10 free opportunities delivered').isVisible()))throw Error('quota absent');
  const link=page.getByRole('link',{name:'Product Manager'});
  if(!(await link.isVisible()))throw Error('real vacancy absent');
  if((await link.getAttribute('href'))!=='https://jobs.example.org/123')throw Error('incorrect employer URL');
  await page.getByRole('button',{name:'Review fit & prepare'}).click();
  await page.getByText('Required: product strategy').waitFor({state:'visible',timeout:6000});
  await page.getByText(/B2B contractor status: unconfirmed/).waitFor({state:'visible',timeout:6000});
  if(!(await page.locator('#contractor').isChecked()))throw Error('saved B2B preference missing');
  if(!(await page.getByRole('button',{name:'Open employer application form'}).isVisible()))throw Error('review/handoff missing');
  console.log('PASS authenticated workspace fixtures and vacancy source URL');
  await page.close();}
}finally{await browser.close();server.kill();}
