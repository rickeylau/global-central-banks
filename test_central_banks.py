import json, unittest
from datetime import date
from central_banks import ROOT, parse_html, utc, render

class TestBanks(unittest.TestCase):
    def test_ecb(self):
        html='''<dl><dt>16/12/2026</dt><dd>Governing Council of the ECB: monetary policy meeting in Frankfurt (Day 1)</dd><dt>17/12/2026</dt><dd>Governing Council of the ECB: monetary policy meeting in Frankfurt (Day 2), followed by press conference</dd><dt>24/02/2027</dt><dd>Governing Council of the ECB: non-monetary policy meeting (virtual)</dd></dl>'''
        self.assertEqual(parse_html(html,'ECB'),{date(2026,12,17)})
    def test_boj(self):
        rows=[('Jan.',21,22),('Mar.',17,18),('Apr.',27,28),('June',10,11),('July',21,22),('Sept.',21,22),('Oct.',28,29),('Dec.',16,17)]
        html='<h2>2027</h2><table><caption>Table : 2027</caption><tr><th>Date of MPM</th></tr>'+''.join(f'<tr><td>{m} {a} (Thurs.), {b} (Fri.)</td><td>-</td></tr>' for m,a,b in rows)+'</table>'
        self.assertEqual(len(parse_html(html,'BOJ')),8)
        self.assertIn(date(2027,1,22),parse_html(html,'BOJ'))
    def test_boe(self):
        rows=[(4,'February'),(18,'March'),(29,'April'),(17,'June'),(29,'July'),(16,'September'),(4,'November'),(16,'December')]
        html='<h2>2027 confirmed dates</h2><table>'+''.join(f'<tr><td>Thursday {d} {m}</td><td>MPC Summary and minutes</td></tr>' for d,m in rows)+'</table>'
        self.assertEqual(len(parse_html(html,'BOE')),8)
    def test_boc(self):
        rows=[('January',27),('March',3),('April',28),('June',2),('July',21),('September',8),('October',27),('December',8)]
        html='<h3>Schedule for 2027</h3><table>'+''.join(f'<tr><td>{m} {d}</td><td>Interest rate announcement</td></tr>' for m,d in rows)+'</table>'
        self.assertIn(date(2027,12,8),parse_html(html,'BOC'))
    def test_dst(self):
        self.assertEqual(utc(date(2027,3,18),14,15,'Europe/Berlin').hour,13)
        self.assertEqual(utc(date(2027,7,22),14,15,'Europe/Berlin').hour,12)
        self.assertEqual(utc(date(2026,12,9),9,45,'America/Toronto').hour,14)
    def test_ics(self):
        snapshot=json.loads((ROOT/'dates.json').read_text()); raw,count=render(snapshot['dates'],snapshot['stamp']); s=raw.decode()
        self.assertEqual(s.count('BEGIN:VEVENT'),count); self.assertEqual(s.count('END:VEVENT'),count)
        self.assertEqual(len({line for line in s.splitlines() if line.startswith('UID:')}),count)
        self.assertIn('DTSTART;VALUE=DATE:20261218',s); self.assertIn('DTSTART:20261217T131500Z',s)
        self.assertTrue(all(len(line)<=75 for line in raw.split(b'\r\n')))
        self.assertEqual(raw,(ROOT/'global-central-banks.ics').read_bytes())
    def test_fail_closed(self):
        with self.assertRaises(ValueError): parse_html('<html>Unavailable</html>','BOE')
if __name__=='__main__': unittest.main()
