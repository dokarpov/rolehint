from fastapi.testclient import TestClient
from app.main import app

def test_anonymous_cv_returns_reviewable_text_without_saving(monkeypatch):
    base='https://rolehint.example'
    monkeypatch.setenv('CFA_WEB_APP_URL',base)
    text='Product Manager\n\nLed research and roadmap discovery for a small software team. Improved onboarding with analytics.'
    with TestClient(app,base_url=base) as client:
        r=client.post('/web-api/anonymous/cv-analysis',headers={'Origin':base},files={'file':('cv.txt',text.encode(),'text/plain')})
        assert r.status_code==200
        assert r.json()['text']==text
        assert r.json()['saved'] is False
        assert r.headers['cache-control']=='no-store'
        assert client.get('/web-api/cv').status_code==401
