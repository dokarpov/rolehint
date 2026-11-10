/* Candidate-controlled, tab-local application preparation. No external writes or generated claims. */
const applicationDrafts=new Map();
let activeDraftJob=null;
function clearCandidateDraft(){
  cvContext='';currentCV=null;lastJobs=[];applicationDrafts.clear();activeDraftJob=null;
  $('anon-cv-text').value='';
  for(const id of ['draft-cv','draft-motivation','draft-gap-context','draft-letter'])$(id).value='';
  $('draft-approve').checked=false;
  $('jobs-list').replaceChildren();
  $('draft-screen').classList.add('hide');
}
function appendFitBadges(target,fit){
  for(const [kind,terms] of [['match',fit.matched_terms||[]],['gap',fit.unconfirmed_terms||[]]]){
    for(const term of terms){const b=document.createElement('span');b.className=kind+'-badge';b.textContent=(kind==='match'?'CV signal: ':'Gap to review: ')+term;target.append(b)}
  }
}
$('anon-cv-text').addEventListener('input',()=>{
  cvContext=$('anon-cv-text').value.slice(0,2500);
  currentCV=new File([$('anon-cv-text').value],'reviewed-cv.txt',{type:'text/plain'});
  // A revised source invalidates old job-specific versions and search results.
  applicationDrafts.clear();lastJobs=[];$('jobs-list').replaceChildren();
});
function openApplicationDraft(job){
  activeDraftJob=job;const saved=applicationDrafts.get(job.url);
  text('draft-heading',job.title+' · '+job.company);
  text('draft-source','Vacancy source: '+job.url+' · eligibility and open status need checking');
  $('draft-signals').replaceChildren();appendFitBadges($('draft-signals'),job.fit);
  $('draft-cv').value=saved?.cv??$('anon-cv-text').value;
  $('draft-motivation').value=saved?.motivation||'';$('draft-gap-context').value=saved?.gaps||'';
  $('draft-letter').value=saved?.letter||'';$('draft-approve').checked=false;
  text('draft-message','');showStep('draft-screen');
}
function rememberDraft(){
  if(activeDraftJob)applicationDrafts.set(activeDraftJob.url,{cv:$('draft-cv').value,motivation:$('draft-motivation').value,gaps:$('draft-gap-context').value,letter:$('draft-letter').value});
}
for(const id of ['draft-cv','draft-motivation','draft-gap-context','draft-letter'])$(id).addEventListener('input',()=>{$('draft-approve').checked=false;rememberDraft()});
$('draft-build-letter').onclick=()=>{
  if(!activeDraftJob)return;
  const motivation=$('draft-motivation').value.trim(),gaps=$('draft-gap-context').value.trim();
  if(!motivation){text('draft-message','Add your motivation first so the letter reflects your reasons.');return}
  const parts=['Dear '+activeDraftJob.company+' hiring team,','I am applying for the '+activeDraftJob.title+' role.',motivation];
  if(gaps)parts.push(gaps);
  parts.push('My attached CV describes the experience I would bring. I would welcome a conversation about the role and your priorities.');
  $('draft-letter').value=parts.join('\n\n');$('draft-approve').checked=false;rememberDraft();
  text('draft-message','A starter letter was built from your notes. Edit it for specificity and check it against the vacancy.');
};
function approvedDraft(){
  if(!$('draft-approve').checked){text('draft-message','Review and approve the documents first.');return false}
  return true;
}
function downloadDraft(id,suffix){
  if(!approvedDraft())return;const content=$(id).value.trim();
  if(!content){text('draft-message','Add and review the document text first.');return}
  const blob=new Blob([content],{type:'text/plain;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download='rolehint-'+suffix+'.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  text('draft-message','TXT downloaded. Nothing was submitted to an employer.');
}
$('draft-download-cv').onclick=()=>downloadDraft('draft-cv','cv');
$('draft-download-letter').onclick=()=>downloadDraft('draft-letter','cover-letter');
$('draft-open-employer').onclick=()=>{if(!approvedDraft())return;const url=safeUrl(activeDraftJob?.url);if(!url){text('draft-message','Employer URL unavailable.');return}window.open(url,'_blank','noopener,noreferrer');text('draft-message','Employer page opened. This is a handoff, not a submitted application.')};
$('draft-back').onclick=()=>{rememberDraft();showStep('jobs-screen')};
