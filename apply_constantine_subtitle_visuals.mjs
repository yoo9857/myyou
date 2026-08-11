import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const pkg = path.join(process.env.APPDATA, "npm", "node_modules", "capcut-cli", "dist");
const lib = await import(pathToFileURL(path.join(pkg, "lib.js")).href);
const fx = await import(pathToFileURL(path.join(pkg, "decorators.js")).href);
const args = process.argv.slice(2);
const arg = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : undefined; };
const project = arg("--project") || path.join(process.env.LOCALAPPDATA, "CapCut", "User Data", "Projects", "com.lveditor.draft", "CONSTANTINE_STORY_REVIEW_V5");
const reportPath = arg("--report") || "C:\\cineyoutube\\Constantine\\story_review_v5\\output\\SUBTITLE_VISUAL_QA.json";
const dryRun = args.includes("--dry-run");

const { draft, filePath } = lib.loadDraft(project);
const movie = draft.tracks.find((t) => t.name === "MOVIE_DIALOGUE");
const review = draft.tracks.find((t) => t.name === "REVIEW_NARRATION");
if (!movie || !review) throw new Error("Required subtitle tracks are missing");
const textById = new Map(draft.materials.texts.map((m) => [m.id, m]));

// Idempotently replace only text animations; keep video/image animations intact.
const textSegments = [...movie.segments, ...review.segments];
const oldAnimIds = new Set((draft.materials.material_animations || []).map((m) => m.id));
const usedByText = new Set();
for (const seg of textSegments) {
  for (const ref of seg.extra_material_refs || []) if (oldAnimIds.has(ref)) usedByText.add(ref);
  seg.extra_material_refs = (seg.extra_material_refs || []).filter((ref) => !oldAnimIds.has(ref));
  seg.common_keyframes = [];
}
draft.materials.material_animations = (draft.materials.material_animations || []).filter((m) => !usedByText.has(m.id));

const PALETTE = {
  dialogue: "#F2F3F5",
  narration: "#FFFFFF",
  name_base: "#F9E7E5",
  name_accent: "#FF241C",
  situation: "#FFFFFF",
  situation_accent: "#FFF1A6",
};
const FONT_ROOT = "C:/Users/hanbi/AppData/Local/Microsoft/Windows/Fonts";
const FONT = {
  dialogue: `${FONT_ROOT}/Pretendard-Medium.ttf`,
  main: `${FONT_ROOT}/ArchivoBlack-Regular.ttf`,
  name: `${FONT_ROOT}/RobotoCondensed-BoldItalic.ttf`,
  situation: `${FONT_ROOT}/CormorantGaramond-Medium.ttf`,
};
const TENSION = ["악령", "악마", "지옥", "죽", "강림", "마몬", "예언", "붙잡", "사라", "공격", "위험", "피", "demon", "hell", "dead", "death", "arrival", "mammon", "prophecy", "possessed", "attack", "danger", "blood"];
const OCCULT = ["천국", "중립", "규칙", "감각", "진실", "징후", "유물", "성수", "성물", "퇴마", "heaven", "neutral", "rules", "senses", "truth", "signs", "relic", "holy water", "exorcism"];
const COMIC = ["박물관", "성질 급한", "수상할 정도", "수돗물", "고양이", "생활형", "쓸모없는", "전용 내비게이션", "변명", "museum material", "suspiciously calm", "tap water", "a cat", "oddly practical", "useless", "navigation system", "excuse"];
const NAMES = ["마누엘", "콘스탄틴", "안젤라", "이사벨", "비먼", "채즈", "마몬", "미드나이트", "Manuel", "Constantine", "Angela", "Isabel", "Beeman", "Chas", "Mammon", "Midnite"];
const NAME_CUES = new Set([1, 4, 8, 12, 16, 19, 23, 25, 28]);
const SITUATION_CUES = new Set([2, 5, 7, 9, 11, 13, 15, 17, 18, 20, 22, 24, 26, 27]);
const TENSION_CUES = new Set([4, 10, 15, 19, 25, 27]);
const COMIC_CUES = new Set([3, 6, 14, 21, 24]);
const firstMatch = (text, words) => {
  let best = null;
  const haystack = text.toLocaleLowerCase("en-US");
  for (const word of words) {
    const start = haystack.indexOf(word.toLocaleLowerCase("en-US"));
    if (start >= 0 && (!best || start < best.start)) best = { start, end: start + word.length, word };
  }
  return best;
};
const visibleLength = (text) => [...text.replace(/\s/g, "")].length;
const adaptiveSize = (text, kind) => {
  const n = visibleLength(text);
  if (kind === "dialogue") return n <= 14 ? 5.15 : n <= 24 ? 4.85 : n <= 34 ? 4.55 : 4.25;
  if (kind === "situation") return n <= 22 ? 6.0 : n <= 32 ? 5.7 : n <= 42 ? 5.35 : 5.0;
  return n <= 18 ? 6.7 : n <= 28 ? 6.35 : n <= 38 ? 5.95 : 5.5;
};
const balancedBreak = (text, kind) => {
  const clean = text.replace(/\s+/g, " ").trim();
  const limit = kind === "dialogue" ? 17 : 22;
  if ([...clean].length <= limit) return clean;
  const target = clean.length / 2;
  const candidates = [];
  for (let i = 1; i < clean.length - 1; i++) {
    if (clean[i] === " " || ",.…?!".includes(clean[i - 1])) {
      const split = clean[i] === " " ? i : i;
      const left = clean.slice(0, split).trim().length;
      const right = clean.slice(split).trim().length;
      if (left >= 7 && right >= 7) {
        const punctuationBonus = ",.…?!".includes(clean[i - 1]) ? -3 : 0;
        candidates.push({ split, score: Math.abs(left - target) + Math.abs(right - target) + punctuationBonus });
      }
    }
  }
  const split = candidates.sort((a, b) => a.score - b.score)[0]?.split ?? Math.round(target);
  return `${clean.slice(0, split).trim()}\n${clean.slice(split).trim()}`;
};
const rangesFor = (text, hit, cfg) => {
  if (!hit) return null;
  const base = { font_color: cfg.base, font_size: cfg.size, bold: cfg.bold, italic: cfg.italic };
  const ranges = [];
  if (hit.start > 0) ranges.push({ start: 0, end: hit.start, ...base });
  ranges.push({ start: hit.start, end: hit.end, font_color: cfg.accent, font_size: Math.min(cfg.size * 1.06, 7.0), bold: true, italic: cfg.italic });
  if (hit.end < text.length) ranges.push({ start: hit.end, end: text.length, ...base });
  return ranges;
};
const applyStyle = (seg, material, cfg) => {
  const rawText = material.recognize_text || JSON.parse(material.content).text || "";
  const text = cfg.displayText || rawText;
  const payload = JSON.parse(material.content);
  payload.text = text;
  payload.styles = [{
    range: [0, text.length], size: cfg.size, bold: cfg.bold, italic: cfg.italic, underline: false,
    fill: { alpha: 1, content: { render_type: "solid", solid: { alpha: 1, color: fx.hexToRgb01(cfg.base) } } },
  }];
  material.content = JSON.stringify(payload);
  material.recognize_text = text;
  Object.assign(material, {
    font_size: cfg.size,
    text_size: Math.round(cfg.size * 6),
    text_color: cfg.base,
    text_alpha: 1,
    font_name: cfg.fontName,
    font_path: cfg.fontPath,
    bold: cfg.bold,
    italic: cfg.italic,
    underline: false,
    alignment: 1,
    line_spacing: cfg.lineSpacing,
    letter_spacing: cfg.letterSpacing,
    line_max_width: cfg.maxWidth,
    force_apply_line_max_width: true,
    fixed_width: -1.0,
    fixed_height: -1.0,
    autoAdaptCanvasEnabled: true,
    oneline_cutoff: false,
    has_shadow: true,
    shadow_color: "#000000",
    shadow_alpha: cfg.shadowAlpha,
    shadow_angle: -45.0,
    shadow_distance: cfg.shadowDistance,
    shadow_smoothing: cfg.shadowSmoothing,
    border_color: "#050608",
    border_alpha: 0.98,
    border_width: cfg.borderWidth,
    has_border: cfg.borderWidth > 0,
    background_color: "#000000",
    background_alpha: 0.0,
    background_style: 0,
    style_name: cfg.styleName,
    is_rich_text: Boolean(cfg.highlight),
    italic_degree: cfg.italic ? -9 : 0,
  });
  if (seg.clip?.transform) { seg.clip.transform.x = 0.0; seg.clip.transform.y = cfg.y; }
  if (seg.uniform_scale) { seg.uniform_scale.on = true; seg.uniform_scale.value = 1.0; }
  const ranges = rangesFor(text, cfg.highlight, cfg);
  if (ranges) {
    payload.styles = ranges.map((r) => ({
      range: [r.start, r.end],
      size: r.font_size,
      bold: r.bold,
      italic: r.italic,
      underline: false,
      fill: { alpha: 1, content: { render_type: "solid", solid: { alpha: 1, color: fx.hexToRgb01(r.font_color) } } },
    }));
    material.content = JSON.stringify(payload);
  }
};

const counts = { dialogue: 0, review: 0, main_narration: 0, name_emphasis: 0, situation_narration: 0, two_tone: 0, animated_review: 0, animated_dialogue: 0 };
const animationPlan = [];

for (const seg of movie.segments) {
  const material = textById.get(seg.material_id);
  const text = material?.recognize_text || "";
  if (!material || !text) continue;
  applyStyle(seg, material, {
    displayText: balancedBreak(text, "dialogue"), size: adaptiveSize(text, "dialogue"), base: PALETTE.dialogue, accent: PALETTE.dialogue, highlight: null,
    fontName: "Pretendard Medium", fontPath: FONT.dialogue, bold: false, italic: false,
    lineSpacing: 0.075, letterSpacing: 0.004, maxWidth: 0.78, shadowAlpha: 0.64, shadowDistance: 1.2,
    shadowSmoothing: 0.58, borderWidth: 0.03, y: -0.78, styleName: "MOBILE_DIALOGUE_V5",
  });
  counts.dialogue++;
}

for (let i = 0; i < review.segments.length; i++) {
  const seg = review.segments[i];
  const material = textById.get(seg.material_id);
  const text = material?.recognize_text || "";
  if (!material || !text) continue;
  const cue = i + 1;
  const comic = firstMatch(text, COMIC);
  const tension = firstMatch(text, TENSION);
  const name = firstMatch(text, NAMES);
  const nameStyle = NAME_CUES.has(cue);
  const situationStyle = !nameStyle && SITUATION_CUES.has(cue);
  const situationHit = situationStyle ? (firstMatch(text, OCCULT) || firstMatch(text, ["평범했던 인간", "받아들이지", "죽은 자", "지옥", "닿고 싶었던", "보호받는", "표적", "강림", "시간", "현실", "ordinary man's life", "refuses to accept", "destination of the dead", "reach her sister", "truth", "a target", "time left", "right in front"])) : null;
  const displayText = balancedBreak(text, situationStyle ? "situation" : "narration");
  const rawHighlight = nameStyle ? (name || tension || comic) : situationHit;
  const highlight = rawHighlight ? firstMatch(displayText, [rawHighlight.word]) : null;
  const kind = situationStyle ? "situation" : "narration";
  const narrationSize = adaptiveSize(text, kind);
  const cfg = {
    displayText,
    size: nameStyle ? Math.min(narrationSize * 1.04, 6.8) : narrationSize,
    base: nameStyle ? PALETTE.name_base : situationStyle ? PALETTE.situation : PALETTE.narration,
    accent: nameStyle ? PALETTE.name_accent : PALETTE.situation_accent,
    highlight,
    fontName: situationStyle ? "Cormorant Garamond" : nameStyle ? "Roboto Condensed" : "Archivo Black",
    fontPath: situationStyle ? FONT.situation : nameStyle ? FONT.name : FONT.main,
    bold: !situationStyle,
    italic: nameStyle,
    lineSpacing: situationStyle ? 0.10 : 0.055,
    letterSpacing: situationStyle ? 0.016 : nameStyle ? -0.018 : -0.012,
    maxWidth: nameStyle ? 0.71 : situationStyle ? 0.74 : 0.72,
    shadowAlpha: situationStyle ? 0.78 : 0.90,
    shadowDistance: situationStyle ? 2.2 : 3.2,
    shadowSmoothing: situationStyle ? 0.46 : 0.24,
    borderWidth: situationStyle ? 0.042 : nameStyle ? 0.075 : 0.085,
    y: nameStyle ? -0.61 : situationStyle ? -0.575 : -0.605,
    styleName: nameStyle ? "USER_REFERENCE_NAME_V5_MOBILE" : situationStyle ? "USER_REFERENCE_CONTEXT_V5_MOBILE" : "USER_REFERENCE_MAIN_V5_MOBILE",
  };
  applyStyle(seg, material, cfg);
  const intro = "fade-in";
  const introDurationUs = TENSION_CUES.has(cue) ? 150000 : 190000;
  const outroDurationUs = cue === 29 ? 240000 : 150000;
  fx.addTextAnim(draft, seg.id, { intro, outro: "fade-out", introDurationUs, outroDurationUs });
  fx.addKeyframes(draft, seg.id, [
    { property: "position_y", timeUs: 0, value: cfg.y - 0.012, easing: "ease-out" },
    { property: "position_y", timeUs: 220000, value: cfg.y, easing: "ease-out" },
  ]);
  animationPlan.push({ cue, track: "REVIEW_NARRATION", segment_id: seg.id, style: cfg.styleName, intro, intro_ms: introDurationUs / 1000, outro: "fade-out", outro_ms: outroDurationUs / 1000 });
  counts.review++; counts.animated_review++;
  if (nameStyle) counts.name_emphasis++; else if (situationStyle) counts.situation_narration++; else counts.main_narration++;
  if (highlight) counts.two_tone++;
}

const report = {
  schema_version: 1,
  project,
  dry_run: dryRun,
  reference_images: ["C:\\cineyoutube\\나레이션.png", "C:\\cineyoutube\\이름강조나레이션.png", "C:\\cineyoutube\\상황나레이션.png", "C:\\cineyoutube\\자막.png"],
  counts,
  safe_area: { dialogue_y: -0.78, review_y_range: [-0.61, -0.575], dialogue_max_width: 0.78, review_max_width_range: [0.71, 0.74], adaptive_font_size: true, max_font_size: 7.0, mobile_legibility: true },
  palette: PALETTE,
  line_layout: {
    explicit_two_line_materials: draft.materials.texts.filter((m) => JSON.parse(m.content).text.includes("\n")).length,
    max_display_line_chars: Math.max(...draft.materials.texts.flatMap((m) => JSON.parse(m.content).text.split("\n").map((line) => [...line].length))),
  },
  motion_detail: {
    native_animation_materials: draft.materials.material_animations.length,
    keyframed_review_segments: review.segments.filter((s) => (s.common_keyframes || []).length > 0).length,
    patterns: ["micro-rise", "fade-in", "fade-out"],
    restrained_motion: true,
    movie_dialogue_animated: false,
  },
  typography: { dialogue: "Pretendard Medium", main_narration: "Archivo Black", name_emphasis: "Roboto Condensed Bold Italic", situation_narration: "Cormorant Garamond Medium", user_reference_driven: true, top_level_style_flags: true },
  overflow_checks: { fixed_width_disabled: true, fixed_height_disabled: true, auto_adapt_canvas: true, force_line_max_width: true, oversized_materials: draft.materials.texts.filter((m) => Number(m.font_size) > 7.0).length },
  animation_plan: animationPlan,
};
if (!dryRun) lib.saveDraft(filePath, draft);
fs.mkdirSync(path.dirname(reportPath), { recursive: true });
fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + os.EOL, "utf8");
console.log(JSON.stringify(report, null, 2));
