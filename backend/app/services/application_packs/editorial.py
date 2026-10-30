"""Editorial exports for RoleHint.

Original template stylesheet re-created from the user's approved one-page two-column
CV and editorial letter layouts; no identity or photograph is shipped in the repo.
Exports contain only user-supplied/approved profile facts and explicitly approved proof.
"""
from __future__ import annotations
import base64
from datetime import datetime, timezone
from html import escape
from io import BytesIO
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

SHORT = re.compile(r"\b(a|an|the|of|to|in|on|at|by|or|as|and|for|with|from)\s+(?=\S)", re.I)
MAIL = re.compile(r"^[^@\s]{1,100}@[^@\s]{1,120}\.[^@\s]{2,30}$")
DATA = re.compile(r"^data:image/(jpeg|png);base64,([A-Za-z0-9+/=]+)$")
MAX_EXPERIENCES = 7
MAX_BULLETS = 4
CV_CSS = """
@page{size:A4;margin:0}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#fff;color:#1d2130}
body{font-family:"SF Pro Text","SF Pro Display",-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
.page{width:794px;min-height:1123px;margin:0 auto;background:#fff;padding:48px 72px 34px}
.header{display:grid;grid-template-columns:120px 1fr 208px;gap:22px;align-items:start;margin-bottom:25px}
.photo{width:108px;height:108px;object-fit:cover;object-position:center;border-radius:50%;clip-path:circle(50% at 50% 50%);display:block}
.photo-placeholder{width:108px;height:108px;border-radius:50%;background:#f2f3f7}
.name{margin:1px 0 11px;color:#353750;font-weight:700;font-size:22px;line-height:1.05;letter-spacing:.005em}
.headline{color:#050505;font-weight:700;font-size:28px;line-height:1.06;letter-spacing:-.022em;max-width:370px}
.contact{padding-top:5px;color:#48506f;font-size:13.55px;line-height:1.58}
.contact div{overflow-wrap:anywhere}
.contact a{color:#4f46ff;text-decoration:none}
.columns{display:grid;grid-template-columns:minmax(0,1fr) 208px;gap:34px;align-items:start}
.columns>aside{margin-top:-14px}
.section{margin-bottom:18px}
.section-title,.side-title{margin:0 0 14px;color:#6d7392;font-weight:700;font-size:14px;line-height:1.1;letter-spacing:.045em;text-transform:uppercase}
.job{margin-bottom:9px;break-inside:avoid}
.role{color:#1d2130;font-weight:700;font-size:14px;line-height:1.13;letter-spacing:.006em;margin-bottom:3px}
.meta{color:#1d2130;font-weight:700;font-size:11.7px;line-height:1.18;margin-bottom:4px}
.desc-list{margin:0;padding-left:18px;color:#5d6687;font-size:10.65px;line-height:1.16;text-align:justify;text-align-last:left;hyphens:auto}
.desc-list li+li{margin-top:2px}
.side-section{margin-bottom:16px}
.side-block{margin-bottom:9px}
.side-block strong{display:block;color:#1d2130;font-size:12.55px;line-height:1.1;font-weight:700;margin-bottom:3px}
.side-block span{display:block;color:#5d6687;font-size:11px;line-height:1.16}
.skills{display:flex;flex-wrap:wrap;gap:8px 14px}
.skill{color:#1d2130;font-weight:700;font-size:12.6px;line-height:1.05}
.provenance{font-size:9px;color:#6d7392;margin-top:4px}
@media print{html,body{background:#fff}.page{margin:0}}
"""
LETTER_CSS = """
@page{size:A4;margin:0}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#fff;color:#1d2130}
body{font-family:"SF Pro Text","SF Pro Display",-apple-system,BlinkMacSystemFont,"Helvetica Neue",Arial,sans-serif;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
.page{width:794px;min-height:1123px;margin:0 auto;padding:48px 72px 44px}
.letter-shell{width:100%;max-width:618px}
.kicker{margin:0 0 16px;color:#6d7392;font-size:11.8px;line-height:1.2;letter-spacing:.08em;text-transform:uppercase;font-weight:700}
.identity{margin-bottom:18px}
.date{margin:0 0 10px;color:#6d7392;font-size:11.7px;line-height:1.2;font-weight:600}
.headline{margin:0 0 12px;color:#050505;font-size:31px;line-height:1.02;letter-spacing:-.05em;font-weight:700;max-width:520px}
.contact{color:#4f5b75;font-size:12px;line-height:1.45}
.contact a{color:#4f46ff;text-decoration:none}
.rule{height:1px;margin:18px 0 24px;background:#e4e6f2}
.letter-body p{margin:0 0 12px;color:#2f374d;font-size:12.45px;line-height:1.46;text-align:justify;text-align-last:left;hyphens:auto;orphans:3;widows:3}
.letter-body .lead{margin-bottom:15px;color:#1d2130;font-size:13.1px;line-height:1.38;font-weight:600;text-align:left}
.signature{margin-top:18px;color:#1d2130!important;font-weight:700;text-align:left!important}
@media print{html,body{background:#fff}.page{margin:0}}
"""

def _plain(value, max_size=500):
    return re.sub(r"\s+"," ",str(value or "")).strip()[:max_size]

def text(value):
    return SHORT.sub(lambda m:m.group(1)+"\u00a0",escape(str(value or ""),quote=False)).replace("\n","<br>")

def _safe_link(link):
    p=urlsplit(str(link or ""))
    return link if p.scheme=="https" and p.hostname and not p.username and not p.password else None

def validate_profile(raw):
    if not isinstance(raw,dict):
        raise ValueError("Profile must be an object")
    result={
        "name":_plain(raw.get("name"),100),
        "headline":_plain(raw.get("headline"),140),
        "city":_plain(raw.get("city"),100),
        "email":_plain(raw.get("email"),254),
        "linkedin":str(_safe_link(raw.get("linkedin")) or "")[:500],
        "skills":[_plain(v,80) for v in (raw.get("skills") or [])[:18] if _plain(v,80)],
        "extras":[],
        "experiences":[],
        "portrait":None,
        "approved":raw.get("approved") is True
    }
    if result["email"] and not MAIL.fullmatch(result["email"]):
        raise ValueError("Email has an invalid format")
    for item in (raw.get("experiences") or [])[:MAX_EXPERIENCES]:
        if not isinstance(item,dict):continue
        bullets=[_plain(b,250) for b in (item.get("bullets") or [])[:MAX_BULLETS] if _plain(b,250)]
        title=_plain(item.get("title"),140)
        company=_plain(item.get("company"),100)
        if title and company:result["experiences"].append({
            "title":title,"company":company,"period":_plain(item.get("period"),80),
            "bullets":bullets
        })
    for item in (raw.get("extras") or [])[:8]:
        if isinstance(item,dict):
            heading=_plain(item.get("heading"),120)
            value=_plain(item.get("value"),250)
            if heading and value:result["extras"].append({"heading":heading,"value":value})
    photo=raw.get("portrait")
    if photo:
        m=DATA.fullmatch(str(photo))
        if not m:raise ValueError("Portrait must be a JPEG or PNG data URI")
        try:payload=base64.b64decode(m.group(2),validate=True)
        except Exception:raise ValueError("Invalid portrait encoding")
        if len(payload)>450_000 or len(payload)<30:
            raise ValueError("Portrait must be smaller than 450 KB")
        result["portrait"]=str(photo)
    return result

def from_user_cv_html(raw_html):
    """Extract the user's editorial CV markup; ignore scripts, styles and raw HTML."""
    if len(raw_html)>1_200_000:raise ValueError("HTML template is too large")
    soup=BeautifulSoup(raw_html,"html.parser")
    page=soup.select_one(".page")
    if not page or not page.select_one(".header") or not page.select_one(".columns"):
        raise ValueError("This is not a supported two-column editorial CV template")
    get=lambda selector:page.select_one(selector).get_text(" ",strip=True) if page.select_one(selector) else ""
    contact=page.select_one(".contact")
    contact_text=contact.get_text(" ",strip=True) if contact else ""
    email=next((m.group(0) for m in re.finditer(r"[^\s<>]+@[^\s<>]+",contact_text)), "")
    linkedin=next((a.get("href") for a in (contact.select("a") if contact else [])
                  if a.get("href") and "linkedin.com" in a.get("href")), "")
    city=get(".contact div") or ""
    jobs=[]
    for row in page.select("article.job")[:MAX_EXPERIENCES]:
        role=row.select_one(".role")
        meta=row.select_one(".meta")
        if not role or not meta:continue
        bullets=[x.get_text(" ",strip=True) for x in row.select(".desc-list li")][:MAX_BULLETS]
        jobs.append({"title":role.get_text(" ",strip=True),
                     "company":meta.get_text(" ",strip=True).split(" • ")[0],
                     "period":meta.select_one(".date").get_text(" ",strip=True) if meta.select_one(".date") else "",
                     "bullets":bullets})
    aside=page.select_one(".columns aside")
    skills=[x.get_text(" ",strip=True) for x in (aside.select(".skill") if aside else [])]
    extras=[]
    if aside:
        for item in aside.select(".side-block")[:8]:
            strong=item.select_one("strong")
            detail=item.select_one("span")
            if strong and detail:extras.append({"heading":strong.get_text(" ",strip=True),"value":detail.get_text(" ",strip=True)})
    pic=page.select_one("img.photo")
    photo=pic.get("src") if pic and DATA.fullmatch(pic.get("src","")) else None
    return validate_profile({
        "name":get(".name"),"headline":get(".headline"),"city":city,
        "email":email,"linkedin":linkedin,"skills":skills,"experiences":jobs,
        "extras":extras,"portrait":photo,"approved":False
    })

def _contact(profile):
    bits=[profile.get("city"),profile.get("email")]
    city_html="".join(f"<div>{text(v)}</div>" for v in bits if v)
    url=_safe_link(profile.get("linkedin"))
    if url: city_html+=f'<div><a rel="noopener" href="{escape(url,quote=True)}">LinkedIn</a></div>'
    return city_html

def cv_html(profile, job, proof_cards):
    profile=validate_profile(profile)
    selected=[x for x in (proof_cards or []) if x.get("approved") is True and x.get("verified") is True and x.get("evidence_id")]
    role_skills=profile["skills"][:12]
    rows=[]
    for item in profile["experiences"][:6]:
        bullets="".join(f"<li>{text(x)}</li>" for x in item["bullets"][:MAX_BULLETS])
        rows.append(f'<article class="job"><div class="role">{text(item["title"])}</div><div class="meta">{text(item["company"])} <span class="dot">·</span> <span class="date">{text(item["period"])}</span></div><ul class="desc-list">{bullets}</ul></article>')
    skill_html="".join(f'<span class="skill">{text(x)}</span>' for x in role_skills)
    extras="".join(f'<div class="side-block"><strong>{text(x["heading"])}</strong><span>{text(x["value"])}</span></div>' for x in profile["extras"][:6])
    # Do not hallucinate experience from the vacancy; verifiable proof is additional.
    proof_html=""
    if selected:
        proof_html='<section class="section"><h2 class="section-title">Selected evidence</h2><ul class="desc-list">'+ "".join(
            f'<li>{text(c["claim"][:220])}</li>' for c in selected[:3])+"</ul></section>"
    photo=f'<img class="photo" alt="Candidate portrait" src="{escape(profile["portrait"],quote=True)}">' if profile["portrait"] else '<div class="photo-placeholder" aria-hidden="true"></div>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{text(profile["name"])} — {text(job.get("title",""))}</title><style>{CV_CSS}</style></head><body><main class="page">
<header class="header">{photo}<div><div class="name">{text(profile["name"])}</div><div class="headline">{text(profile["headline"])}</div></div><div class="contact">{_contact(profile)}</div></header>
<div class="columns"><div><section class="section"><h2 class="section-title">Work Experience</h2>{"".join(rows)}</section>{proof_html}</div>
<aside><section class="side-section"><h2 class="side-title">Core skills</h2><div class="skills">{skill_html}</div></section><section class="side-section"><h2 class="side-title">Selected expertise</h2>{extras}</section></aside></div></main></body></html>'''

def letter_html(profile, job, approved_proof, interest, body=None):
    profile=validate_profile(profile)
    company=_plain(job.get("company"),120)
    title=_plain(job.get("title"),120)
    interest=_plain(interest,650)
    verified=[c for c in approved_proof or [] if c.get("verified") is True and c.get("approved") is True and c.get("evidence_id")]
    intro=body if body else interest
    paragraphs=[p.strip() for p in re.split(r"\n\s*\n",str(intro or "")) if p.strip()]
    if not paragraphs:
        paragraphs=[f"I am interested in the {title} role at {company}."]
    if not body and verified:
        paragraphs += ["My relevant, documented work includes "+ "; ".join(x["claim"].strip().rstrip(".") for x in verified[:2])+"."]
        paragraphs += ["I'd be interested in exploring the problems the team wants this hire to solve."]
    paragraphs=paragraphs[:6]
    contents="".join(f'<p class="{("lead" if i==0 else "")}">{text(p[:1800])}</p>' for i,p in enumerate(paragraphs))
    date=datetime.now(timezone.utc).strftime("%d %B %Y")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Cover letter — {text(company)}</title><style>{LETTER_CSS}</style></head><body><main class="page"><section class="letter-shell">
<p class="kicker">Cover Letter</p><div class="identity"><p class="date">{text(date)}</p><h1 class="headline">{text(title)} · {text(company)}</h1><div class="contact">{text(profile.get("city"))} · {text(profile.get("email"))}</div></div><div class="rule"></div>
<div class="letter-body"><p>Dear {text(company)} team,</p>{contents}<p class="signature">{text(profile.get("name"))}</p></div>
</section></main></body></html>'''

def pdf_from_html(html):
    try:
        from weasyprint import HTML
        from pypdf import PdfReader
    except ImportError as ex:raise RuntimeError("PDF renderer not available") from ex
    raw=HTML(string=html).write_pdf()
    if len(PdfReader(BytesIO(raw)).pages)!=1:
        raise ValueError("Document exceeds one A4 page. Shorten text before exporting.")
    return raw

def docx_from_html_data(profile,job,kind,proof,interest,body):
    from docx import Document
    from docx.shared import Cm,Pt,RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    profile=validate_profile(profile)
    doc=Document()
    sec=doc.sections[0]
    sec.top_margin=Cm(1.2);sec.bottom_margin=Cm(1.1)
    sec.left_margin=Cm(1.85);sec.right_margin=Cm(1.85)
    sec.page_height=Cm(29.7);sec.page_width=Cm(21)
    normal=doc.styles['Normal'];normal.font.name='Arial';normal.font.size=Pt(9)
    normal.font.color.rgb=RGBColor(45,55,77)
    if kind=="cv":
        p=doc.add_paragraph();p.style='Title';p.add_run(profile['name'])
        h=doc.add_paragraph();h.add_run(profile['headline']).bold=True
        doc.add_paragraph(" · ".join(x for x in [profile['city'],profile['email']] if x))
        doc.add_heading('Work Experience',level=2)
        for exp in profile['experiences'][:6]:
            p=doc.add_paragraph();r=p.add_run(exp['title']);r.bold=True
            doc.add_paragraph(exp['company']+" · "+exp['period'])
            for bullet in exp['bullets'][:MAX_BULLETS]:
                doc.add_paragraph(bullet,style='List Bullet')
        verified=[c for c in proof or [] if c.get('verified') and c.get('approved') and c.get('evidence_id')]
        if verified:
            doc.add_heading('Selected Evidence',level=2)
            for e in verified[:3]:doc.add_paragraph(e['claim'],style='List Bullet')
        if profile['skills']:
            doc.add_heading('Core Skills',level=2);doc.add_paragraph(' · '.join(profile['skills'][:12]))
    else:
        doc.add_paragraph('COVER LETTER')
        doc.add_heading(f"{job.get('title','')} · {job.get('company','')}",level=1)
        doc.add_paragraph(profile['city']+' · '+profile['email'])
        doc.add_paragraph('Dear '+str(job.get('company') or 'Hiring')+' team,')
        for p in re.split(r"\n\s*\n",body or interest or ''):
            if p.strip():doc.add_paragraph(p.strip())
        doc.add_paragraph(profile['name'])
    out=BytesIO();doc.save(out);return out.getvalue()
