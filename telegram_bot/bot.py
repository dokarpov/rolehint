from __future__ import annotations
import asyncio, html, os, httpx

TOKEN=os.environ["TELEGRAM_BOT_TOKEN"]
APP_URL=os.environ["TELEGRAM_MINI_APP_URL"].rstrip("/") + "/"
CAREER_API=os.environ.get("CAREER_FIT_API_URL","http://localhost:8000").rstrip("/")
BOT_SECRET=os.environ.get("CFA_INTERNAL_BOT_SECRET","")
STARS=int(os.environ.get("CFA_MANAGED_CYCLE_STARS","2499"))
GITHUB_URL=os.environ.get("CFA_GITHUB_URL","https://github.com/dokarpov/career-fit-agent")
API=f"https://api.telegram.org/bot{TOKEN}"
OFFSET=0

async def tg(method,payload=None):
    async with httpx.AsyncClient(timeout=35) as c:
        r=await c.post(f"{API}/{method}",json=payload or {});r.raise_for_status();d=r.json()
        if not d.get("ok"):raise RuntimeError(d)
        return d["result"]

async def backend(method,path,json=None):
    async with httpx.AsyncClient(timeout=25) as c:
        r=await c.request(method,CAREER_API+path,json=json,headers={"X-CFA-Bot-Secret":BOT_SECRET});r.raise_for_status();return r.json()

def web_button(text="Open RoleHint",open_id=None):
    url=APP_URL+(('?open='+open_id) if open_id else '')
    return {"inline_keyboard":[[{"text":text,"web_app":{"url":url}}]]}

async def send(chat_id,text,markup=None):
    p={"chat_id":chat_id,"text":text,"parse_mode":"HTML","disable_web_page_preview":True}
    if markup:p["reply_markup"]=markup
    return await tg("sendMessage",p)

async def summary(tg_id):return await backend("GET",f"/internal/telegram/{tg_id}/summary")

def link_job(j,label=None):
    label=html.escape(label or f"{j['company']} · {j['title']}")
    url=j.get("source_url")
    return f'<a href="{html.escape(url,quote=True)}">{label}</a>' if url else label

async def start(msg):
    cid=msg["chat"]["id"];u=msg.get("from") or {}
    command=(msg.get("text") or "").strip().split(maxsplit=1)
    if len(command)==2 and command[1].startswith("web_"):
        try:
            result=await backend("POST","/web-api/telegram/bot-issue",{"state":command[1][4:],"telegram_user":{"id":u["id"],"first_name":u.get("first_name",""),"username":u.get("username","")}})
            return await send(cid,"<b>RoleHint web sign-in</b>\n\nEnter this one-time code in the web page: <code>"+html.escape(result["code"])+"</code>\n\nExpires in 10 minutes. Never share this code.")
        except Exception:
            return await send(cid,"This web sign-in link has expired or is invalid. Start a new sign-in from the RoleHint website.")
    data=await summary(u["id"])
    ap=data.get("autopilot") or {};profiles=ap.get("search_profiles") or []
    if profiles:
        status="I’m already searching automatically: "+", ".join(x["query"] for x in profiles[:3])+"."
    else:
        status="Set your search preferences in the Mini App. Your workspace is ready to explore; automated job discovery requires a connected source."
    await send(cid,f"<b>RoleHint</b>{', '+html.escape(u.get('first_name','')) if u.get('first_name') else ''}\n\n{html.escape(status)}\n\nOpen your workspace to review opportunities and next steps. Automated alerts are not enabled until your search is configured.",web_button("Open RoleHint"))

async def today(msg):
    cid=msg["chat"]["id"];u=msg.get("from") or {};data=await summary(u["id"]);plan=data.get("funnel") or {};batch=plan.get("today_batch") or []
    if not batch:
        remaining=sum((plan.get("remaining") or {}).values())
        text=f"<b>No application batch is ready yet.</b>\n\nI’m still searching against the weekly funnel. Remaining capacity: {remaining}."
        return await send(cid,text,web_button("Open search cockpit"))
    lines=[f"<b>Today’s application batch · {len(batch)} roles · ~{plan.get('today_minutes',0)} min</b>",""]
    for i,j in enumerate(batch,1):
        tier=((j.get("payload") or {}).get("funnel") or {}).get("tier") or ""
        lines.append(f"{i}. <b>{tier}</b> · {link_job(j)}")
    done=sum((plan.get("completed") or {}).values());fc=plan.get("conversion_forecast") or {}
    lines += ["",f"Weekly progress: <b>{done}/{plan.get('target_total',23)}</b> unique applications.",
      f"Estimated screening conversion: <b>{fc.get('estimated_rate_low_percent','—')}–{fc.get('estimated_rate_high_percent','—')}%</b> · ~{fc.get('expected_screenings_low','—')}–{fc.get('expected_screenings_high','—')} screening/week."]
    first=batch[0] if batch else None
    await send(cid,"\n".join(lines),web_button("Review batch",first.get("job_id") if first else None))

async def jobs_cmd(msg):
    cid=msg["chat"]["id"];u=msg.get("from") or {};data=await summary(u["id"]);plan=data.get("funnel") or {};queue=plan.get("queue") or []
    lines=["<b>Weekly application queue</b>",""]
    for j in queue[:25]:
        tier=((j.get("payload") or {}).get("funnel") or {}).get("tier") or ""
        mins=((j.get("payload") or {}).get("funnel") or {}).get("estimated_minutes")
        lines.append(f"• <b>{tier}</b> · {link_job(j)}"+(f" · ~{mins}m" if mins else ""))
    if not queue:lines.append("I’m still discovering roles. No duplicate or blocked vacancy is added just to fill the quota.")
    q=plan.get("quotas") or {};fc=plan.get("conversion_forecast") or {};pol=plan.get("policy") or {}
    lines += ["",f"Target mix: P0/P1 {q.get('P01',6)} · P2 {q.get('P2',10)} · low-cost {q.get('LOW_COST',7)}",
      f"Strategy: {html.escape(str(pol.get('pace_preset','balanced')))} · {html.escape(str(pol.get('breadth','standard')))} reach",
      f"Estimated conversion: {fc.get('estimated_rate_low_percent','—')}–{fc.get('estimated_rate_high_percent','—')}%"]
    await send(cid,"\n".join(lines),web_button("Open funnel"))

async def profile_cmd(msg):
    cid=msg["chat"]["id"];u=msg.get("from") or {};data=await summary(u["id"]);p=data["profile"];ap=data.get("autopilot") or {}
    profiles=ap.get("search_profiles") or []
    target=" / ".join(x["query"] for x in profiles[:3]) or p.get("target")
    await send(cid,f"<b>Search profile</b>\n\nTarget: {html.escape(str(target))}\nEvidence: {html.escape(str(p.get('evidence_health')))}\nSearch mode: {html.escape(str(ap.get('mode','learning')))}",web_button("Open profile"))

async def upgrade(msg):
    await tg("sendInvoice",{"chat_id":msg["chat"]["id"],"title":"Career Fit — Managed Search Cycle","description":"Hosted discovery, matching, evidence rebuild, email tracking and Telegram application batches for one search cycle.","payload":"managed_search_cycle_v1","currency":"XTR","prices":[{"label":"Managed Search Cycle","amount":STARS}]})

async def handle(update):
    if update.get("pre_checkout_query"):
        return await tg("answerPreCheckoutQuery",{"pre_checkout_query_id":update["pre_checkout_query"]["id"],"ok":True})
    msg=update.get("message") or {}
    if not msg:return
    if msg.get("successful_payment"):
        p=msg["successful_payment"];u=msg.get("from") or {}
        await backend("POST","/billing/telegram-stars/confirm",{"telegram_user_id":u["id"],"first_name":u.get("first_name",""),"telegram_payment_charge_id":p["telegram_payment_charge_id"],"total_amount":p["total_amount"],"currency":p["currency"],"invoice_payload":p["invoice_payload"]})
        return await send(msg["chat"]["id"],"<b>Managed Search Cycle activated.</b>\n\nDiscovery, scheduled matching, connector sync and Telegram batches are enabled.",web_button("Open Career Fit"))
    chat=msg.get("chat") or {}
    if chat.get("type")!="private":return
    text=(msg.get("text") or "").strip()
    if text.startswith("/start"):return await start(msg)
    if text.startswith("/today"):return await today(msg)
    if text.startswith("/jobs"):return await jobs_cmd(msg)
    if text.startswith("/profile"):return await profile_cmd(msg)
    if text.startswith("/upgrade"):return await upgrade(msg)
    if text.startswith("/selfhost"):return await send(chat["id"],f"<b>Free self-hosted edition</b>\n\nUse your own compute, keys and storage. Autopilot logic is the same core.\n\n{GITHUB_URL}")
    if text.startswith("/paysupport"):return await send(chat["id"],"For payment issues, send the Telegram payment receipt / charge ID in this chat.")
    if text:return await send(chat["id"],"You don’t need to send me vacancy links. I search, deduplicate and match them automatically. Use /today for the current five-role batch or /jobs for the weekly queue.",web_button())

async def configure():
    await tg("setMyCommands",{"commands":[
      {"command":"today","description":"Get today’s application batch"},
      {"command":"jobs","description":"Open weekly application queue"},
      {"command":"profile","description":"See inferred search profile"},
      {"command":"upgrade","description":"Activate managed search cycle"},
      {"command":"selfhost","description":"Free self-hosted edition"},
      {"command":"paysupport","description":"Payment support"}
    ]})
    await tg("setChatMenuButton",{"menu_button":{"type":"web_app","text":"Open RoleHint","web_app":{"url":APP_URL}}})

async def poll():
    global OFFSET
    await configure()
    while True:
        try:
            updates=await tg("getUpdates",{"offset":OFFSET,"timeout":30,"allowed_updates":["message","pre_checkout_query"]})
            for u in updates:OFFSET=max(OFFSET,u["update_id"]+1);await handle(u)
        except Exception as e:print("poll error",repr(e));await asyncio.sleep(2)

if __name__=="__main__":asyncio.run(poll())
