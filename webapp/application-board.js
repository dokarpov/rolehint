/* RoleHint application command center. Own implementation; no third-party AGPL code. */
'use strict';
let rolehintBoard = null;
const rolehintStageLabels = {
  all:'All stages',review:'To review',draft:'Drafts',handoff:'Form opened',
  awaiting_response:'Awaiting reply',interview:'Interviews',offer:'Offers',
  rejected:'Rejected',not_eligible:'Not eligible'
};
const boardText = (tag, cls, value) => {
  const node=document.createElement(tag);
  if(cls)node.className=cls;
  node.textContent=String(value??'');
  return node;
};
function rolehintBoardCsvCell(value){
  let data=String(value??'').replace(/\r|\n/g,' ');
  if(/^[\s]*[=+@-]/.test(data))data="'"+data;
  return '"'+data.replace(/"/g,'""')+'"';
}
function exportApplicationBoard(){
  if(!rolehintBoard?.items?.length){text('board-feedback','There are no tracked opportunities to export.');return}
  const headings=['Company','Role','Stage','Decision','Applied at','Location','Employer URL'];
  const lines=[headings,...rolehintBoard.items.map(item=>[
    item.company,item.title,item.stage_label,item.decision,item.submitted_at||'',item.location||'',item.source_url||''
  ])];
  const csv='\ufeff'+lines.map(row=>row.map(rolehintBoardCsvCell).join(',')).join('\r\n');
  const blob=new Blob([csv],{type:'text/csv;charset=utf-8'});
  const link=document.createElement('a');
  const url=URL.createObjectURL(blob);
  link.href=url;link.download='rolehint-application-status.csv';
  document.body.append(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
  text('board-feedback','Exported your own saved application records. No application was sent.');
}
function renderApplicationBoard(){
  if(!rolehintBoard)return;
  const stats=document.getElementById('board-metrics');
  const list=document.getElementById('board-list');
  const stageSelect=document.getElementById('board-stage-filter');
  const search=document.getElementById('board-search');
  if(!stats||!list||!stageSelect||!search)return;
  stats.replaceChildren();
  const s=rolehintBoard.summary||{};
  for(const [amount,label] of [
    [s.opportunities||0,'Tracked roles'],
    [s.confirmed_submitted||0,'Confirmed applications'],
    [s.interviews||0,'Recruiter / interview'],
    [s.offers||0,'Offers'],
  ]){
    const m=boardText('div','board-metric','');
    const n=boardText('strong','',amount);n.setAttribute('aria-label',label+': '+amount);
    m.append(n,boardText('span','',label));stats.append(m);
  }
  const current=stageSelect.value||'all';
  stageSelect.replaceChildren();
  for(const [value,label] of Object.entries(rolehintStageLabels)){
    const count=value==='all'?(s.opportunities||0):(rolehintBoard.counts?.[value]||0);
    const opt=document.createElement('option');opt.value=value;opt.textContent=label+' · '+count;stageSelect.append(opt);
  }
  stageSelect.value=rolehintStageLabels[current]?current:'all';
  const needle=search.value.trim().toLocaleLowerCase();
  const matches=(rolehintBoard.items||[]).filter(j=>
    (stageSelect.value==='all'||j.stage===stageSelect.value)
    &&(!needle||[j.company,j.title,j.location].join(' ').toLocaleLowerCase().includes(needle))
  );
  list.replaceChildren();
  if(!matches.length){
    list.append(boardText('p','board-placeholder',
      s.opportunities?'No matching applications. Change the filters to see the rest.':'No applications yet. Search real vacancies and review one to begin.'));
    text('board-feedback','Showing 0 of '+(s.opportunities||0)+' opportunities.');
    return;
  }
  const frag=document.createDocumentFragment();
  for(const item of matches){
    const row=boardText('article','board-entry','');
    const detail=boardText('div','board-entry-main','');
    detail.append(boardText('h3','board-entry-title',item.title));
    const meta=boardText('p','board-entry-meta',item.company+(item.location?' · '+item.location:''));
    const url=safeUrl(item.source_url);
    if(url){const link=boardText('a','','View original vacancy');link.href=url;link.target='_blank';link.rel='noopener noreferrer';meta.append(' · ',link)}
    detail.append(meta);
    const tags=boardText('div','board-entry-tags','');
    const stage=boardText('span','board-stage',item.stage_label);
    stage.dataset.stage=item.stage;tags.append(stage);
    if(item.submitted_at){
      const date=new Date(item.submitted_at);
      if(!Number.isNaN(date.getTime()))tags.append(boardText('span','board-tag-secondary','Applied '+new Intl.DateTimeFormat('en',{dateStyle:'medium'}).format(date)));
    }else if(item.pack_version){
      tags.append(boardText('span','board-tag-secondary','Draft v'+item.pack_version+' · not submitted'));
    }else if(item.stage==='handoff'){
      tags.append(boardText('span','board-tag-secondary','Employer form opened; submission unconfirmed'));
    }
    if(item.evidence_gaps)tags.append(boardText('span','board-tag-secondary',item.evidence_gaps+' evidence gap'+(item.evidence_gaps===1?'':'s')));
    detail.append(tags);
    const button=boardText('button','btn secondary',item.submitted_at?'Review outcome':'Review & prepare');
    button.type='button';button.addEventListener('click',()=>reviewJob(item.job_id));
    row.append(detail,button);frag.append(row);
  }
  list.append(frag);
  text('board-feedback','Showing '+matches.length+' of '+(s.opportunities||0)+' saved roles. Data is not refreshed from employers automatically.');
}
async function loadApplicationBoard(){
  const feedback=document.getElementById('board-feedback');
  if(feedback)feedback.textContent='Loading your saved application history…';
  try{
    rolehintBoard=await api('application-board');
    renderApplicationBoard();
  }catch(err){
    if(feedback)feedback.textContent='Could not load application history: '+(err?.message||'Please retry');
  }
}
document.getElementById('board-stage-filter')?.addEventListener('change',renderApplicationBoard);
document.getElementById('board-search')?.addEventListener('input',renderApplicationBoard);
document.getElementById('board-export')?.addEventListener('click',exportApplicationBoard);
