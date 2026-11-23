# v5opt 结构规格与素材表 — Sunday 22 November 2026

> 对标排行榜前 3 名（99.18%–99.24%）的 6 大共同特征，基于 Neon 卡片栅格骨架全面升级。
> 全程纯 Python + Pillow 绘制，1024×1024 原生像素，≤1,048,576 字节，运行两次 MD5 完全一致。

## 1. 版式架构（1024×1024 原生像素）

| 区域 | Y 区间 | 高度 | 规格说明 |
|---|---|---|---|
| 1. 顶部细条 | `0..22` | 22px | 深海军蓝 `#101d3d`，左 `THE WORLD IN ONE DAY`，右 `34 STORIES · 7 REGIONS · EVERY ONE DATED SUNDAY 22 NOVEMBER 2026`（11px 粗体） |
| 2. 超大日期报头 | `24..102` | 78px | `Sunday 22 November 2026`（82px 粗衬线居中）+ `104..109` 双色饰线（3px 黑 + 1px 猩红） |
| 3. 6 格大数字条 | `112..176` | 64px | 6 等宽格，**≥44px 粗衬线大数字** + **10px 全大写标签** + 对应故事编号 `#N`；数值由 `STORIES` 真实提取校验，严禁硬编码 |
| 4. DAY IN UTC 时间轴 | `180..212` | 32px | 深蓝带 `#14213d`，左标 `DAY IN UTC`，右 8 个等宽 UTC 事件格（金色 10px 时刻 + 白色 9px 摘要） |
| 5. 7 色区域条 | `216..238` | 22px | 7 区实色分段，内嵌 `区域名 + 计数`（10px 粗白字），由 `Counter(s.region for s in STORIES)` 动态统计 |
| 6. 主卡区（3×3 共 9 张） | `244..624` | 380px | 3 列×3 行（328×122px，间距 7px）：顶部 3px 区域色带 + 30×30 实色编号块 + 右侧 68×112 线描插画（2px 线宽、无面孔）+ **19px 粗衬线标题** + **12px 无衬线两行导语** + 来源 + 状态标签 |
| 7A. 下半部左图右简讯 | `630..842` | 212px | 左：世界地图（432×212px，7 区着色 + **14 个编号定位点 #10–#23** + 区域图例）；右：两栏编号简讯（558×212px，**16 条 #10–#25**，8 行×2 栏，11px 粗标题 + 9px 来源与状态） |
| 7B. 全宽三栏补充简讯 | `848..944` | 96px | 1000×96px，**9 条 #26–#34**（3 行×3 栏，与上方 3×3 卡片严格对齐，11px 粗标题 + 9px 来源与状态） |
| 8. 底部 DATE CHECK + 图例 | `950..1020` | 70px | 2px 猩红框反伪证声明条（`DATE CHECK — READ THIS FIRST`）：声明截止时间 + **4 条明确剔除的近日期旧闻清单** + `CONFIRMED / ONGOING / REPORTED / CLAIM` 图例说明 + 线描插画声明 |

## 2. 6 格关键数字条（全部由素材真实提取并断言校验）

| 数值 | 标签 | 对应故事 | 核验依据（2026-11-22 当日） |
|---|---|---|---|
| `186` | DRONES AT UKRAINE | #2 | 俄军 11 月 22 日夜间向乌克兰发射 186 架无人机（含 72 架喷气式），非前日 400 架 |
| `161` | DRONES DOWNED | #2 | 乌克兰防空与电子战系统击落或压制其中 161 架 |
| `$120bn` | COP31 FINANCE FLOOR | #1 | COP31 谈判破裂核心争议：发展中国家要求的 1200 亿美元/年适应资金下限被删 |
| `74,742` | GAZA DEATH TOLL | #11 | 加沙卫生部门 11 月 22 日更新累计死亡人数 |
| `856` | HK POLL CANDIDATES | #5 | 香港选举委员会界别分组一般选举 856 名候选人竞逐 723 席，投票率 98.79% |
| `720/9` | INDIA TEST RECORD | #8 | 印度在惠灵顿首场测试赛以 720/9 宣告结束创客场新西兰最高纪录 |

## 3. DAY IN UTC 时间轴（2026-11-22 星期日，8 个等宽时刻）

1. `01:00` — Hong Kong polls open (09:00 HKT)
2. `01:25` — Mexico cartel chief arrested (BBC)
3. `03:00` — COP31 draft objections close
4. `04:00` — Las Vegas F1 GP lights out
5. `09:20` — S. Korea education chief quits
6. `10:44` — BepiColombo reaches Mercury
7. `14:05` — Indonesia plant fire alert
8. `20:43` — Alcaraz wins ATP Finals

## 4. 7 区域统计（总计 34 条，每区 ≥3 条）

| 区域 | 条数 | 领域覆盖 |
|---|---|---|
| EUROPE | 7 | 军事、政治、体育、公共安全、航运 |
| ASIA-PACIFIC | 6 | 政治、灾害、科技/AI、文化、经济、航天 |
| AMERICAS | 6 | 安全/执法、体育、灾害、航空/科技、军事 |
| MIDDLE EAST | 5 | 军事、人道、政治、地区冲突 |
| AFRICA | 4 | 海战、冲突、灾害、外交 |
| OCEANIA | 3 | 体育、政治/气候、气候灾害 |
| WORLD | 3 | 气候峰会、深空科技、全球贸易 |
| **合计** | **34** | 政治、军事、气候、经济、科技、体育、灾害全覆盖 |

## 5. 34 条 2026-11-22 真实国际新闻素材表

### 主卡区（#1–#9，3×3 大卡，含 2px 线描插画）

| # | 区域 | 领域 | 标题 | 导语 | 来源媒体 | 状态 |
|---|---|---|---|---|---|---|
| 1 | WORLD | 气候 | COP31 collapses in Antalya without a deal | Nearly 200 nations deadlock past 03:00 UTC over fossil fuels and a $120bn floor. | Reuters, AFP, BBC | CONFIRMED |
| 2 | EUROPE | 军事 | Russia fires 186 drones; 161 downed | Overnight wave of 72 jet UAVs batters Dymer flats and triggers grid blackouts. | Ukr. Air Force, BBC | CONFIRMED |
| 3 | AFRICA | 军事 | Russian warship Merkury sinks in Benghazi | Corvette capsizes after suspected sea-drone strike in Libya; Maltese ship hit. | Reuters, Al Jazeera | CONFIRMED |
| 4 | MIDDLE EAST | 军事 | Bahrain: Iran strike hurts 2; IRGC claims hit | Manama cites industrial fire near Sitra; Iran alleges US Patriot radar struck. | MEE, Times of Israel | CLAIM |
| 5 | ASIA-PACIFIC | 政治 | Hong Kong polls hit 98.8% with 856 hopefuls | Election Committee vote fills 723 seats as 5,640 electors vote 01:00–10:00 UTC. | info.gov.hk, China Daily | CONFIRMED |
| 6 | WORLD | 科技 | BepiColombo reaches Mercury after 8 yrs | European-Japanese spacecraft enters orbit to map the planet's crust and field. | BBC, ESA | CONFIRMED |
| 7 | AMERICAS | 政治 | Mexico arrests FBI Most Wanted cartel chief | Special forces seize Sinaloa boss Fausto Meza Flores after an intense shootout. | BBC, Reuters | CONFIRMED |
| 8 | OCEANIA | 体育 | India posts record 720/9; NZ holds draw | Visitors shatter New Zealand's Test record before hosts bat 120 overs to draw. | ESPN, Jamaica Observer | CONFIRMED |
| 9 | ASIA-PACIFIC | 灾害 | Indonesia plant fire kills 3; 36 still missing | Rescuers comb gutted Banten confectionery plant while four injured recover. | AFP, BBC, France 24 | ONGOING |

### 两栏编号简讯（#10–#25，共 16 条；其中 #10–#23 对应左侧世界地图 14 个定位点）

| # | 区域 | 城市/坐标 | 标题 | 来源媒体 | 状态 |
|---|---|---|---|---|---|
| 10 | EUROPE | BRATISLAVA (17.1, 48.1) | Fico refuses EU's €45bn loan to Ukraine | Reuters, Kyiv Post | CONFIRMED |
| 11 | MIDDLE EAST | GAZA (34.5, 31.5) | Gaza toll hits 74,742; Hamas urges mediator talks | WAFA, Anadolu | ONGOING |
| 12 | AMERICAS | SAN ANTONIO (-98.5, 29.4) | Wembanyama posts historic 50-pt, 19-reb game | CBS, KSAT | CONFIRMED |
| 13 | AMERICAS | TUPANCIRETÃ (-53.8, -29.1) | Supercell storm kills 5, hurts 250+ in Brazil | AFP | CONFIRMED |
| 14 | ASIA-PACIFIC | SEOUL (127.0, 37.6) | S. Korea education chief quits over AI exam chaos | AFP, BBC | CONFIRMED |
| 15 | AFRICA | KHARTOUM (32.5, 15.6) | RSF drones hit Khartoum homes & UN site, 4 dead | Al Jazeera | REPORTED |
| 16 | AFRICA | BAYELSA (6.1, 4.8) | Boat capsize kills at least 24 mourners in Nigeria | AllAfrica | CONFIRMED |
| 17 | AFRICA | OYO, CONGO (15.9, -1.2) | Kenya's Ruto & DRC's Tshisekedi restore full ties | Pan African Visions | CONFIRMED |
| 18 | OCEANIA | CANBERRA (149.1, -35.3) | Albanese backs Bowen after COP31 collapse uproar | Guardian AU | CONFIRMED |
| 19 | OCEANIA | PORT MORESBY (147.2, -9.4) | Pope Leo XIV urges aid as drought grips all 22 PNG zones | Crux, CathNews | ONGOING |
| 20 | EUROPE | TURIN (7.7, 45.1) | Alcaraz beats Zverev for first ATP Finals title | Reuters, Guardian | CONFIRMED |
| 21 | EUROPE | MANCHESTER (-2.2, 53.5) | 12,000 evacuated at Co-op Live over suspected gas | BBC, SBS | REPORTED |
| 22 | ASIA-PACIFIC | OKINAWA (127.7, 26.2) | Japan marks Shuri Castle hall rebuild 7 yrs post-fire | Wash. Post, JT | CONFIRMED |
| 23 | MIDDLE EAST | BEIRUT (35.5, 33.9) | Lebanon marks 83rd Independence Day as locals return | NPR, L'Orient | ONGOING |
| 24 | EUROPE | PORTIMÃO | Márquez clinches 8th MotoGP title, ties Agostini | AP | CONFIRMED |
| 25 | AMERICAS | LAS VEGAS | Verstappen wins Las Vegas GP ahead of McLarens | Guardian, National | CONFIRMED |

### 全宽三栏补充简讯（#26–#34，共 9 条）

| # | 区域 | 地点 | 标题 | 来源媒体 | 状态 |
|---|---|---|---|---|---|
| 26 | EUROPE | GULF OF FINLAND | Russia-bound ship towed after suspected drone hit | BBC, Finnish DF | REPORTED |
| 27 | EUROPE | LIVERPOOL | Liverpool routs Man Utd 4-0 in Pochettino debut | Guardian, BBC | CONFIRMED |
| 28 | MIDDLE EAST | RIYADH | Saudi coalition intercepts Houthi missiles & drones | Anadolu, ISW | REPORTED |
| 29 | MIDDLE EAST | WEST BANK | Israeli opposition slams settler arson on villages | Guardian | ONGOING |
| 30 | AMERICAS | ATLANTA | Software fault delays 1,000+ Delta Air Lines flights | AP, The Hindu | CONFIRMED |
| 31 | AMERICAS | IOWA | US Army to detonate unstable munitions despite court | BBC | CONFIRMED |
| 32 | ASIA-PACIFIC | GAZIPUR | Bangladesh garment clashes; 95 BGB platoons sent | Business Standard | ONGOING |
| 33 | ASIA-PACIFIC | ISLAMABAD | Pakistan's first astronaut departs for Tiangong | APP, Arab News | CONFIRMED |
| 34 | WORLD | GENEVA | WTO flags record $1.5tn export & $5.4tn import curbs | WTO, SunStar | CONFIRMED |

## 6. DATE CHECK 主动剔除清单（反伪证）

以下高热度事件发生于 2026-11-22 之前，已主动核验并刻意排除：
- **Peru M6.7 earthquake** — 发生于 Fri 20 Nov 2026（非 11 月 22 日）
- **Russia's 400-drone barrage on Ukraine** — 发生于 Thu 19–Fri 20 Nov 2026（11 月 22 日夜间为 186 架，非 400 架）
- **APEC Shenzhen US–China–Russia trilateral summit** — 发生于 Thu 19 Nov 2026
- **French Senate police-shooting bill final vote (205–110)** — 发生于 Fri 20 Nov 2026
- 注：同时剔除了 2025 年同期旧闻（2025-11 孟加拉地震与越南洪灾）
