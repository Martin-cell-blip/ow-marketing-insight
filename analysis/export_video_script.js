// 视频脚本：《守望先锋凉了吗？》5–6 分钟数据解说。数字全部取自 report/data.json 与 analysis/metrics_<日期>.json。
// 用法：node analysis/export_video_script.js（NODE_PATH 指向全局 node_modules，由 export_office.py 同样方式调用）
// 输出：deliverables/OW视频脚本_守望先锋凉了吗_<日期>.docx
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType,
  ShadingType, PageOrientation, BorderStyle, LevelFormat, AlignmentType,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const D = JSON.parse(fs.readFileSync(path.join(ROOT, "report", "data.json"), "utf-8"));
const DAY = D.meta.cutoff;
const M = JSON.parse(fs.readFileSync(path.join(ROOT, "analysis", `metrics_${DAY}.json`), "utf-8"));

// ---------- 从数据取数 ----------
const comp = M.composition, pan = M.panel, rec = M.recent, po = M.official_pctile;
const pct = x => `${Math.round(x)}%`;
const th = Object.fromEntries(rec.themes.map(t => [t.theme, t]));
const young = pan.by_age_at_july[0], old = pan.by_age_at_july[pan.by_age_at_july.length - 1];
const esm = rec.esports_match_titles;
const N = {
  julyClean: comp.july.n_clean.toLocaleString("en-US"),
  j30: pct(comp.july.share_pub_within_30d), r30: pct(comp.replica.share_pub_within_30d),
  overlap: comp.overlap_clean, nRandom: pan.n_random, nFound: pan.n_random_found,
  young: young.median_ratio, old: old.median_ratio,
  weekly: rec.n_weekly_sample.toLocaleString("en-US"), weeks: rec.weekly_windows.length,
  hero: Math.round(th["新英雄/新赛季"].median_pctile_in_week), skin: Math.round(th["活动/福利/外观"].median_pctile_in_week),
  espShare: pct(th["赛事"].share), espPct: Math.round(th["赛事"].median_pctile_in_week),
  espN: esm.n_esports, espMatch: esm.n_match_like,
  offMain: Math.round(po.main.median), offEsp: Math.round(po.esports.median), ugc: Math.round(po.ugc.median),
  offMainN: po.main.n, offEspN: po.esports.n,
  tut: M.official_tutorials.n, recentN: rec.n_clean.toLocaleString("en-US"), ret: M.returning_titles.n,
};

// ---------- 分镜（旁白即口播稿；时长按 4.6 字/秒估算，标点不计） ----------
const RATE = 4.6;
const TODO = "【待你补充】";
const S = [
  { ch: "开场", visual: "B 站搜索「守望先锋」的录屏，向下滚动，停在两个标题上。只放标题文字，隐去封面、UP 主昵称和头像。",
    vo: "在 B 站搜守望先锋，很容易刷到这样的标题。「16年引爆全球的守望先锋!现在到底成啥样了？！」151 万播放。「我心中最可惜的游戏守望先锋，他怎么凉的？」36 万。",
    text: "标题卡 ×2；角标「151 万」「36 万」", src: "7 月基线、10 月快照（播放为各自抓取时）" },
  { ch: "开场", visual: "黑底打字「守望先锋凉了吗？」，然后切到数据看板首页。",
    vo: "守望先锋到底凉没凉，隔几个月就有人问一次。我想用数据回答这个问题，结果第一步就被数据骗了。",
    text: "片名卡：守望先锋凉了吗？", src: "" },

  { ch: "一 · 搜索会骗人", visual: "看板「方法与来源」里的采集情况表，镜头慢推到关键词与页数。",
    vo: "我做的事很简单。七月和十月，用同样五个关键词在 B 站搜索，各抓一次，每个词翻到第五十页。",
    text: "5 个关键词 × 综合排序 × 每词 50 页｜7 月一次，10 月一次", src: "fetch_log：replica 设计" },
  { ch: "一 · 搜索会骗人", visual: "看板「样本口径」柱状图，只显示灰色的 7 月柱子，高亮 2026-07。",
    vo: `七月那次，清洗后有 ${N.julyClean} 条。按发布月份排开，最高的柱子在七月，看上去七月正在爆发。`,
    text: "高亮：2026-07", src: "看板第 04 节" },
  { ch: "一 · 搜索会骗人", visual: "橙色的 10 月柱子出现，最高点移到 2026-10。",
    vo: "十月再抓一次，最高的柱子跑到了十月，而十月才过了一半。两次都是最近一个月最火。",
    text: "两次都是「最近一个月最火」", src: "看板第 04 节" },
  { ch: "一 · 搜索会骗人", visual: "两张数字卡依次弹出。",
    vo: `看两个数字就明白了。七月那批视频，${N.j30} 是抓取前 30 天内发的；十月那批是 ${N.r30}。两次结果里同时出现的视频只有 ${N.overlap} 条。两次拿到的基本是两批视频，而且都偏向新视频。`,
    text: `${N.j30} → ${N.r30}｜两次重合 ${N.overlap} 条`, src: "metrics：composition" },
  { ch: "一 · 搜索会骗人", visual: "看板「同一视频」图，橙点从上往下逐行出现。",
    vo: `还有一层。我从七月那批里随机抽了 ${N.nRandom} 条，十月再查它们的播放。七月时发布不到一个月的视频，三个月后中位涨到 ${N.young} 倍；发布一年以上的，只涨到 ${N.old} 倍。新视频还在长，老视频差不多停了。`,
    text: `发布 ≤30 天：${N.young}×｜发布 >1 年：${N.old}×`, src: "看板第 05 节" },
  { ch: "一 · 搜索会骗人", visual: "章节小结卡。",
    vo: "所以拿搜索结果按月份比热度，比出来的主要是你哪天去搜。它回答不了凉没凉。",
    text: "小结卡 1", src: "" },

  { ch: "二 · 换一种比法", visual: "动画：一条时间轴按周切成 13 段，每段落下一排视频卡片。",
    vo: `不能比总量，那就只跟同一周发的视频比。我把七月二十二号以后按周切开，每周每个词取搜索前三页，一共 ${N.weekly} 条。每条视频只跟同一周发的排名次，排在正中间就是 50。`,
    text: `${N.weeks} 周 × 5 个词 × 前 3 页 = ${N.weekly} 条｜同周百分位：50 = 居中`, src: "fetch_log：weekly 设计" },
  { ch: "二 · 换一种比法", visual: "看板主题图，高亮新英雄与外观两行；穿插 D.Mon、血律的游戏内录屏（不搬运官方宣传片整段）。",
    vo: `这样比，有三件事比较清楚。第一，新英雄和新皮肤的视频排得靠前：新英雄、新赛季类中位排在 ${N.hero}，皮肤和活动类排在 ${N.skin}。这和 D.Mon、血律上线的时间重合。`,
    text: `新英雄/新赛季 ${N.hero}｜皮肤/活动 ${N.skin}`, src: "看板第 06 节" },
  { ch: "二 · 换一种比法", visual: "赛事视频标题墙（只放标题文字，快速滚动），再切回主题图的赛事一行。",
    vo: `第二，赛事视频最多，排名却偏低。赛事类占了两成，中位只排在 ${N.espPct}。${N.espN} 条赛事视频里，${N.espMatch} 条的标题是某一场对阵、某个比赛日，或者选手的第一视角。一场比赛被切成很多条，这可能是单条排名低的原因之一。直播的观看不算在里面。`,
    text: `占 ${N.espShare}，中位 ${N.espPct}｜${N.espN} 条中 ${N.espMatch} 条是单场或第一视角`, src: "metrics：esports_match_titles" },
  { ch: "二 · 换一种比法", visual: "三根横条对比：官方视频号、官方电竞号、其他账号。",
    vo: `第三，官方号比我想的能打。官方视频号的视频排在 ${N.offMain}，官方电竞号 ${N.offEsp}，其他账号 ${N.ugc}。我七月写过官方电竞号不如 UP 主，那是拿累计播放的平均值比出来的，现在看站不住。不过官方视频本来就更容易被搜到。`,
    text: `官方视频号 ${N.offMain}｜官方电竞号 ${N.offEsp}｜其他账号 ${N.ugc}`, src: "看板发现 03" },
  { ch: "二 · 换一种比法", visual: "章节小结卡（停 3 秒，无旁白）。", vo: "", seconds: 3, text: "小结卡 2", src: "" },

  { ch: "三 · 官方这三个月在做什么", visual: "你的游戏录屏或出镜。", vo: `${TODO}用一两句讲你自己离开或回坑的经历：什么时候不玩的、为什么回来。没有就整段删掉。`,
    seconds: 8, todo: true, text: "", src: "作者本人提供" },
  { ch: "三 · 官方这三个月在做什么", visual: "官网公告截图（标注发布日期），接新手任务界面录屏。",
    vo: `再看官方这三个月在做什么。对新玩家，给得很直接。八月起，新玩家买高级战令半价；十月起，注册不到 60 天的新玩家做完新手任务，能白拿一个满级神话皮肤。B 站官方号还连发了两批新手英雄教学，我在样本里数到 ${N.tut} 条。`,
    text: `8-12 起 新玩家高级战令半价｜10-07 起 注册不足 60 天送满级神话｜官方新手教学 ${N.tut} 条`, src: "S03、S10；metrics：official_tutorials" },
  { ch: "三 · 官方这三个月在做什么", visual: "往期战令界面录屏（你的账号，UID 打码），再切英雄选择界面，停在 D.Mon、血律、黑影。",
    vo: "对回归玩家，其实也有好东西。第五赛季把第一到第九赛季，还有第十五赛季的旧战令拿了回来，以前推到哪，现在接着推。离开这段时间，多了 D.Mon 和血律两个英雄，黑影从输出改成了支援。九月嘉年华还送过一张神话代券，十月六号已经截止了。",
    text: "往期战令返场：S1–S9、S15，进度继承｜新英雄：D.Mon、血律｜黑影 → 支援｜神话代券 10-06 截止", src: "S09、S07、S16" },
  { ch: "三 · 官方这三个月在做什么", visual: "看板发现 01；18 条回坑相关标题快速滚过（只放标题）。",
    vo: `问题是，这些信息散在各个赛季公告里。七月以后我抓到的 ${N.recentN} 条新视频，标题提到回坑、回归或者老玩家的，只有 ${N.ret} 条，大多是皮肤调侃和主播回归。讲回来以后怎么接上进度的，我只找到一条活动奖励合集。官网新闻里，也没有一篇是写给回归玩家的。`,
    text: `${N.recentN} 条里 ${N.ret} 条`, src: "metrics：returning_titles；官网新闻快照" },
  { ch: "三 · 官方这三个月在做什么", visual: "两条评论原文卡（不显示用户名和头像）。",
    vo: "评论区有人说：「玩的越来越少，看的越来越多。」还有人说：「脱坑那么久我都爱看。」离开的人可能还在看，只是很少有内容按他们的处境，把这些讲清楚。",
    text: "评论原文卡 ×2", src: "评论快照 C419、C445" },
  { ch: "三 · 官方这三个月在做什么", visual: "章节小结卡（停 3 秒，无旁白）。", vo: "", seconds: 3, text: "小结卡 3", src: "" },

  { ch: "四 · 接下来", visual: "看板时间线，三个斜纹节点依次点亮。",
    vo: "接下来两个多月，节点比较集中。城市挑战者秋季赛十月二十五号开打，不限段位，二十二个城市。中国赛区第三赛段打到十一月八号。十二月二号到六号，全球总决赛在广州，后三天在广州体育馆，具体以主办方公告为准。",
    text: "10-25 城市挑战者｜11-08 第三赛段结束｜12-02 至 06 全球总决赛 · 广州　小字：场馆来源 白云融媒、Liquipedia", src: "S11、S15（第三方）、S14（未见主办方原文）" },
  { ch: "四 · 接下来", visual: "你的出镜或录屏。", vo: `${TODO}你会不会关注或去现场看总决赛、支持哪支队伍，一两句即可。`,
    seconds: 8, todo: true, text: "", src: "作者本人提供" },
  { ch: "四 · 接下来", visual: "游戏内录屏，镜头拉远。",
    vo: "如果你离开了一段时间，这可能是回来看看的时间点。", text: "小结卡 4", src: "" },

  { ch: "结尾", visual: "看板首页缓慢推近。",
    vo: "所以守望先锋凉没凉，搜索数据给不出答案。换个比法，它告诉你的东西反而更有用：哪类内容在同一周更受关注，官方这三个月在给谁发福利，接下来哪几天值得回来看看。",
    text: "同周比较｜官方给谁发福利｜接下来的节点", src: "" },
  { ch: "结尾", visual: "互动卡，角落标注数据截止日期。",
    vo: "你是什么时候离开守望先锋的，又是什么时候回来的？评论区告诉我。数据和方法放在简介里。",
    text: `互动卡｜数据截至 ${DAY}（北京时间）`, src: "" },
];

// 时长与时间码
const spoken = t => t.replace(/【[^】]*】/g, "").replace(/[\s，。；：、！？「」“”…（）()·,.;:!?\-—|｜/×→≤>]/g, "").length;
let t = 0;
const fmtT = s => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;
for (const s of S) {
  s.chars = s.todo ? 0 : spoken(s.vo);
  s.dur = s.seconds || Math.max(3, Math.round(s.chars / RATE + 1));  // +1 秒留给画面切换
  s.start = t; t += s.dur; s.end = t;
}
const TOTAL = t, VO_CHARS = S.reduce((a, s) => a + s.chars, 0);

const titles = [
  "守望先锋凉了吗？我抓了两次 B 站数据",
  "别再用搜索结果判断守望先锋凉没凉了",
  "守望先锋这三个月：新玩家送神话，老玩家呢？",
];
const cards = [
  "搜索结果偏向最近发布的视频。按月份比热度，比的主要是抓取时间。",
  "只跟同一周比：新英雄和皮肤靠前，赛事视频多但单条排名偏低，官方号不弱。",
  "新玩家有福利和教学；回归玩家的好处散在公告里，标题直接讲回坑的新视频很少。",
  "10 月到 12 月：城市挑战者、第三赛段、广州全球总决赛。",
];
const intro = [
  `七月和十月，我用同样的关键词在 B 站抓了两次守望先锋视频，又按周切窗，只在同一周发布的视频之间比较。数据截至 ${DAY}（北京时间）。`,
  "方法：B 站公开搜索接口的检索样本；排名只在同一周发布的视频之间计算。",
  "来源：守望先锋国服官网公告（第4、5赛季，暴雪嘉年华，城市挑战者等）；赛事日程参考 Liquipedia 与白云融媒，以主办方公告为准。",
  "个人研究，与暴雪娱乐、网易无隶属关系。",
  `完整数据看板：${TODO}放你的链接`,
];
const pinned = "你是哪一年入坑、哪一年离开、什么时候回来的？我想看看大家卡在哪一步，下一期就从评论里挑问题讲。";
const todos = [
  "三 · 开头：你自己离开或回坑的经历（可整段删除，不要用别人的经历代替）。",
  "四 · 中段：你会不会关注总决赛、支持哪支队伍。",
  "录屏素材：往期战令界面（UID 打码）、英雄选择界面、几段普通对局、新手任务界面。",
  "简介里的看板链接：看板目前只在本地，是否公开部署由你决定。",
  "发布当天复核：活动与福利以官网当日公告为准（例如神话代券已截止、热补丁会改英雄数值）。",
];
const rights = [
  "他人视频只放标题文字，不用封面截图，不出现 UP 主昵称与头像。",
  "评论截图去掉用户名和头像，只保留原文。",
  "官方宣传片不整段搬运，优先用自己的游戏内录屏。",
  "比赛画面授权不明，本片不用。",
];
const checks = [
  ["7 月样本清洗后条数", N.julyClean, "metrics.composition.july.n_clean"],
  ["抓取前 30 天内发布占比（7 月 / 10 月）", `${N.j30} / ${N.r30}`, "metrics.composition.*.share_pub_within_30d"],
  ["两次样本重合条数", N.overlap, "metrics.composition.overlap_clean"],
  ["同一视频增长倍数（≤30 天 / >1 年）", `${N.young} / ${N.old}`, "metrics.panel.by_age_at_july"],
  ["随机抽样 / 能搜回", `${N.nRandom} / ${N.nFound}`, "metrics.panel.n_random / n_random_found"],
  ["按周样本条数、周数", `${N.weekly} / ${N.weeks}`, "metrics.recent.n_weekly_sample / weekly_windows"],
  ["新英雄、皮肤类同周排名", `${N.hero} / ${N.skin}`, "metrics.recent.themes"],
  ["赛事类占比、排名、单场标题", `${N.espShare} / ${N.espPct} / ${N.espMatch} of ${N.espN}`, "metrics.recent.themes + esports_match_titles"],
  ["官方视频号 / 官方电竞号 / 其他账号", `${N.offMain} / ${N.offEsp} / ${N.ugc}`, "metrics.official_pctile"],
  ["官方新手教学条数", N.tut, "metrics.official_tutorials.n"],
  ["新视频总数 / 标题提到回坑", `${N.recentN} / ${N.ret}`, "metrics.recent.n_clean / returning_titles.n"],
  ["开场两个标题的播放", "151 万 / 36 万", "7 月基线 BV1rJVfzDECL；10 月快照 BV1Yw8E6UECu"],
  ["版本、福利、赛事日期", "见各段来源列", "analysis/evidence_sources.json（S03、S07、S09–S11、S14–S16）"],
];

// ---------- Word 排版 ----------
const FONT = "Microsoft YaHei";
const run = (text, o = {}) => new TextRun({ text, font: FONT, size: o.size || 22, bold: o.bold, color: o.color });
const para = (children, o = {}) => new Paragraph({ spacing: { after: o.after ?? 100, line: o.line || 360 }, children: Array.isArray(children) ? children : [children], ...o.p });
const h1 = text => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 300, after: 120 }, children: [run(text, { bold: true, size: 30, color: "1F2937" })] });
const h2 = text => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 220, after: 80 }, children: [run(text, { bold: true, size: 25, color: "B45309" })] });
const bullet = text => new Paragraph({ numbering: { reference: "dots", level: 0 }, spacing: { after: 60, line: 320 }, children: [run(text, { size: 21 })] });
const voRuns = (text, size) => text.split(/(【[^】]*】)/).filter(Boolean).map(seg =>
  seg.startsWith("【") ? run(seg, { bold: true, color: "C2410C", size }) : run(seg, { size }));

// 口播稿（按章节连续排）
const script = [];
let lastCh = null;
for (const s of S) {
  if (s.ch !== lastCh) { script.push(h2(`${s.ch}　${fmtT(s.start)}`)); lastCh = s.ch; }
  if (!s.vo) continue;
  script.push(para(voRuns(s.vo), { line: 400 }));
}

// 分镜表（横向页）
const W = [1100, 3200, 5000, 3300, 2200];
const cell = (children, w, head = false) => new TableCell({
  width: { size: w, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 90, right: 90 },
  shading: head ? { type: ShadingType.CLEAR, color: "auto", fill: "F3F4F6" } : undefined,
  children: [new Paragraph({ children: Array.isArray(children) ? children : [run(children, { size: 18, bold: head })] })],
});
const shotRows = [new TableRow({ tableHeader: true, children: ["时间码", "画面", "旁白", "屏幕文字 / 数据卡", "素材与来源"].map((h, i) => cell(h, W[i], true)) })];
for (const s of S) {
  shotRows.push(new TableRow({ cantSplit: true, children: [
    cell([run(`${fmtT(s.start)}–${fmtT(s.end)}`, { size: 18, bold: true }),
          new TextRun({ text: s.ch, break: 1, font: FONT, size: 16, color: "6B7280" })], W[0]),
    cell(s.visual, W[1]),
    cell(s.vo ? voRuns(s.vo, 18) : [run("（无旁白）", { size: 18, color: "6B7280" })], W[2]),
    cell(s.text || "—", W[3]),
    cell(s.src || "—", W[4]),
  ] }));
}

const portrait = [
  new Paragraph({ spacing: { after: 60 }, children: [run("守望先锋凉了吗？", { size: 40, bold: true })] }),
  para(run(`5–6 分钟数据解说 · 脚本与口播稿 · 数据截至 ${DAY}（北京时间）`, { size: 22, color: "B45309" })),
  para(run(`按 ${RATE} 字/秒估算，旁白约 ${VO_CHARS} 字，全片约 ${fmtT(TOTAL)}（已给两段待你补充的内容各留约 8 秒）。橙色【】处需要你补充或替换。`, { size: 19, color: "6B7280" })),
  new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "F59E0B", space: 4 } }, children: [] }),

  h1("一、标题与封面"),
  ...titles.map((x, i) => para(run(`标题 ${i + 1}：${x}`, { bold: i === 0 }))),
  para([run("封面：", { bold: true }), run("主文字「凉了吗？」；副文字「我抓了两次 B 站数据」。底图用看板里两张柱子都冲到最近一个月的那张图。")]),
  para([run("风格：", { bold: true }), run("第一人称旁白，游戏录屏为底，关键数字用看板同款数据卡（石板灰底、橙色数字）。每章用一个问题开头、一句话收尾，B 站分 P 按章节打点。")]),

  h1("二、口播稿（照着念，边念边改）"),
  para(run("画面角标、小字和括号里的来源只放在屏幕上，不用念。", { size: 19, color: "6B7280" })),
  ...script,

  h1("三、章节小结卡"),
  ...cards.map((c, i) => para([run(`小结卡 ${i + 1}：`, { bold: true }), run(c)])),

  h1("四、简介与置顶评论"),
  ...intro.map(x => para(voRuns(x))),
  para([run("置顶评论：", { bold: true }), run(pinned)]),

  h1("五、需要你补充的地方"),
  ...todos.map(bullet),
  h2("素材使用"),
  ...rights.map(bullet),

  h1("六、数字核对表"),
  para(run("改稿时如果动了数字，先在这里找到出处再改。", { size: 19, color: "6B7280" })),
  new Table({ width: { size: 9026, type: WidthType.DXA }, columnWidths: [3300, 2026, 3700],
    rows: [new TableRow({ tableHeader: true, children: [["数字", 3300], ["值", 2026], ["出处", 3700]].map(([h, w]) => cell(h, w, true)) }),
           ...checks.map(r => new TableRow({ cantSplit: true, children: [cell(String(r[0]), 3300), cell(String(r[1]), 2026), cell(String(r[2]), 3700)] }))] }),
];

const doc = new Document({
  styles: { default: { document: { run: { font: FONT, size: 22 } } } },
  numbering: { config: [{ reference: "dots", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 360, hanging: 240 } } } }] }] },
  sections: [
    { properties: { page: { margin: { top: 1200, bottom: 1200, left: 1440, right: 1440 } } }, children: portrait },
    { properties: { page: { size: { orientation: PageOrientation.LANDSCAPE }, margin: { top: 900, bottom: 900, left: 900, right: 900 } } },
      children: [h1("七、分镜脚本（时间码为估算，录完按实际口播调整）"), new Table({ width: { size: W.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: W, rows: shotRows })] },
  ],
});
const out = path.join(ROOT, "deliverables", `OW视频脚本_守望先锋凉了吗_${DAY}.docx`);
Packer.toBuffer(doc).then(buf => { fs.writeFileSync(out, buf); console.log(`OK -> ${out}  旁白 ${VO_CHARS} 字，约 ${fmtT(TOTAL)}`); });
