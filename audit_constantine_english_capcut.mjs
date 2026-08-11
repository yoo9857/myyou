import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const project = "C:/Users/hanbi/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft/CONSTANTINE_STORY_REVIEW_V5";
const root = path.join(project, "draft_content.json");
const json = JSON.parse(fs.readFileSync(root, "utf8"));
const tracks = new Map((json.tracks ?? []).map((track) => [track.name, track]));
const texts = new Map((json.materials?.texts ?? []).map((material) => [material.id, material]));

function trackTexts(name) {
  return (tracks.get(name)?.segments ?? []).map((segment) => texts.get(segment.material_id)).filter(Boolean);
}

function payload(material) {
  try { return JSON.parse(material.content ?? "{}"); } catch { return {}; }
}

const movie = trackTexts("MOVIE_DIALOGUE");
const review = trackTexts("REVIEW_NARRATION");
const allPayloads = [...movie, ...review].map(payload);
const visibleTexts = allPayloads.map((item) => item.text ?? "");
const cue12 = payload(review[11]);
const mirrors = [root];
for (const timeline of fs.readdirSync(path.join(project, "Timelines"), { withFileTypes: true })) {
  if (!timeline.isDirectory()) continue;
  for (const name of ["draft_content.json", "template-2.tmp"]) {
    const candidate = path.join(project, "Timelines", timeline.name, name);
    if (fs.existsSync(candidate)) mirrors.push(candidate);
  }
}
const hashes = mirrors.map((file) => ({
  file,
  sha256: crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex"),
}));
const ranges = cue12.styles ?? cue12.text_styles ?? [];
const report = {
  movie_dialogue: movie.length,
  review_narration: review.length,
  hangul_remaining: visibleTexts.filter((text) => /[\u3131-\u318E\uAC00-\uD7A3]/u.test(text)).length,
  html_tags_remaining: visibleTexts.filter((text) => /<[^>]+>/u.test(text)).length,
  cue12_text: cue12.text,
  cue12_style_ranges: ranges.map((item) => ({ range: item.range, fill: item.fill?.content?.solid?.color ?? item.fill?.color ?? null })),
  expected_isabel_range: [9, 15],
  mirror_count: hashes.length,
  mirrors_identical: new Set(hashes.map((item) => item.sha256)).size === 1,
  hashes,
  native_animation_materials: json.materials?.material_animations?.length ?? 0,
  review_segments_with_keyframes: (tracks.get("REVIEW_NARRATION")?.segments ?? []).filter((segment) => Object.keys(segment.common_keyframes ?? {}).length > 0).length,
  movie_segments_with_animation_refs: (tracks.get("MOVIE_DIALOGUE")?.segments ?? []).filter((segment) => (segment.extra_material_refs ?? []).some((id) => (json.materials?.material_animations ?? []).some((animation) => animation.id === id))).length,
  font_families: [...new Set([...movie, ...review].map((material) => material.font_name))],
  missing_font_files: [...new Set([...movie, ...review].map((material) => material.font_path).filter((fontPath) => fontPath && !fs.existsSync(fontPath)))],
  oversized_materials: [...movie, ...review].filter((material) => Number(material.font_size) > 7.0).length,
  review_materials_with_top_level_bold_flag: review.filter((material) => typeof material.bold === "boolean").length,
  review_materials_with_top_level_italic_flag: review.filter((material) => typeof material.italic === "boolean").length,
};
fs.writeFileSync("C:/cineyoutube/Constantine/story_review_v5/output/CAPCUT_ENGLISH_FINAL_AUDIT.json", `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify(report, null, 2));
