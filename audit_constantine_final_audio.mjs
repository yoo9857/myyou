import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";

const project = "C:/Users/hanbi/AppData/Local/CapCut/User Data/Projects/com.lveditor.draft/CONSTANTINE_STORY_REVIEW_V5";
const output = "C:/cineyoutube/Constantine/story_review_v5/output";
const finalVideo = path.join(output, "constantine_story_review_v5_nayva_final.mp4");
const voiceStem = path.join(output, "constantine_nayva_voice_stem.wav");
const musicStem = path.join(output, "constantine_outro_music_stem.m4a");
const bedVideo = path.join(output, "constantine_story_review_v5_ducked_bed.mp4");
const expectedCapCutBed = "constantine_story_review_v5_ducked_bed_v2.mp4";
const root = path.join(project, "draft_content.json");
const draft = JSON.parse(fs.readFileSync(root, "utf8"));

function command(program, args) {
  const result = spawnSync(program, args, { encoding: "utf8" });
  return `${result.stdout ?? ""}\n${result.stderr ?? ""}`;
}

function probe(file) {
  return JSON.parse(command("ffprobe", ["-v", "error", "-show_entries", "format=duration,size", "-show_entries", "stream=index,codec_type,codec_name,sample_rate,channels", "-of", "json", file]));
}

function volume(file, start, duration, mapAudio = false) {
  const args = ["-hide_banner", "-nostats", "-ss", String(start), "-t", String(duration), "-i", file];
  if (mapAudio) args.push("-map", "0:a:0");
  args.push("-af", "volumedetect", "-f", "null", "NUL");
  const text = command("ffmpeg", args);
  const mean = [...text.matchAll(/mean_volume:\s*(-?[\d.]+) dB/g)].at(-1);
  const max = [...text.matchAll(/max_volume:\s*(-?[\d.]+) dB/g)].at(-1);
  return { mean_db: mean ? Number(mean[1]) : null, max_db: max ? Number(max[1]) : null };
}

const loudnessText = command("ffmpeg", ["-hide_banner", "-nostats", "-i", finalVideo, "-map", "0:a:0", "-af", "ebur128=peak=true:framelog=verbose", "-f", "null", "NUL"]);
const integratedMatches = [...loudnessText.matchAll(/I:\s*(-?[\d.]+) LUFS/g)];
const peakMatches = [...loudnessText.matchAll(/Peak:\s*(-?[\d.]+) dBFS/g)];
const middleVoice = volume(voiceStem, 601, 3, false);
const middleBed = volume(bedVideo, 601, 3, true);
const outroMusic = volume(musicStem, 0, 14, false);

const tracks = Object.fromEntries((draft.tracks ?? []).map((track) => [track.name, track]));
const audioById = new Map((draft.materials?.audios ?? []).map((material) => [material.id, material]));
const audioTracks = ["REVIEW_VOICE", "OUTRO_MUSIC"].map((name) => {
  const track = tracks[name];
  const segment = track?.segments?.[0];
  const material = segment ? audioById.get(segment.material_id) : null;
  return {
    name,
    segments: track?.segments?.length ?? 0,
    start_sec: segment ? segment.target_timerange.start / 1e6 : null,
    duration_sec: segment ? segment.target_timerange.duration / 1e6 : null,
    file: material?.path ?? null,
    file_exists: Boolean(material?.path && fs.existsSync(material.path)),
  };
});

const mirrorFiles = [root];
for (const entry of fs.readdirSync(path.join(project, "Timelines"), { withFileTypes: true })) {
  if (!entry.isDirectory()) continue;
  for (const name of ["draft_content.json", "template-2.tmp"]) {
    const candidate = path.join(project, "Timelines", entry.name, name);
    if (fs.existsSync(candidate)) mirrorFiles.push(candidate);
  }
}
const hashes = mirrorFiles.map((file) => crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex"));
const finalProbe = probe(finalVideo);
const videoMaterial = (draft.materials?.videos ?? [])[0];
const report = {
  schema_version: 1,
  final_video: finalVideo,
  final_exists: fs.existsSync(finalVideo),
  final_duration_sec: Number(finalProbe.format.duration),
  final_size_bytes: Number(finalProbe.format.size),
  final_streams: finalProbe.streams,
  final_integrated_lufs: integratedMatches.length ? Number(integratedMatches.at(-1)[1]) : null,
  final_true_peak_dbfs: peakMatches.length ? Number(peakMatches.at(-1)[1]) : null,
  middle_voice_mean_db: middleVoice.mean_db,
  middle_bed_mean_db: middleBed.mean_db,
  middle_voice_margin_db: middleVoice.mean_db !== null && middleBed.mean_db !== null ? Number((middleVoice.mean_db - middleBed.mean_db).toFixed(1)) : null,
  outro_music_mean_db: outroMusic.mean_db,
  outro_music_max_db: outroMusic.max_db,
  capcut_video_asset: videoMaterial?.path ?? null,
  capcut_uses_ducked_bed: Boolean(videoMaterial?.path?.endsWith(expectedCapCutBed)),
  audio_tracks: audioTracks,
  movie_dialogue_segments: tracks.MOVIE_DIALOGUE?.segments?.length ?? 0,
  review_narration_segments: tracks.REVIEW_NARRATION?.segments?.length ?? 0,
  timeline_mirror_count: mirrorFiles.length,
  timeline_mirrors_identical: new Set(hashes).size === 1,
  audio_gate_pass: audioTracks.every((track) => track.segments === 1 && track.file_exists)
    && Boolean(videoMaterial?.path?.endsWith(expectedCapCutBed))
    && Number(finalProbe.format.duration) > 1501
    && (peakMatches.length ? Number(peakMatches.at(-1)[1]) <= -0.8 : false)
    && (middleVoice.mean_db !== null && middleBed.mean_db !== null ? middleVoice.mean_db - middleBed.mean_db >= 4 : false)
    && (outroMusic.mean_db !== null && outroMusic.max_db !== null ? outroMusic.mean_db >= -30 && outroMusic.max_db >= -12 : false)
    && new Set(hashes).size === 1,
};
const reportPath = path.join(output, "CAPCUT_FINAL_AUDIO_QA.json");
fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify(report, null, 2));
