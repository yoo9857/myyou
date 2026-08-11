import fs from "node:fs";
import path from "node:path";

const project = "C:/Users/hanbi/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft/CONSTANTINE_STORY_REVIEW_V5";
const bed = "C:/cineyoutube/Constantine/story_review_v5/output/constantine_story_review_v5_ducked_bed.mp4";
const assetDir = path.join(project, "assets", "video");
fs.mkdirSync(assetDir, { recursive: true });
const assetPath = path.join(assetDir, "constantine_story_review_v5_ducked_bed_v2.mp4");
if (!fs.existsSync(assetPath) || fs.statSync(assetPath).size !== fs.statSync(bed).size) {
  try { fs.linkSync(bed, assetPath); } catch { fs.copyFileSync(bed, assetPath); }
}

const contentPaths = [path.join(project, "draft_content.json")];
const timelines = path.join(project, "Timelines");
if (fs.existsSync(timelines)) {
  for (const entry of fs.readdirSync(timelines, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    for (const name of ["draft_content.json", "template-2.tmp"]) {
      const candidate = path.join(timelines, entry.name, name);
      if (fs.existsSync(candidate)) contentPaths.push(candidate);
    }
  }
}

const updated = [];
const updateTime = Math.floor(Date.now() * 1000);
for (const contentPath of contentPaths) {
  const content = JSON.parse(fs.readFileSync(contentPath, "utf8"));
  const videoTrack = (content.tracks ?? []).find((track) => track.type === "video");
  if (!videoTrack?.segments?.length) throw new Error(`CapCut video track is missing: ${contentPath}`);
  const videoMaterial = (content.materials?.videos ?? []).find(
    (material) => material.id === videoTrack.segments[0].material_id,
  ) ?? content.materials?.videos?.[0];
  if (!videoMaterial) throw new Error(`CapCut video material is missing: ${contentPath}`);
  videoMaterial.path = assetPath;
  videoMaterial.material_name = path.basename(assetPath);
  videoMaterial.has_audio = true;
  content.update_time = updateTime;
  const temp = `${contentPath}.audio_tmp`;
  fs.writeFileSync(temp, JSON.stringify(content), "utf8");
  fs.renameSync(temp, contentPath);
  updated.push(contentPath);
}

console.log(JSON.stringify({ project, bed_asset: assetPath, updated_mirrors: updated }, null, 2));
