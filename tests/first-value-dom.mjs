import {JSDOM} from 'jsdom';
import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
const cv='Product Manager with customer research, roadmap ownership and analytics experience. Led discovery for a software team.';
const searches=[];
const dom=new JSDOM(readFileSync('webapp/index.html','utf8'),{url:'https://rolehint.example/webapp/',runScripts:'dangerously',beforeParse(w){
 w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=()=>{};
 w.fetch=async(url,opt={})=>{
  let status=200,body={};
  if(url.endsWith('/me')){status=401;body={detail:'Please sign in'}}
  if(url.endsWith('auth-status'))body={telegram_login_available:true};
  if(url.endsWith('anonymous/cv-analysis'))body={text:cv,evidence:[{evidence:cv}],insights:[],suggested_roles:['Product Manager']};
  if(url.endsWith('anonymous/matches')){searches.push(JSON.parse(opt.body));body={jobs:[{title:'Product Manager',company:'QA ONLY',location:'Remote',url:'https://example.com/qa',fit:{label:'Some CV evidence',matched_terms:['research'],unconfirmed_terms:['sql'],note:'Text signals'}}]}}
  return {ok:status===200,status,json:async()=>body};
 };
}});
dom.window.eval(readFileSync('webapp/application-draft.js','utf8'));
const w=dom.window,d=w.document,$=id=>d.getElementById(id);
const tick=()=>new Promise(r=>setTimeout(r,5));await tick();
Object.defineProperty($('cv-input'),'files',{configurable:true,value:[new w.File([cv],'cv.txt')]});
await $('cv-input').onchange({target:$('cv-input')});
assert.equal($('anon-cv-text')?.value,cv,'extracted CV must be editable before matching');
$('anon-cv-text').value=cv+' SQL reporting.';$('anon-cv-text').dispatchEvent(new w.Event('input'));
await $('role-first').onsubmit({preventDefault(){}});await tick();
assert(searches.at(-1).cv_terms.includes('SQL reporting'));
assert(d.querySelector('.match-badge'));assert(d.querySelector('.gap-badge'));
d.querySelector('.prepare-application').click();
assert.equal($('draft-cv').value,cv+' SQL reporting.');
$('draft-motivation').value='I want to improve access to education.';
$('draft-gap-context').value='I am learning SQL; I have not used it professionally.';
$('draft-build-letter').click();
assert($('draft-letter').value.includes('improve access to education'));
assert($('draft-letter').value.includes('not used it professionally'));
Object.defineProperty($('cv-input'),'files',{configurable:true,value:[new w.File(['bad'],'bad.jpg')]});
await $('cv-input').onchange({target:$('cv-input')});
await $('role-first').onsubmit({preventDefault(){}});await tick();
assert.equal(searches.at(-1).cv_terms,'','failed CV replacement must clear old matching context');
assert.equal($('anon-cv-text').value,'');
console.log('PASS DOM: CV correction → match/gap badges → per-vacancy drafts → motivation/gaps → stale context cleanup');
w.close();
