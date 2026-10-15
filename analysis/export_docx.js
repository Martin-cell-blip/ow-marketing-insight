// 生成简短中文 Word 摘要：核心发现、旧结论变化、优先营销建议。数据全部来自 report/data.json。
// 用法：node analysis/export_docx.js <data.json> <out.docx>（由 analysis/export_office.py 调用）
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, ShadingType, AlignmentType, LevelFormat, BorderStyle,
} = require("docx");

const [, , dataPath, outPath] = process.argv;
const D = JSON.parse(fs.readFileSync(dataPath, "utf-8"));
const FONT = "Microsoft YaHei";
const strip = s => String(s ?? "").replace(/<[^>]+>/g, "");

const p = (text, opts = {}) => new Paragraph({
  spacing: { after: 80, line: 300 }, ...opts,
  children: [new TextRun({ text: strip(text), font: FONT, size: opts.size || 21, bold: opts.bold, color: opts.color })],
});
const runs = (parts, opts = {}) => new Paragraph({
  spacing: { after: 80, line: 300 }, ...opts,
  children: parts.map(([t, b, c]) => new TextRun({ text: strip(t), bold: !!b, color: c, font: FONT, size: 21 })),
});
const h = (text, level) => new Paragraph({
  heading: level, spacing: { before: level === HeadingLevel.HEADING_1 ? 280 : 200, after: 100 },
  children: [new TextRun({ text, font: FONT, bold: true, size: level === HeadingLevel.HEADING_1 ? 28 : 24, color: "1F2937" })],
});
const bullet = (parts) => new Paragraph({
  numbering: { reference: "dots", level: 0 }, spacing: { after: 60, line: 290 },
  children: (Array.isArray(parts) ? parts : [[parts]]).map(([t, b]) => new TextRun({ text: strip(t), bold: !!b, font: FONT, size: 21 })),
});

// 表格：A4 内容宽 9026 DXA（左右边距 1440）
const TW = 9026;
const cell = (text, w, head = false) => new TableCell({
  width: { size: w, type: WidthType.DXA },
  shading: head ? { type: ShadingType.CLEAR, color: "auto", fill: "F3F4F6" } : undefined,
  margins: { top: 60, bottom: 60, left: 100, right: 100 },
  children: [new Paragraph({ children: [new TextRun({ text: strip(text), font: FONT, size: 19, bold: head })] })],
});
const table = (cols, rows) => new Table({
  width: { size: TW, type: WidthType.DXA }, columnWidths: cols.map(c => c[1]),
  rows: [new TableRow({ tableHeader: true, children: cols.map(([t, w]) => cell(t, w, true)) }),
         ...rows.map(r => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, cols[i][1])) }))],
});

const m = D.meta, P = D.priority, E = D.experiment;
const children = [
  new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: `《守望先锋》B 站内容与玩家信号`, font: FONT, size: 36, bold: true })] }),
  new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: `研究更新摘要 · 截至 ${m.cutoff}（北京时间）`, font: FONT, size: 26, color: "B45309" })] }),
  p(`作者：${m.author}　｜　7 月基线采集：${m.baseline_fetch}（${m.baseline_note}）　｜　本次采集：${m.snapshot_fetch}　｜　个人研究项目，与暴雪娱乐/网易无隶属关系`, { size: 18, color: "6B7280" }),
  new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "F59E0B", space: 4 } }, children: [] }),

  h("一、读数口径", HeadingLevel.HEADING_1),
  bullet("B 站搜索结果是检索样本，不是全站总量；两次抓取的视频集合不同，只比较样本组成，不做增减。"),
  bullet("累计播放随发布时长增长：跨时间只比较同一视频（追踪面板）或同一周发布的视频（同周百分位）。"),
  bullet("高赞评论样本只说明出现了哪些说法，不能估计比例；全部逐条人工复核。结论分「事实 / 推断 / 待验证假设」。"),

  h("二、核心发现", HeadingLevel.HEADING_1),
  p("文中 S01–S17 为已核验来源编号、F01–F02 为失败记录，明细见同目录 Excel「来源与证据」。", { size: 18, color: "6B7280" }),
  ...D.findings.flatMap((f, i) => [
    runs([[`${i + 1}. ${f.title}`, true], [`　【${f.strength}】`, true, f.strength === "事实" ? "0E7490" : "B45309"]], { spacing: { before: 120, after: 60 } }),
    runs([["事实与依据：", true], [f.fact]]),
    runs([["解释与其他可能：", true], [f.reading]]),
    runs([["对营销的意义：", true], [f.meaning]]),
    runs([["下一步：", true], [f.next]]),
  ]),

  h("三、旧结论的变化", HeadingLevel.HEADING_1),
  p("先核验 2026-07 版报告，不预设旧建议正确。下表为核验结果（「撤下」= 证据无法回溯或口径错误）。", { size: 19, color: "4B5563" }),
  table([["7 月报告的说法", 3000], ["结果", 900], ["依据", 5126]], D.corrections.map(c => [c.old, c.status, c.why])),

  h("四、优先营销建议（未经验证的判断）", HeadingLevel.HEADING_1),
  runs([[P.title, true]]),
  p(P.what),
  runs([["北极星指标：", true], [`${P.north_star.name}。${P.north_star.definition}`]]),
  bullet([["分母：", true], [P.north_star.denominator]]),
  bullet([["观察窗口：", true], [P.north_star.window]]),
  bullet([["数据取得：", true], [P.north_star.data]]),
  bullet([["不能证明：", true], [P.north_star.cannot_prove]]),
  runs([["护栏：", true], [P.guardrails.map(g => `${g.name}：${g.definition.replace(/。$/, "")}`).join("；") + "。"]]),
  runs([["个人可用的代理指标：", true], [P.proxies.map(g => `${g.name}（不能证明${g.cannot_prove.replace(/。$/, "")}）`).join("；") + "。"]]),
  runs([["小规模实验：", true], [`${E.title}。核心信息「${E.message}」；${E.content}`]], { spacing: { before: 100, after: 80 } }),
  runs([["停止条件：", true], [E.stop_rule]]),

  h("五、仍缺的数据", HeadingLevel.HEADING_1),
  ...D.limits.map(x => bullet(x)),
  p(`完整看板：report/index.html（docs/index.html 同步）；来源与选题明细见同目录 Excel。`, { size: 18, color: "6B7280" }),
];

const doc = new Document({
  styles: { default: { document: { run: { font: FONT, size: 21 } } } },
  numbering: { config: [{ reference: "dots", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 360, hanging: 240 } } } }] }] },
  sections: [{ properties: { page: { margin: { top: 1200, bottom: 1200, left: 1440, right: 1440 } } }, children }],
});
Packer.toBuffer(doc).then(buf => { fs.writeFileSync(outPath, buf); console.log(`OK -> ${outPath}`); });
