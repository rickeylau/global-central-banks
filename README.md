# Global Central Banks Calendar

适用于 SPX 交易准备的海外央行日历。BOJ、ECB、BOE、BOC；不包含 Fed。

- BOJ：日本会议最后一天，全天标记（日本日期），无固定利率决议公布时间，纽约可能在前一晚或凌晨公布。
- ECB：法兰克福当地 14:15 决议、14:45 新闻发布会；BOE：伦敦当地 12:00 决议及纪要；BOC：多伦多当地 09:45 决议。自动处理各地夏令时及其不同步的周次。15 分钟仅为显示长度。
- 初始 dates.json 是截至 2026-11-15 核对的 2026 年剩余会议及 2027 年全年会议；45 个事件。之后从四家官方网页读取日期，已过去的快照日期保留。如果抓取失败、解析无数据或未来日程异常缩减，则不发布新文件。非常规会议、临时讲话、突发干预不保证覆盖，时间规则变化须人工修改程序。

## 安装
1. 创建公开仓库 `global-central-banks`，上传 `central_banks.py`、`test_central_banks.py`、`requirements.txt`、`dates.json`、`global-central-banks.ics`、`README.md`。
2. 单独创建 `.github/workflows/update-calendar.yml`，粘贴压缩包内的工作流。Actions → Update Global Central Banks → Run workflow。
3. 成功后订阅 `https://raw.githubusercontent.com/你的用户名/global-central-banks/refs/heads/main/global-central-banks.ics#1`。
4. 每日 UTC 07:53 检查，无 API Key。Google Calendar 自己决定刷新周期。

## 本地
`python -m pip install -r requirements.txt`；`python -m unittest -v`；`python central_banks.py --offline`（使用快照）或 `python central_banks.py`（访问官方页面）。测试使用模拟网页，不是实际网络端到端测试。

## 官方来源
- BOJ: https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm
- ECB: https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html
- ECB 时间: https://www.ecb.europa.eu/press/govcdec/mopo/html/index.en.html ; https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/html/index.en.html
- BOE: https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates ; https://www.bankofengland.co.uk/monetary-policy
- BOC: https://www.bankofcanada.ca/core-functions/monetary-policy/key-interest-rate/ ; https://www.bankofcanada.ca/2026/07/bank-canada-publishes-2027-schedule-policy-interest-rate-announcements-other-major-publications/

仅供日历规划，不连接交易系统。实际交易前核对官方公告。
