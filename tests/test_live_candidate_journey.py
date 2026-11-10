"""Opt-in local real-backend journey; local mailbox capture, real ATS. NOT production OTP proof."""
import os,uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app,product
from app import web_identity

@pytest.mark.skipif(os.getenv('ROLEHINT_LIVE_JOURNEY')!='1',reason='Opt-in live ATS network journey')
def test_candidate_journey_with_live_ats(monkeypatch):
    base='https://rolehint.example'
    monkeypatch.setenv('CFA_WEB_APP_URL',base)
    monkeypatch.setenv('CFA_SMTP_HOST','local-test-mailbox')
    monkeypatch.setenv('CFA_MAIL_FROM','qa@example.invalid')
    out=[]
    monkeypatch.setattr(web_identity,'send_email',lambda email,url,*args:out.append(url))
    # These employer boards are existing real-source test inputs, not invented vacancies.
    from app import web_release
    from app.services.job_search import JobSearchService
    import asyncio
    found=asyncio.run(JobSearchService(ashby_boards=['openai','elevenlabs','ashby']).search('Product Manager',sources=['ashby']))
    assert found,'Real ATS returned no jobs; do not fabricate a fallback'
    chosen=next(j for j in found if len(j.get('description',''))>=120)
    cv='QA Candidate — synthetic account, not an applicant\n\nProduct Manager with experience in roadmap strategy, customer research and analytics. Led discovery for a software team.\n\nOwned stakeholder communication, experiment design and onboarding improvements. No unverified numerical claims.'
    email='qa-'+uuid.uuid4().hex+'@example.invalid'
    with TestClient(app,base_url=base) as c:
        preview=c.post('/web-api/anonymous/cv-analysis',headers={'Origin':base},files={'file':('qa-cv.txt',cv.encode(),'text/plain')})
        assert preview.status_code==200,preview.text
        assert c.post('/web-api/login',headers={'Origin':base},json={'email':email}).status_code==200
        assert c.get(out[-1],follow_redirects=False).status_code==303
        assert c.get('/web-api/me').status_code==200
        assert c.post('/web-api/cv',headers={'Origin':base},files={'file':('qa-cv.txt',cv.encode(),'text/plain')}).status_code==200
        correction=cv+'\n\nCollaboration: co-owned delivery with engineering.'
        assert c.put('/web-api/cv',headers={'Origin':base},json={'text':correction}).status_code==200
        assert c.post('/web-api/cv/confirm',headers={'Origin':base}).status_code==200
        # Persist an actual retrieved employer vacancy; this tests review onwards, not discovery delivery.
        uid=product.conn.execute('SELECT user_id FROM web_accounts WHERE email=?',(email,)).fetchone()['user_id']
        jid=product.upsert_user_job(uid,chosen)['job_id']
        root='/web-api/jobs/'+jid
        review=c.get(root+'/review');assert review.status_code==200,review.text
        pack=c.get(root+'/pack');assert pack.status_code==200
        data=pack.json()['data'];data['recruiter_note']='I am interested in this role because it connects customer research with product decisions. My background is described in the attached CV; any unconfirmed requirements need discussion.'
        assert c.put(root+'/pack',headers={'Origin':base},json=data).status_code==200
        export=c.get(root+'/export');assert export.status_code==200
        assert data['recruiter_note'] in export.text
        handoff=c.post(root+'/handoff',headers={'Origin':base});assert handoff.status_code==200
        assert handoff.json()['submitted'] is False
        assert c.get('/web-api/release-state').json()['application_history']==[]
        assert c.post('/web-api/logout',headers={'Origin':base},follow_redirects=False).status_code==303
        assert c.get('/web-api/cv').status_code==401
        assert c.post('/web-api/login',headers={'Origin':base},json={'email':email}).status_code==200
        assert c.get(out[-1],follow_redirects=False).status_code==303
        assert c.get('/web-api/cv').json()['text']==correction
        assert c.get(root+'/pack').json()['data']['recruiter_note']==data['recruiter_note']
        print('LIVE ATS job:',chosen['title'],chosen['company'],chosen['source_url'])
        print('PASS local account/CV corrections/review/pack/export/handoff/logout/resume; no employer submission')
