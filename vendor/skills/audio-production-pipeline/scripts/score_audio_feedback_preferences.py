#!/usr/bin/env python3
"""Score audio candidates with planner feedback preferences.

First-stage implementation:
- Uses local feedback CSV from the review page.
- Extracts lightweight WAV features for best/miss samples.
- Builds per-asset preference centroids.
- Adds quality_score, feedback_score, and final_score to review manifests.

CLAP is intentionally optional here. If --semantic-model clap is requested but
the local model stack is missing, the script falls back to existing rule scores.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from workspace_paths import find_workspace_root


ROOT = find_workspace_root()
CACHE_ROOT = ROOT / ".cache" / "semantic_audio"

FEATURE_KEYS = [
    "duration_sec",
    "rms",
    "peak",
    "crest",
    "zero_crossing_rate",
    "attack_ratio",
    "tail_ratio",
    "high_motion_ratio",
]


@dataclass
class FeatureVector:
    values: dict[str, float]

    def distance(self, other: "FeatureVector") -> float:
        total = 0.0
        count = 0
        for key in FEATURE_KEYS:
            if key not in self.values or key not in other.values:
                continue
            total += (self.values[key] - other.values[key]) ** 2
            count += 1
        return math.sqrt(total / count) if count else 1.0


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def project_path(value: str) -> Path:
    text = (value or "").strip()
    if not text:
        return Path()
    path = Path(text)
    if path.is_absolute():
        return path
    return ROOT / text.lstrip("/")


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def read_wav_mono(path: Path) -> tuple[int, list[float]]:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        sample_rate = handle.getframerate()
        raw = handle.readframes(handle.getnframes())
    if sample_width != 2:
        raise ValueError(f"Only 16-bit WAV is supported for feature extraction: {path.name}")
    samples: list[float] = []
    step = sample_width * channels
    for offset in range(0, len(raw), step):
        if channels == 1:
            value = int.from_bytes(raw[offset : offset + 2], "little", signed=True)
        else:
            total = 0
            for channel in range(channels):
                start = offset + channel * 2
                total += int.from_bytes(raw[start : start + 2], "little", signed=True)
            value = int(total / channels)
        samples.append(value / 32768.0)
    return sample_rate, samples


def extract_wav_features(path: Path) -> FeatureVector | None:
    if not path.exists() or path.suffix.lower() != ".wav":
        return None
    try:
        sample_rate, samples = read_wav_mono(path)
    except Exception:
        return None
    if not samples or sample_rate <= 0:
        return None
    abs_samples = [abs(value) for value in samples]
    duration = len(samples) / sample_rate
    rms = math.sqrt(sum(value * value for value in samples) / len(samples))
    peak = max(abs_samples) if abs_samples else 0.0
    crest = peak / (rms + 1e-6)
    crossings = sum(1 for a, b in zip(samples, samples[1:]) if (a >= 0) != (b >= 0))
    zero_crossing_rate = crossings / max(1, len(samples) - 1)
    high_motion = sum(abs(b - a) for a, b in zip(samples, samples[1:])) / max(1, len(samples) - 1)
    frame = max(1, int(sample_rate * 0.025))
    energies = [
        math.sqrt(sum(value * value for value in samples[i : i + frame]) / max(1, len(samples[i : i + frame])))
        for i in range(0, len(samples), frame)
    ]
    max_energy = max(energies) if energies else 0.0
    threshold = max_energy * 0.25
    first_loud = next((index for index, energy in enumerate(energies) if energy >= threshold), 0)
    tail_frames = max(1, int(0.25 / 0.025))
    tail_energy = sum(energies[-tail_frames:]) / min(tail_frames, len(energies)) if energies else 0.0
    attack_ratio = first_loud / max(1, len(energies) - 1)
    tail_ratio = tail_energy / (max_energy + 1e-6)
    return FeatureVector(
        {
            "duration_sec": min(duration / 3.0, 1.0),
            "rms": min(rms / 0.25, 1.0),
            "peak": peak,
            "crest": min(crest / 12.0, 1.0),
            "zero_crossing_rate": min(zero_crossing_rate / 0.18, 1.0),
            "attack_ratio": min(attack_ratio, 1.0),
            "tail_ratio": min(tail_ratio, 1.0),
            "high_motion_ratio": min(high_motion / 0.12, 1.0),
        }
    )


def average_feature(vectors: Iterable[FeatureVector]) -> FeatureVector | None:
    vectors = list(vectors)
    if not vectors:
        return None
    values: dict[str, float] = {}
    for key in FEATURE_KEYS:
        present = [vector.values[key] for vector in vectors if key in vector.values]
        if present:
            values[key] = sum(present) / len(present)
    return FeatureVector(values) if values else None


def quality_score(features: FeatureVector | None, duration_hint: float = 0.0) -> float:
    if features is None:
        duration = duration_hint
        if not duration:
            return 58.0
        duration_penalty = max(0.0, min(35.0, abs(duration - 1.0) * 18.0))
        return clamp_score(78.0 - duration_penalty)
    v = features.values
    duration = v.get("duration_sec", 0.3) * 3.0
    score = 82.0
    if duration < 0.25:
        score -= 15.0
    if duration > 2.2:
        score -= min(22.0, (duration - 2.2) * 14.0)
    score -= max(0.0, v.get("tail_ratio", 0.0) - 0.55) * 22.0
    score -= max(0.0, v.get("peak", 0.0) - 0.96) * 35.0
    score -= max(0.0, v.get("high_motion_ratio", 0.0) - 0.74) * 18.0
    score += max(0.0, 0.32 - v.get("attack_ratio", 0.0)) * 10.0
    return clamp_score(score)


def preference_score(features: FeatureVector | None, liked: FeatureVector | None, missed: FeatureVector | None) -> float:
    if features is None or (liked is None and missed is None):
        return 50.0
    score = 50.0
    if liked is not None:
        score += (1.0 - min(1.0, features.distance(liked))) * 32.0
    if missed is not None:
        score -= (1.0 - min(1.0, features.distance(missed))) * 28.0
    return clamp_score(score)


def load_semantic_scores(args: argparse.Namespace, manifest: list[dict[str, object]]) -> dict[str, float]:
    if args.semantic_model in ("", "none"):
        return {}
    if args.semantic_model != "clap":
        raise SystemExit(f"Unsupported semantic model: {args.semantic_model}")
    try:
        import laion_clap  # type: ignore  # noqa: F401
    except Exception as exc:
        print(f"CLAP unavailable, falling back to rule scores: {exc}")
        return {}
    print("CLAP package is installed, but embedding inference is not wired in this first-stage script yet.")
    return {}


def build_feedback_profiles(feedback_rows: list[dict[str, str]]) -> dict[str, dict[str, object]]:
    grouped: dict[str, dict[str, list[FeatureVector]]] = {}
    for row in feedback_rows:
        asset = row.get("asset_name", "").strip()
        feedback = row.get("feedback", "").strip()
        if not asset or feedback not in {"best", "miss", "usable", "edit"}:
            continue
        features = extract_wav_features(project_path(row.get("source_path", "")))
        if features is None:
            continue
        bucket = "best" if feedback in {"best", "usable"} else "miss"
        grouped.setdefault(asset, {"best": [], "miss": []})[bucket].append(features)
    profiles: dict[str, dict[str, object]] = {}
    for asset, buckets in grouped.items():
        liked = average_feature(buckets.get("best", []))
        missed = average_feature(buckets.get("miss", []))
        profiles[asset] = {
            "best_count": len(buckets.get("best", [])),
            "miss_count": len(buckets.get("miss", [])),
            "best_center": liked.values if liked else {},
            "miss_center": missed.values if missed else {},
        }
    return profiles


def feature_from_profile(values: object) -> FeatureVector | None:
    if not isinstance(values, dict) or not values:
        return None
    return FeatureVector({str(key): safe_float(value) for key, value in values.items()})


def score_candidate(
    item: dict[str, object],
    candidate: dict[str, object],
    profiles: dict[str, dict[str, object]],
    semantic_scores: dict[str, float],
) -> dict[str, object]:
    candidate_id = str(candidate.get("candidate_id", ""))
    local_path = str(candidate.get("local_preview_url") or "").replace("../", "")
    features = extract_wav_features(project_path(local_path))
    q_score = quality_score(features, safe_float(candidate.get("duration_sec")))
    profile = profiles.get(str(item.get("asset_name", "")), {})
    liked = feature_from_profile(profile.get("best_center"))
    missed = feature_from_profile(profile.get("miss_center"))
    f_score = preference_score(features, liked, missed)
    rule_score = safe_float(candidate.get("match_score"), 50.0)
    semantic_score = semantic_scores.get(candidate_id, rule_score)
    final = (semantic_score * 0.55) + (q_score * 0.15) + (rule_score * 0.15) + (f_score * 0.15)
    updated = dict(candidate)
    updated.update(
        {
            "semantic_score": round(semantic_score, 1),
            "rule_match_score": round(rule_score, 1),
            "quality_score": round(q_score, 1),
            "feedback_score": round(f_score, 1),
            "final_score": round(clamp_score(final), 1),
            "feedback_profile_best_count": profile.get("best_count", 0),
            "feedback_profile_miss_count": profile.get("miss_count", 0),
        }
    )
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply feedback preference scoring to audio candidates.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--feedback", type=Path, required=True)
    parser.add_argument("--output-manifest", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--semantic-model", choices=["none", "clap"], default="none")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    feedback_rows = read_csv(args.feedback)
    profiles = build_feedback_profiles(feedback_rows)
    semantic_scores = load_semantic_scores(args, manifest)

    scored_manifest: list[dict[str, object]] = []
    csv_rows: list[dict[str, object]] = []
    for item in manifest:
        updated_item = dict(item)
        scored_candidates = [
            score_candidate(item, candidate, profiles, semantic_scores)
            for candidate in item.get("candidates", [])
        ]
        scored_candidates.sort(key=lambda row: safe_float(row.get("final_score")), reverse=True)
        updated_item["candidates"] = scored_candidates
        scored_manifest.append(updated_item)
        for candidate in scored_candidates:
            csv_rows.append(
                {
                    "request_id": item.get("request_id", ""),
                    "asset_name": item.get("asset_name", ""),
                    "event_name": item.get("event_name", ""),
                    "candidate_id": candidate.get("candidate_id", ""),
                    "filename": candidate.get("filename", ""),
                    "semantic_score": candidate.get("semantic_score", ""),
                    "rule_match_score": candidate.get("rule_match_score", ""),
                    "quality_score": candidate.get("quality_score", ""),
                    "feedback_score": candidate.get("feedback_score", ""),
                    "final_score": candidate.get("final_score", ""),
                    "duration_sec": candidate.get("duration_sec", ""),
                    "local_preview_url": candidate.get("local_preview_url", ""),
                    "match_reasons": candidate.get("match_reasons", ""),
                    "mismatch_reasons": candidate.get("mismatch_reasons", ""),
                }
            )

    args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.output_manifest.write_text(json.dumps(scored_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(
        args.output_csv,
        csv_rows,
        [
            "request_id",
            "asset_name",
            "event_name",
            "candidate_id",
            "filename",
            "semantic_score",
            "rule_match_score",
            "quality_score",
            "feedback_score",
            "final_score",
            "duration_sec",
            "local_preview_url",
            "match_reasons",
            "mismatch_reasons",
        ],
    )
    args.profiles.parent.mkdir(parents=True, exist_ok=True)
    args.profiles.write_text(json.dumps(profiles, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Feedback rows: {len(feedback_rows)}")
    print(f"Profiles: {len(profiles)}")
    print(f"Scored candidates: {len(csv_rows)}")
    print(f"Wrote {args.output_manifest}")
    print(f"Wrote {args.output_csv}")
    print(f"Wrote {args.profiles}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
