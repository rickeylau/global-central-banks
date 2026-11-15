#!/usr/bin/env python3
"""Official central bank decision calendars, no trading or broker access."""
import argparse, json, re, calendar
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT/'dates.json'
OUTPUT = ROOT/'global-central-banks.ics'
SOURCES = {
    'BOJ': 'https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm',
    'ECB': 'https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html',
    'BOE': 'https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates',
    'BOC': 'https://www.bankofcanada.ca/core-functions/monetary-policy/key-interest-rate/',
}
TIME_SOURCES = {
    'ECB': 'https://www.ecb.europa.eu/press/govcdec/mopo/html/index.en.html',
    'BOE': 'https://www.bankofengland.co.uk/monetary-policy',
    'BOC': 'https://www.bankofcanada.ca/2026/07/bank-canada-publishes-2027-schedule-policy-interest-rate-announcements-other-major-publications/',
    'BOJ': SOURCES['BOJ'],
}
MONTHS = {s.lower().rstrip('.'):i for i in range(1,13) for s in (calendar.month_name[i],calendar.month_abbr[i])}
MONTHS['sept']=9
MONTH_PATTERN = '|'.join(sorted(MONTHS,key=len,reverse=True))

def clean(s): return ' '.join(s.split())

def monthnum(s): return MONTHS[s.lower().rstrip('.')]

def cell_text(cell): return clean(cell.get_text(' ',strip=True))

def year_of_table(table, pattern):
    caption=table.find('caption')
    if caption:
        m=re.search(pattern, cell_text(caption), re.I)
        if m: return int(m[1])
    # Some sites use a heading; others use a plain paragraph immediately before the table.
    for tag in table.find_all_previous(['h1','h2','h3','h4','h5','h6','p','strong','caption'],limit=40):
        if tag.find_parent('table') is not None: continue
        m=re.search(pattern,cell_text(tag),re.I)
        if m: return int(m[1])
    return None

def table_rows(table):
    return [[cell_text(c) for c in tr.find_all(['td','th'],recursive=False)] for tr in table.find_all('tr')]

def parse_ecb(soup):
    text=clean(soup.get_text(' ',strip=True))
    # Each date precedes its event description. Only Day 2 / press conference.
    matches=list(re.finditer(r'\b(\d{2}/\d{2}/20\d{2})\b',text))
    result=set()
    for i,m in enumerate(matches):
        desc=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)]
        if re.search(r'Governing Council of the ECB:\s*monetary policy meeting\b.{0,180}?\(Day 2\)',desc,re.I):
            result.add(datetime.strptime(m[1],'%d/%m/%Y').date())
    return result

def parse_tables(soup,bank):
    result=set(); found_years=set()
    patterns={'BOJ':r'^(?:Table\s*:\s*)?(20\d{2})$', 'BOE':r'\b(20\d{2})\s+confirmed dates\b','BOC':r'\bSchedule for (20\d{2})\b'}
    for table in soup.find_all('table'):
        rows=table_rows(table)
        full=' '.join(' '.join(r) for r in rows)
        if bank=='BOJ' and not re.search(r'Date of MPM',full,re.I): continue
        if bank=='BOE' and not re.search(r'MPC Summary and minutes',full,re.I): continue
        if bank=='BOC' and not re.search(r'Interest rate announcement',full,re.I): continue
        year=year_of_table(table,patterns[bank])
        if not year: continue
        dates=set()
        for r in rows:
            if not r: continue
            t=r[0]
            if bank=='BOJ':
                m=re.match(rf'^({MONTH_PATTERN})\.?\s+(\d{{1,2}})\s*\([^)]+\)\s*[,–-]\s*(?:({MONTH_PATTERN})\.?\s+)?(\d{{1,2}})\s*\(',t,re.I)
                if m:
                    mon=monthnum(m[3] or m[1]); dates.add(date(year,mon,int(m[4])))
                elif re.match(rf'^({MONTH_PATTERN})\.?\s+\d',t,re.I): raise ValueError('Unrecognized BOJ meeting: '+t)
            elif bank=='BOE':
                m=re.match(rf'^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{{1,2}})\s+({MONTH_PATTERN})\b',t,re.I)
                if m: dates.add(date(year,monthnum(m[2]),int(m[1])))
            else:
                m=re.match(rf'^({MONTH_PATTERN})\.?\s+(\d{{1,2}})\b',t,re.I)
                if m and 'interest rate announcement' in ' '.join(r[1:]).lower(): dates.add(date(year,monthnum(m[1]),int(m[2])))
        if not dates: continue
        if not 7<=len(dates)<=12: raise ValueError(f'{bank} {year}: unexpected number of meetings {len(dates)}')
        if year in found_years: raise ValueError(f'{bank}: duplicate schedule {year}')
        found_years.add(year); result.update(dates)
    return result

def parse_html(html,bank):
    soup=BeautifulSoup(html,'html.parser')
    for tag in soup(['script','style','noscript']): tag.decompose()
    result=parse_ecb(soup) if bank=='ECB' else parse_tables(soup,bank)
    if not result: raise ValueError(f'{bank}: no dates found')
    return result

def refresh(old,today):
    fresh={}
    for bank,url in SOURCES.items():
        req=Request(url,headers={'User-Agent':'Mozilla/5.0 (Central Bank Calendar)','Accept':'text/html'})
        with urlopen(req,timeout=40) as res: html=res.read(8_000_000)
        parsed=parse_html(html,bank)
        previous={date.fromisoformat(x) for x in old['dates'][bank]}
        future={d for d in parsed if d>=today}
        oldfuture={d for d in previous if d>=today}
        if not future or max(future)<today+timedelta(days=30): raise ValueError(f'{bank}: future coverage missing')
        # Fail closed if a source suddenly loses large parts of its schedule.
        for y in {d.year for d in oldfuture}:
            n=sum(d.year==y for d in oldfuture); f=sum(d.year==y for d in future)
            if f<max(1,n-1): raise ValueError(f'{bank} {y}: schedule unexpectedly shrank {n} -> {f}')
        fresh[bank]=sorted(d.isoformat() for d in future | {d for d in previous if d<today})
        print(bank,len(fresh[bank]),'decision dates')
    return fresh

def esc(s): return s.replace('\\','\\\\').replace('\n','\\n').replace(';','\\;').replace(',','\\,')
def fold(line):
    out=[]; part=''
    for ch in line:
        if len((part+ch).encode('utf-8'))>75: out.append(part); part=' '+ch
        else: part+=ch
    out.append(part); return '\r\n'.join(out)
def utc(d,h,m,zone): return datetime.combine(d,time(h,m),ZoneInfo(zone)).astimezone(timezone.utc)
def fmt(dt): return dt.strftime('%Y%m%dT%H%M%SZ')

def render(data,stamp):
    lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Global Central Banks//EN','CALSCALE:GREGORIAN','X-WR-CALNAME:Global Central Banks','X-WR-TIMEZONE:America/New_York','X-WR-CALDESC:Official BOJ ECB BOE BOC policy schedules. No Fed events.']
    count=0
    for bank,values in sorted(data.items()):
        for value in sorted(set(values)):
            d=date.fromisoformat(value)
            specs={'BOJ':[('decision','BOJ Rate Decision (Japan date - time TBD)',None)],'ECB':[('decision','ECB Rate Decision',(14,15,'Europe/Berlin')),('press','ECB Press Conference',(14,45,'Europe/Berlin'))],'BOE':[('decision','BOE Rate Decision & Minutes',(12,0,'Europe/London'))],'BOC':[('decision','BOC Rate Decision',(9,45,'America/Toronto'))]}[bank]
            for kind,title,clock in specs:
                if clock:
                    start=utc(d,*clock); end=start+timedelta(minutes=15)
                    fields=['DTSTART:'+fmt(start),'DTEND:'+fmt(end)]
                    note='Scheduled standard local release time; 15-minute display block, not actual duration.'
                else:
                    fields=[f'DTSTART;VALUE=DATE:{d:%Y%m%d}',f'DTEND;VALUE=DATE:{d+timedelta(days=1):%Y%m%d}']
                    note='Meeting end date in Japan. No fixed release time. In New York, the decision may arrive the previous evening or overnight.'
                desc=note+'\nOfficial schedule: '+SOURCES[bank]+'\nTiming: '+TIME_SOURCES[bank]+'\nVerify official updates before trading.'
                lines+=['BEGIN:VEVENT',f'UID:{bank.lower()}-{kind}-{value}@global-central-banks',f'DTSTAMP:{stamp}',*fields,'SUMMARY:'+esc(title),'DESCRIPTION:'+esc(desc),'URL:'+SOURCES[bank],'TRANSP:TRANSPARENT','END:VEVENT']; count+=1
    lines+=['END:VCALENDAR']
    return ('\r\n'.join(fold(x) for x in lines)+'\r\n').encode(),count

def main():
    p=argparse.ArgumentParser(); p.add_argument('--offline',action='store_true'); args=p.parse_args()
    old=json.loads(SNAPSHOT.read_text()); today=datetime.now(ZoneInfo('America/New_York')).date()
    dates=old['dates'] if args.offline else refresh(old,today)
    stamp=old['stamp'] if dates==old['dates'] else fmt(datetime.now(timezone.utc))
    data,count=render(dates,stamp)
    for path,content in [(SNAPSHOT,(json.dumps({'stamp':stamp,'dates':dates},indent=2)+'\n').encode()),(OUTPUT,data)]:
        if not path.exists() or path.read_bytes()!=content:
            tmp=path.with_suffix('.tmp'); tmp.write_bytes(content); tmp.replace(path)
    print(f'{count} events published to {OUTPUT.name}')
if __name__=='__main__': main()
