/* Editable editorial dossier based on user-owned templates and explicit approvals. */
'use strict';
let editorialProfile=null;
let editorialPortrait=null;
const epNode=(tag,cls,value)=>{
  const el=document.createElement(tag);if(cls)el.className=cls;
  if(value!==undefined)el.textContent=value;return el;
};
function editorialExperienceRow(exp={},index=0){
  const row=epNode('fieldset','editorial-experience');
  row.dataset.editorialExperience='1';
  const legend=epNode('legend','', 'Experience '+(index+1));row.append(legend);
  const fields=[['Role / responsibility','title',exp.title||''],
                ['Company','company',exp.company||''],
                ['Dates','period',exp.period||'']];
  for(const [label,key,value] of fields){
    const div=epNode('div','field');
    const lab=epNode('label','','');
    const input=document.createElement('input');input.type='text';input.maxLength=140;
    input.value=value;input.dataset.field=key;
    const id='ed-'+key+'-'+index;input.id=id;lab.htmlFor=id;lab.textContent=label;
    div.append(lab,input);row.append(div);
  }
  const div=epNode('div','field');
  const lab=epNode('label','', 'Evidence-based achievements — one per line');
  const area=document.createElement('textarea');
  area.id='ed-bullets-'+index;lab.htmlFor=area.id;
  area.value=(exp.bullets||[]).join('\n');area.rows=4;area.maxLength=1100;
  area.dataset.field='bullets';div.append(lab,area);row.append(div);
  const rm=epNode('button','btn secondary editorial-remove','Remove experience');
  rm.type='button';rm.onclick=()=>{row.remove();editorialRenumber()};
  row.append(rm);return row;
}
function editorialRenumber(){
  document.querySelectorAll('[data-editorial-experience]').forEach((row,i)=>{
    row.querySelector('legend').textContent='Experience '+(i+1);
  });
}
function renderEditorialProfile(profile){
  editorialProfile=profile||null;
  editorialPortrait=profile?.portrait||null;
  for(const key of ['name','headline','city','email','linkedin']){
    const node=document.getElementById('editorial-'+key);if(node)node.value=profile?.[key]||'';
  }
  const skills=document.getElementById('editorial-skills');
  if(skills)skills.value=(profile?.skills||[]).join(', ');
  const extras=document.getElementById('editorial-extras');
  if(extras)extras.value=(profile?.extras||[]).map(x=>x.heading+' | '+x.value).join('\n');
  const approved=document.getElementById('editorial-approved');
  if(approved)approved.checked=!!profile?.approved;
  const list=document.getElementById('editorial-experiences');if(list){
    list.replaceChildren();(profile?.experiences||[]).forEach((exp,i)=>list.append(editorialExperienceRow(exp,i)));
  }
  const photo=document.getElementById('editorial-photo-preview');
  if(photo){
    photo.replaceChildren();
    if(editorialPortrait){
      const img=document.createElement('img');img.src=editorialPortrait;
      img.alt='Saved profile photo';img.className='editorial-photo';photo.append(img);
    }else photo.textContent='No portrait added';
  }
  text('editorial-status',profile?'Profile loaded. Review every claim before approval.':'Import your HTML CV or build a profile manually.');
}
async function loadEditorialProfile(){
  try{const d=await api('editorial-profile');renderEditorialProfile(d.profile||null)}
  catch(e){text('editorial-status','Cannot load profile: '+e.message)}
}
function collectEditorialProfile(){
  const val=id=>$(id).value.trim();
  const experiences=[...document.querySelectorAll('[data-editorial-experience]')].map(row=>{
    const field=k=>row.querySelector('[data-field="'+k+'"]')?.value.trim()||'';
    return {title:field('title'),company:field('company'),period:field('period'),
      bullets:field('bullets').split(/\n/).map(x=>x.trim()).filter(Boolean).slice(0,4)};
  }).filter(x=>x.title&&x.company);
  const extras=val('editorial-extras').split(/\n/).map(s=>s.split('|'))
      .filter(a=>a.length>=2&&a[0].trim()&&a.slice(1).join('|').trim())
      .map(a=>({heading:a[0].trim(),value:a.slice(1).join('|').trim()}));
  return {
    name:val('editorial-name'),headline:val('editorial-headline'),
    city:val('editorial-city'),email:val('editorial-email'),linkedin:val('editorial-linkedin'),
    skills:val('editorial-skills').split(',').map(s=>s.trim()).filter(Boolean),
    experiences,extras,portrait:editorialPortrait,
    approved:$('editorial-approved').checked
  };
}
async function loadEditorialDraft(jobId){
  const node=$('editorial-document-zone');node.classList.remove('hide');
  text('editorial-document-status','Loading your draft…');
  try{
    const d=await api('jobs/'+encodeURIComponent(jobId)+'/documents/draft');
    $('doc-interest').value=d.interest||'';$('doc-body').value=d.body||'';
    $('doc-letter-approved').checked=!!d.approved;
    text('editorial-document-status','Draft version '+d.version+'. Preview or approve before exporting.');
  }catch(err){text('editorial-document-status',err.message)}
}
function installEditorialHandlers(){
$('editorial-html-form').onsubmit=async e=>{
  e.preventDefault();
  const file=$('editorial-html').files?.[0];
  if(!file)return;
  if(file.size>1200000){text('editorial-status','HTML CV must be smaller than 1.2 MB.');return}
  const fd=new FormData();fd.append('file',file);
  text('editorial-status','Extracting your template and existing experience…');
  try{
    const r=await fetch('/web-api/editorial-profile/import-html',{
      method:'POST',credentials:'same-origin',headers:{Origin:location.origin},body:fd
    });
    const d=await r.json();if(!r.ok)throw Error(d.detail||'Import failed');
    renderEditorialProfile(d.profile);text('editorial-status','Template imported. Check dates, metrics and photo, then approve.');
  }catch(err){text('editorial-status',err.message)}
};
$('editorial-add-experience').onclick=()=>{
  const list=$('editorial-experiences'),index=list.children.length;
  if(index>=7){text('editorial-status','Maximum seven experience entries in the one-page template.');return}
  list.append(editorialExperienceRow({},index));editorialRenumber();
};
$('editorial-photo').onchange=async e=>{
  const file=e.target.files?.[0];if(!file)return;
  if(!['image/jpeg','image/png'].includes(file.type)||file.size>450000){
    text('editorial-status','Portrait must be JPEG or PNG under 450 KB.');return;
  }
  try{
    const data=await new Promise((ok,bad)=>{const r=new FileReader();r.onload=()=>ok(r.result);r.onerror=bad;r.readAsDataURL(file)});
    editorialPortrait=data;
    $('editorial-approved').checked=false;
    const preview=$('editorial-photo-preview');preview.replaceChildren();
    const img=document.createElement('img');img.className='editorial-photo';img.src=data;img.alt='New portrait';preview.append(img);
    text('editorial-status','Photo attached locally; save your profile to persist it.');
  }catch{ text('editorial-status','Could not read this image.'); }
};
$('editorial-profile-form').onsubmit=async e=>{
  e.preventDefault();
  text('editorial-status','Saving your editorial profile…');
  try{
    const result=await api('editorial-profile',{
      method:'PUT',body:JSON.stringify(collectEditorialProfile())
    });
    renderEditorialProfile(result.profile);text('editorial-status',result.profile.approved?
      'Approved profile saved. Ready for job-specific drafts.':
      'Draft profile saved. Approve it after reviewing the claims.');
  }catch(err){text('editorial-status',err.message)}
};
$('doc-save-draft').onclick=async()=>{
  if(!currentJobId)return;
  text('editorial-document-status','Saving job-specific letter…');
  try{
    const d=await api('jobs/'+encodeURIComponent(currentJobId)+'/documents/draft',{
      method:'PUT',body:JSON.stringify({
        interest:$('doc-interest').value,body:$('doc-body').value,
        approved:$('doc-letter-approved').checked
      })
    });text('editorial-document-status',d.approved?
      'Approved letter saved (v'+d.version+'). No email sent.':
      'Draft saved (v'+d.version+'). Review and approve before exporting.');
  }catch(err){text('editorial-document-status',err.message)}
};
$('doc-preview').onclick=()=>{
  if(!currentJobId)return;
  const kind=$('doc-kind').value;
  const url='/web-api/jobs/'+encodeURIComponent(currentJobId)+'/documents/preview?kind='+kind;
  window.open(url,'_blank','noopener,noreferrer');
};
$('doc-export').onclick=async()=>{
  if(!currentJobId)return;
  if(!$('doc-export-approved').checked){
    text('editorial-document-status','Approve this export before downloading.');return
  }
  const kind=$('doc-kind').value,format=$('doc-format').value;
  const button=$('doc-export');button.disabled=true;
  text('editorial-document-status','Rendering '+format.toUpperCase()+'…');
  try{
    const r=await fetch('/web-api/jobs/'+encodeURIComponent(currentJobId)+'/documents/export',{
      method:'POST',credentials:'same-origin',
      headers:{'Content-Type':'application/json',Origin:location.origin},
      body:JSON.stringify({kind,format,approved:true})
    });
    if(!r.ok){const d=await r.json().catch(()=>({}));throw Error(d.detail||'Export failed')}
    const blob=await r.blob(),url=URL.createObjectURL(blob);
    const link=document.createElement('a');
    const header=r.headers.get('Content-Disposition')||'';
    const match=/filename="([A-Za-z0-9._-]+)"/.exec(header);
    link.href=url;link.download=match?.[1]||('rolehint-'+kind+'.'+format);
    document.body.append(link);link.click();link.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1500);
    text('editorial-document-status','Downloaded '+format.toUpperCase()+' for your review. Nothing was submitted.');
  }catch(err){text('editorial-document-status',err.message)}
  finally{button.disabled=false}
};

}
document.addEventListener('DOMContentLoaded',installEditorialHandlers,{once:true});
