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
      if(pathname.endsWith('/application-board'))return respond({summary:{opportunities:0,confirmed_submitted:0,interviews:0,offers:0},counts:{},items:[]});
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
    else if(u.endsWith('/application-board'))body={
      summary:{opportunities:3,confirmed_submitted:1,interviews:1,offers:0},
      counts:{review:1,handoff:1,interview:1},
      items:[
        {job_id:'ashby:123',company:'Example employer',title:'Product Manager',location:'Remote Spain',source_url:'https://jobs.example.org/123',stage:'review',stage_label:'To review',evidence_gaps:2,submitted_at:null,pack_version:null},
        {job_id:'ats:handoff',company:'Unsubmitted Ltd',title:'Design Lead',location:'Europe',source_url:'https://jobs.example.org/other',stage:'handoff',stage_label:'Employer form opened',submitted_at:null,pack_version:2},
        {job_id:'ats:interview',company:'Interview Studio',title:'Senior PM',location:'Remote',source_url:'https://jobs.example.org/interview',stage:'interview',stage_label:'Recruiter / interview',submitted_at:'2026-10-20T12:00:00+00:00'}
      ]};
    else if(u.endsWith('/cv'))body={uploaded:false};
    else if(u.endsWith('/editorial-profile'))body={exists:true,profile:{
      name:'Test Candidate',headline:'Senior Product Manager',city:'Barcelona, Spain',
      email:'candidate@example.com',linkedin:'https://www.linkedin.com/in/test',
      skills:['Product strategy','Experimentation'],
      experiences:[{title:'Product Manager',company:'Sample Learning',period:'2023–2026',
        bullets:['Led customer discovery and improved workflows.']}],
      extras:[{heading:'Strength',value:'Product experiments'}],approved:false}};
    else if(u.endsWith('/google/status'))body={
      connected:false,gmail_readonly:false,calendar_events:false,can_send_email:false};
    else if(u.endsWith('/documents/draft'))body={interest:'',body:'',approved:false,version:0};
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
  await page.locator('#board-list .board-entry').first().waitFor({state:'visible',timeout:5000});
  if((await page.locator('#board-list .board-entry').count())!==3)throw Error('pipeline did not show all source states '+width);
  if(!(await page.getByText('Employer form opened; submission unconfirmed').isVisible()))throw Error('handoff was incorrectly treated as submitted '+width);
  if(!(await page.locator('#board-metrics').getByText('Confirmed applications').isVisible()))throw Error('application metrics absent '+width);
  if((await page.evaluate(()=>document.documentElement.scrollWidth))>width+2)throw Error('tracker causes horizontal overflow '+width);
  await page.locator('#board-stage-filter').selectOption('interview');
  if((await page.locator('#board-list .board-entry').count())!==1)throw Error('stage filter did not work '+width);
  if(!(await page.getByText('Interview Studio').isVisible()))throw Error('stage filter selected wrong company '+width);
  await page.locator('#board-stage-filter').selectOption('all');
  await page.locator('#board-search').fill('Unsubmitted');
  if((await page.locator('#board-list .board-entry').count())!==1)throw Error('company search did not work '+width);
  await page.locator('#board-search').fill('');
  if(!(await page.locator('#capture-ats-url').isVisible()))throw Error('direct employer ATS import missing '+width);
  if(!(await page.locator('#capture-ats-form button').isVisible()))throw Error('capture action missing '+width);
  await page.locator('#editorial-name').waitFor({state:'visible',timeout:5000});
  if((await page.locator('#editorial-name').inputValue())!=='Test Candidate')throw Error('template profile did not load '+width);
  if((await page.locator('[data-editorial-experience]').count())!==1)throw Error('editable experience not loaded '+width);
  if(!(await page.locator('#editorial-html').isVisible()))throw Error('source HTML template import unavailable '+width);
  if(!(await page.locator('#google-connect').isVisible()))throw Error('Google consent missing '+width);
  if(!(await page.locator('#google-inbox-load').isDisabled()))throw Error('Gmail inbox readable without consent '+width);
  if(!(await page.locator('#google-calendar-create').isDisabled()))throw Error('Google Calendar writable without consent '+width);
  if((await page.evaluate(()=>document.documentElement.scrollWidth))>width+2)throw Error('new template or Google panel overflows '+width);
  await page.getByRole('button',{name:'Review fit & prepare'}).click();
  await page.getByText('Required: product strategy').waitFor({state:'visible',timeout:6000});
  await page.getByText(/B2B contractor status: unconfirmed/).waitFor({state:'visible',timeout:6000});
  if(!(await page.locator('#editorial-document-zone').isVisible()))throw Error('role-specific CV and letter panel missing '+width);
  if(!(await page.locator('#doc-export-approved').isVisible()))throw Error('explicit document export approval missing '+width);
  if(!(await page.locator('#job-recheck').isVisible()))throw Error('employer freshness control missing '+width);
  if(!(await page.locator('#contractor').isChecked()))throw Error('saved B2B preference missing');
  if(!(await page.getByRole('button',{name:'Open employer application form'}).isVisible()))throw Error('review/handoff missing');
  console.log('PASS authenticated workspace fixtures and vacancy source URL');
  await page.close();}
}finally{await browser.close();server.kill();}
