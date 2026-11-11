/* Read-only Gmail and explicitly approved Google Calendar workbench. */
'use strict';
let googleMessages=[];
function googleUiStatus(message){document.getElementById('google-status').textContent=message}
function googleOptions(select,items,getValue,getTitle){
  select.replaceChildren();
  const frag=document.createDocumentFragment();
  for(const item of items){
    const option=document.createElement('option');
    option.value=getValue(item);option.textContent=getTitle(item);frag.append(option);
  }
  select.append(frag);
}
function refreshGoogleJobs(){
  const jobs=window.rolehintJobs||[];
  for(const id of ['google-email-job','google-calendar-job']){
    const el=document.getElementById(id);
    if(el)googleOptions(el,jobs,x=>x.job_id,x=>x.company+' — '+x.title);
  }
  googleUiStatus(jobs.length?'Choose a verified vacancy for linking.':'Add a real vacancy before linking an email or calendar event.');
}
async function loadWorkspaceGoogle(){
  try{
    const state=await api('google/status');
    document.getElementById('google-disconnect').classList.toggle('hide',!state.connected);
    document.getElementById('google-connect').classList.toggle('hide',
      state.connected&&state.gmail_readonly&&state.calendar_events);
    document.getElementById('google-inbox-load').disabled=!state.gmail_readonly;
    document.getElementById('google-calendar-load').disabled=!state.calendar_events;
    document.getElementById('google-calendar-create').disabled=!state.calendar_events;
    document.getElementById('google-email-link').disabled=!state.gmail_readonly;
    googleUiStatus(!state.connected?'Not connected. No email or calendar data is read.':
       state.gmail_readonly&&state.calendar_events?
       'Google connected: Gmail read-only + Calendar event access. No automatic sending or scheduling.':
       'Google connected but permissions are incomplete. Reconnect to enable both.');
    refreshGoogleJobs();
  }catch(err){googleUiStatus('Cannot check Google connection: '+err.message)}
}
function googleRenderInbox(messages){
  const target=document.getElementById('google-inbox-list');
  target.replaceChildren();
  if(!messages?.length){target.textContent='No matching inbox messages found in the latest 30 days.';return}
  const list=document.createDocumentFragment();
  for(const m of messages){
    const row=document.createElement('article');row.className='google-message';
    const title=document.createElement('strong');title.textContent=m.subject||'(no subject)';
    const from=document.createElement('span');from.className='fine';from.textContent=m.from+' · '+m.date;
    const suggestion=document.createElement('span');suggestion.className='fine';
    suggestion.textContent='Suggested: '+String(m.suggested_event||'other').replaceAll('_',' ')+' · review required';
    row.append(title,from,suggestion);
    if(m.url&&m.url.startsWith('https://mail.google.com/')){
      const a=document.createElement('a');a.href=m.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Open in Gmail';row.append(a);
    }
    list.append(row);
  }
  target.append(list);
}
function googleRenderCalendar(events){
  const target=document.getElementById('google-calendar-list');
  target.replaceChildren();
  if(!events?.length){target.textContent='No upcoming events in the next 21 days.';return}
  for(const ev of events){
    const item=document.createElement('p');item.className='google-event';
    const dt=ev.start&&ev.start.includes('T')?new Date(ev.start).toLocaleString():(ev.start||'All day');
    item.textContent=dt+' · '+(ev.summary||'Untitled event');target.append(item);
  }
}
function initGoogleWorkspace(){
  document.getElementById('google-connect').onclick=async()=>{
    googleUiStatus('Opening Google consent screen…');
    try{
      const x=await api('google/connect',{method:'POST',body:'{}'});
      if(!x.url.startsWith('https://accounts.google.com/'))throw Error('Unexpected authorization URL');
      location.assign(x.url);
    }catch(err){googleUiStatus(err.message)}
  };
  document.getElementById('google-disconnect').onclick=async()=>{
    if(!confirm('Disconnect Google from RoleHint? This removes saved access for this account.'))return;
    try{const r=await api('google/disconnect',{method:'POST',body:'{}'});googleMessages=[];googleRenderInbox([]);googleRenderCalendar([]);await loadWorkspaceGoogle();googleUiStatus('Disconnected. Google revocation: '+r.google_revoke)}
    catch(err){googleUiStatus(err.message)}
  };
  document.getElementById('google-inbox-load').onclick=async()=>{
    googleUiStatus('Checking recent inbox messages. No statuses will change…');
    try{
      const data=await api('google/inbox');googleMessages=data.messages||[];
      googleRenderInbox(googleMessages);
      googleOptions(document.getElementById('google-message-select'),googleMessages,
        m=>m.message_id,m=>(m.subject||'(no subject)')+' · '+m.from);
      googleUiStatus('Read-only preview. Select an email and vacancy to save a reviewed association.');
    }catch(err){googleUiStatus(err.message)}
  };
  document.getElementById('google-email-link').onclick=async()=>{
    const id=document.getElementById('google-message-select').value;
    const jid=document.getElementById('google-email-job').value;
    const kind=document.getElementById('google-email-event').value;
    if(!document.getElementById('google-email-confirm').checked){
      googleUiStatus('Confirm this email and vacancy association explicitly.');return}
    try{
      const x=await api('google/inbox/link',{method:'POST',body:JSON.stringify({
        message_id:id,job_id:jid,event_type:kind,approved:true
      })});
      googleUiStatus(x.duplicate?'This message was already recorded.':'Email linked after your review. No application was submitted.');
      document.getElementById('google-email-confirm').checked=false;
    }catch(err){googleUiStatus(err.message)}
  };
  document.getElementById('google-calendar-load').onclick=async()=>{
    googleUiStatus('Reading upcoming calendar events…');
    try{const x=await api('google/calendar');googleRenderCalendar(x.events||[]);googleUiStatus('Calendar loaded (21 days). No changes made.')}
    catch(err){googleUiStatus(err.message)}
  };
  document.getElementById('google-calendar-create').onclick=async()=>{
    if(!document.getElementById('google-calendar-confirm').checked){
      googleUiStatus('Approve this calendar slot before creating it.');return}
    const data={
      job_id:document.getElementById('google-calendar-job').value,
      start:document.getElementById('google-calendar-start').value,
      minutes:Number(document.getElementById('google-calendar-duration').value),
      approved:true
    };
    googleUiStatus('Checking conflicts before writing to Google Calendar…');
    try{
      const x=await api('google/calendar/preparation',{method:'POST',body:JSON.stringify(data)});
      googleUiStatus(x.created?'Preparation event created with an alert at the start.':'Existing preparation event reused. No duplicate created.');
      document.getElementById('google-calendar-confirm').checked=false;
      await document.getElementById('google-calendar-load').click();
    }catch(err){googleUiStatus(err.message)}
  };
}
document.addEventListener('DOMContentLoaded',initGoogleWorkspace,{once:true});
