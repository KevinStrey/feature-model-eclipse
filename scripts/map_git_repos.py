import json
import os
import subprocess
import re
import datetime
from collections import Counter

# ─── Dynamic base_dir: works on both Windows and Linux ───────────────────────
# Script lives at: <base_dir>/feature-model-eclipse/scripts/map_git_repos.py
_script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.normpath(os.path.join(_script_dir, "..", ".."))

json_dir = os.path.join(base_dir, "releases", "dados-features")
out_dir  = os.path.join(base_dir, "releases", "mappings")
os.makedirs(out_dir, exist_ok=True)

# ─── Repository mapping ───────────────────────────────────────────────────────
repo_map = {
    "JDT":          ["eclipse.jdt.core"],
    "PDE":          ["eclipse.pde"],
    "CDT":          ["cdt"],
    "GEF":          ["gef-classic", "gef"],
    "EMF":          ["org.eclipse.emf"],
    "BIRT":         ["birt"],
    "DATATOOLS":    ["datatools"],
    "ECLIPSELINK":  ["eclipselink"],
    "EGIT":         ["egit"],
    "GMF":          ["gmf-runtime"],
    "MYLYN":        ["org.eclipse.mylyn"],
    "RAP":          ["org.eclipse.rap"],
    "PTP":          ["ptp"],
    "SCOUT":        ["scout.rt"],
    "WEBTOOLS":     ["webtools.javaee"],
    "WINDOWBUILDER":["windowbuilder"],
    "MAVEN":        ["m2e-core"],
}

target_features = list(repo_map.keys())

# ─── Release date upper bounds ────────────────────────────────────────────────
# Used to:
#   (a) sanity-check H0 timestamps (reject if version is >H0_MAX_AGE_DAYS old)
#   (b) constrain H2 Pickaxe so it won't pick commits from future releases
RELEASE_DATE_BOUNDS = {
    "JunoSR0":        "2012-07-15",
    "JunoSR1":        "2012-11-01",
    "JunoSR2":        "2013-03-01",
    "KeplerPostRC4":  "2013-07-01",
    "KeplerSR0":      "2013-08-01",
    "KeplerSR1":      "2013-11-01",
    "LunaSR0":        "2014-07-15",
    "z20140805-2300": "2014-08-20",
    "z20140806":      "2014-08-20",
    "LunaRC4":        "2014-07-01",
    "LunaSR2":        "2015-03-01",
    "S201504150911":  "2015-05-01",
    "Mars.1":         "2015-11-01",
    "Neon":           "2016-07-15",
    "OxygenPreRienaRemoval_9-8-2016": "2016-09-20",
    "Neon.1":         "2016-10-01",
    "Neon.1a":        "2016-10-15",
    "Neon.2":         "2017-03-01",
    "Neon.3":         "2017-07-01",
    "Neon.3_respin":  "2017-07-15",
    "Oxygen":         "2017-07-15",
    "Oxygen.1":       "2017-10-15",
    "Oxygen.1a_respin":"2017-10-25",
    "Oxygen.1a":      "2017-11-01",
    "Oxygen.2":       "2018-03-01",
    "Oxygen.2_respin":"2018-03-15",
    "Oxygen.3":       "2018-04-01",
    "PhotonM7":       "2018-06-20",
    "PhotonRC4":      "2018-06-25",
    "Photon.0":       "2018-07-15",
    "2018-09":        "2018-10-01",
    "2018-12":        "2019-01-01",
    "2019-03":        "2019-04-01",
    "2019-06":        "2019-07-01",
    "2019-09":        "2019-10-01",
    "2019-12":        "2020-01-01",
    "2020-03":        "2020-04-01",
    "2020-06":        "2020-07-01",
    "2020-09":        "2020-10-01",
    "2020-12":        "2021-01-01",
    "2021-03":        "2021-04-01",
    "2021-06":        "2021-07-01",
    "2021-09":        "2021-10-01",
    "2021-12":        "2022-01-01",
    "2022-03":        "2022-04-01",
    "2022-06":        "2022-07-01",
    "2022-09":        "2022-10-01",
    "2022-12":        "2023-01-01",
    "2023-03":        "2023-04-01",
    "2023-06":        "2023-07-01",
    "2023-09":        "2023-10-01",
    "2023-12":        "2024-01-01",
    "2024-03":        "2024-04-01",
    "2024-06":        "2024-07-01",
    "2024-09":        "2024-10-01",
    "2024-12":        "2025-01-01",
    "2025-03":        "2025-04-01",
    "2025-06":        "2025-07-01",
    "2025-09":        "2025-10-01",
    "2025-12":        "2026-01-01",
    "2026-03":        "2026-04-01",
}

# ─── Version overrides ────────────────────────────────────────────────────────
# Corrects wrong versions recorded in dados-features before any heuristic runs.
# CDT: simrel b3aggrcon referenced CDT 8.0.x (Indigo), but Juno shipped 8.1.x.
VERSION_OVERRIDES = {
    ("CDT", "JunoSR0"): "8.1.0",
    ("CDT", "JunoSR1"): "8.1.1",
    ("CDT", "JunoSR2"): "8.1.2",
}

# Max age (days) between version timestamp and release date for H0 to be valid.
# Rejects Indigo 2011 commits being used for Juno 2012 releases.
H0_MAX_AGE_DAYS = 180

# ─── Heuristic weights for voting ────────────────────────────────────────────
# Higher = more trustworthy signal.
# H0b and H1_EXACT are the most reliable because they match the tag directly.
# H0 (timestamp) is reliable but can be fooled by --all.
# H4 (maintenance branch) is reliable for repos without tags.
# H2 (pickaxe) can still be wrong even with a date bound, so gets lower weight.
HEURISTIC_WEIGHTS = {
    "H0b":       10,  # tag name contains exact timestamp → near-perfect
    "H1_EXACT":  10,  # tag version == version string exactly
    "H1_SR":      9,  # SR-specific tag (e.g. R4_2_1 for JunoSR1)
    "H1_LOOSE":   7,  # version digits + "release" in tag name
    "H1_PARTIAL": 6,  # partial version match (e.g. major.minor without patch)
    "H4":         8,  # maintenance branch with timestamp
    "H0":         6,  # timestamp time-travel (branch-restricted)
    "H2":         4,  # pickaxe (date-bounded, oldest-first)
    "H3":         5,  # release-train tag
}

# Minimum total weight to accept a voted result without UNCERTAIN flag.
VOTE_CONFIDENT_THRESHOLD = 6


# ─── Git helpers ──────────────────────────────────────────────────────────────
def run_git(cmd, cwd):
    try:
        result = subprocess.run(
            ["git"] + cmd, cwd=cwd,
            capture_output=True, text=True, check=True, timeout=30
        )
        return result.stdout.strip().split('\n')
    except subprocess.TimeoutExpired:
        print(f"    [git timeout] {cmd}", flush=True)
        return []
    except Exception:
        return []


def get_commit(ref, cwd):
    res = run_git(["rev-list", "-n", "1", ref], cwd)
    return res[0] if res and res[0] else None


def get_commit_date(commit, cwd):
    """Return author date of commit as datetime, or None."""
    res = run_git(["log", "-1", "--format=%ai", commit], cwd)
    if not res or not res[0]:
        return None
    try:
        return datetime.datetime.fromisoformat(res[0].strip()[:19])
    except Exception:
        return None


# ─── Individual heuristics (each returns a list of (commit, heuristic_id, weight, description, matched_value)) ──

def h0b_tag_timestamp(version, repo_dir):
    """Tag whose name contains the 12-digit version timestamp (e.g. EGIT tags)."""
    match = re.search(r'\.(\d{12})$', version)
    if not match:
        return []
    ts = match.group(1)
    tags = run_git(["tag"], cwd=repo_dir)
    results = []
    for t in (tags or []):
        if ts in t:
            commit = get_commit(t, repo_dir)
            if commit:
                results.append((commit, "H0b", HEURISTIC_WEIGHTS["H0b"],
                                 "Tag with Timestamp in Name", t))
    return results


def h0_timestamp(version, repo_dir, release_name=None):
    """Timestamp time-travel: find last commit before the version timestamp."""
    match = re.search(r'\.(\d{12})$', version)
    if not match:
        return []
    ts = match.group(1)
    dt_str = f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}:00"

    # Sanity check: reject if version timestamp is too old for this release
    if release_name and release_name in RELEASE_DATE_BOUNDS:
        try:
            version_dt = datetime.datetime(int(ts[0:4]), int(ts[4:6]), int(ts[6:8]))
            release_dt = datetime.datetime.strptime(RELEASE_DATE_BOUNDS[release_name], "%Y-%m-%d")
            age_days = (release_dt - version_dt).days
            if age_days > H0_MAX_AGE_DAYS:
                print(f"    [H0 SKIP] timestamp {dt_str} is {age_days}d before "
                      f"release bound (max {H0_MAX_AGE_DAYS}d)", flush=True)
                return []
        except ValueError:
            pass

    results = []
    # Prefer branch-restricted (avoids stray doc/dev commits)
    res = run_git(["log", f"--until={dt_str}", "--format=%H", "-1", "--branches"], cwd=repo_dir)
    if res and res[0]:
        results.append((res[0], "H0", HEURISTIC_WEIGHTS["H0"],
                         "Timestamp Time-Travel (--branches)", dt_str))

    # Also collect from --all (may be different; lower weight since includes any ref)
    res2 = run_git(["log", f"--until={dt_str}", "--format=%H", "-1", "--all"], cwd=repo_dir)
    if res2 and res2[0] and (not results or res2[0] != results[0][0]):
        # Only add if different from --branches result
        results.append((res2[0], "H0", max(HEURISTIC_WEIGHTS["H0"] - 2, 1),
                         "Timestamp Time-Travel (--all)", dt_str))
    return results


def h1_tags(version, repo_dir, release_name=None):
    """
    Fuzzy tag matching — now returns ALL plausible tag matches with weights,
    not just the first match. SR-specific tags get higher weight than generic ones.
    Also handles RAP-style (major.minor.patch-YYYYMMDD) and PTP-style (PTP_x_y_z).
    """
    tags = run_git(["tag"], cwd=repo_dir)
    if not tags or tags == ['']:
        return []

    clean_v = re.sub(r'\.\d{12}$', '', version)
    parts = clean_v.split('.')
    if len(parts) < 2:
        return []

    major, minor = parts[0], parts[1]
    patch = parts[2] if len(parts) > 2 else "0"

    # Determine SR number
    sr_num = 0
    if release_name:
        sr_match = re.search(r'SR(\d+)$', release_name, re.IGNORECASE)
        if sr_match:
            sr_num = int(sr_match.group(1))

    results = []
    seen_commits = set()

    def _add(tag, weight, label):
        commit = get_commit(tag, repo_dir)
        if commit and commit not in seen_commits:
            seen_commits.add(commit)
            results.append((commit, "H1", weight, label, tag))

    # Tier 1: exact version match (highest confidence)
    exact_candidates = [
        f"v{major}.{minor}.{patch}", f"v{major}.{minor}.{patch}.0",
        f"R{major}_{minor}_{patch}",
        f"{major}.{minor}.{patch}",
        f"CDT_{major}_{minor}_{patch}",
        f"PTP_{major}_{minor}_{patch}",
        f"R_{major}_{minor}_{patch}",
        clean_v, version,
    ]
    # RAP-style: major.minor.patch-YYYYMMDD → match by version prefix
    # (e.g. "1.5.0" matches "1.5.0-20120612")
    exact_lower = [c.lower() for c in exact_candidates]
    for t in tags:
        tl = t.lower()
        # Exact match
        if tl in exact_lower or tl == f"v{clean_v.lower()}":
            _add(t, HEURISTIC_WEIGHTS["H1_EXACT"], "H1 exact tag")
            continue
        # RAP/SCOUT-style: tag starts with version and has date suffix
        for c in [f"{major}.{minor}.{patch}-", f"{major}.{minor}.{patch}_S-"]:
            if tl.startswith(c.lower()):
                _add(t, HEURISTIC_WEIGHTS["H1_EXACT"] - 1,
                     f"H1 exact-with-date-suffix tag")
                break
        # SCOUT/DATATOOLS date-prefixed: "YYYY-MM-DD_S-3.8.0" — match by version in suffix
        if f"_s-{major}.{minor}.{patch}" in tl or f"-{major}.{minor}.{patch}" == tl[-len(f"-{major}.{minor}.{patch}"):]:
            _add(t, HEURISTIC_WEIGHTS["H1_EXACT"] - 1,
                 "H1 date-prefixed tag (version in suffix)")

    # Tier 2: SR-specific tag (e.g. R4_2_1 for JunoSR1 when version is "4.2")
    if sr_num > 0:
        sr_candidates = [
            f"R{major}_{minor}_{sr_num}",
            f"v{major}.{minor}.{sr_num}",
            f"v{major}.{minor}.{sr_num}.0",
            f"{major}.{minor}.{sr_num}",
            f"CDT_{major}_{minor}_{sr_num}",
            f"PTP_{major}_{minor}_{sr_num}",
            f"R_{major}_{minor}_{sr_num}",
        ]
        sr_lower = [c.lower() for c in sr_candidates]
        for t in tags:
            if t.lower() in sr_lower:
                _add(t, HEURISTIC_WEIGHTS["H1_SR"], "H1 SR-specific tag")

    # Tier 3: partial match (major.minor only, no patch)
    partial_candidates = [
        f"v{major}.{minor}", f"R{major}_{minor}",
        f"CDT_{major}_{minor}", f"PTP_{major}_{minor}", f"R_{major}_{minor}",
        f"{major}.{minor}",
    ]
    partial_lower = [c.lower() for c in partial_candidates]
    for t in tags:
        if t.lower() in partial_lower:
            _add(t, HEURISTIC_WEIGHTS["H1_PARTIAL"], "H1 partial tag (major.minor)")

    # Tier 4: loose match — tag contains version digits + the word "release"
    # (BIRT_4_2_0_Release_YYYYMMDDHHMM, DTP_1_10_0_Release_...)
    v_digits = re.sub(r'\D', '', f"{major}{minor}{patch}")
    for t in tags:
        if v_digits in re.sub(r'\D', '', t) and 'release' in t.lower():
            _add(t, HEURISTIC_WEIGHTS["H1_LOOSE"], "H1 loose tag (digits+release)")

    return results


def h2_pickaxe(version, repo_dir, release_name=None):
    """Date-bounded Pickaxe: finds the OLDEST commit introducing the version string."""
    clean_v = re.sub(r'\.\d{12}$', '', version)
    until_args = []
    if release_name and release_name in RELEASE_DATE_BOUNDS:
        until_args = [f"--until={RELEASE_DATE_BOUNDS[release_name]}"]

    results = []
    seen = set()
    for search_str in [
        f"Bundle-Version: {clean_v}",
        f"<version>{clean_v}</version>",
        f"<version>{clean_v}.0</version>",
        f"<version>{clean_v}.qualifier</version>",
    ]:
        res = run_git(
            ["log", "-S", search_str, "--format=%H"] + until_args + ["--all", "--reverse", "-1"],
            cwd=repo_dir
        )
        if res and res[0] and res[0] not in seen:
            seen.add(res[0])
            results.append((res[0], "H2", HEURISTIC_WEIGHTS["H2"],
                             "Pickaxe (date-bounded, oldest-first)", search_str))
    return results


def h3_train_tags(release_name, repo_dir):
    """Matches repos that use the Eclipse release-train name as their tag."""
    tags = run_git(["tag"], cwd=repo_dir)
    if not tags or tags == ['']:
        return []

    _ALIAS = {
        "neon":    ["Neon", "neon_R", "R4_6"],
        "oxygen":  ["Oxygen", "oxygen_R", "R4_7"],
        "2018-09": ["simrel-2018-09", "2018-09", "R4_9"],
        "2026-03": ["simrel-2026-03", "2026-03", "R4_39"],
    }
    aliases = [release_name] + _ALIAS.get(release_name.lower(), [])

    results = []
    for alias in aliases:
        for t in tags:
            if t.lower() == alias.lower() or t.lower() == f"v{alias.lower()}":
                commit = get_commit(t, repo_dir)
                if commit:
                    results.append((commit, "H3", HEURISTIC_WEIGHTS["H3"],
                                    "Release Train Tagging", t))
    return results


def h4_maintenance_branch(version, repo_dir, release_name=None):
    """Maintenance-branch time-travel for repos without release tags (e.g. GEF)."""
    clean_v = re.sub(r'\.\d{12}$', '', version)
    parts = clean_v.split('.')
    if len(parts) < 2:
        return []
    major, minor = parts[0], parts[1]

    dt_str = None
    match = re.search(r'\.(\d{12})$', version)
    if match:
        ts = match.group(1)
        dt_str = f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}:00"
    elif release_name and release_name in RELEASE_DATE_BOUNDS:
        dt_str = RELEASE_DATE_BOUNDS[release_name]

    if not dt_str:
        return []

    results = []
    seen = set()
    for branch in [
        f"R{major}_{minor}_maintenance",
        f"R{major}_{minor}_x_maintenance",
        f"maintenance/{major}.{minor}",
        f"maintenance-{major}.{minor}",
        f"stable-{major}.{minor}",
        f"release/{major}.{minor}",
    ]:
        for ref in [branch, f"origin/{branch}"]:
            exists = run_git(["rev-parse", "--verify", ref], cwd=repo_dir)
            if not exists or not exists[0]:
                continue
            res = run_git(["log", ref, f"--until={dt_str}", "--format=%H", "-1"], cwd=repo_dir)
            if res and res[0] and res[0] not in seen:
                seen.add(res[0])
                results.append((res[0], "H4", HEURISTIC_WEIGHTS["H4"],
                                 f"Maintenance Branch Time-Travel ({ref})", ref))
    return results


# ─── Voting / ensemble engine ─────────────────────────────────────────────────
def vote(candidates, release_name=None, repo_dir=None):
    """
    Aggregate all candidate (commit, heuristic, weight, description, matched_value)
    tuples and pick the winner by total accumulated weight.

    Tie-breaking:
    1. Highest total weight wins.
    2. If tied, pick the candidate whose commit date is closest to (and before)
       the release date upper bound.
    3. If still tied, prefer the candidate from the highest-weight single vote.

    Returns a dict with all voting metadata included.
    """
    if not candidates:
        return None

    # Accumulate weight per commit
    commit_weight  = Counter()
    commit_meta    = {}   # commit → (heuristic_id, description, matched_value)
    commit_sources = {}   # commit → list of heuristic names

    for (commit, h_id, weight, desc, matched) in candidates:
        commit_weight[commit] += weight
        commit_sources.setdefault(commit, []).append(f"{h_id}({weight})")
        if commit not in commit_meta or weight > commit_meta[commit][2]:
            commit_meta[commit] = (h_id, desc, weight, matched)

    # Sort by total weight desc, then by commit date proximity to release bound
    def sort_key(c):
        total_w = commit_weight[c]
        proximity = 0
        if repo_dir and release_name and release_name in RELEASE_DATE_BOUNDS:
            cd = get_commit_date(c, repo_dir)
            if cd:
                bound = datetime.datetime.strptime(RELEASE_DATE_BOUNDS[release_name], "%Y-%m-%d")
                delta = (bound - cd).days
                # Negative means commit is after bound (penalise)
                proximity = delta if delta >= 0 else -9999
        return (total_w, proximity)

    sorted_commits = sorted(commit_weight.keys(), key=sort_key, reverse=True)
    winner = sorted_commits[0]

    h_id, desc, _, matched = commit_meta[winner]
    total_w = commit_weight[winner]
    sources_str = " + ".join(commit_sources[winner])
    confident = total_w >= VOTE_CONFIDENT_THRESHOLD

    return {
        "commit":               winner,
        "heuristic_id":         h_id,
        "heuristic_description":f"VOTE({sources_str}): {desc}",
        "matched_value":        matched,
        "vote_total_weight":    total_w,
        "vote_confident":       confident,
        "vote_candidates":      len(commit_weight),
    }


# ─── Main processing loop ─────────────────────────────────────────────────────
target_files = sorted(f for f in os.listdir(json_dir) if f.endswith('.json'))

print(f"Base dir  : {base_dir}")
print(f"Dados-dir : {json_dir}")
print(f"Out-dir   : {out_dir}")
print(f"Releases  : {len(target_files)} arquivo(s)\n")

for file in target_files:
    filepath     = os.path.join(json_dir, file)
    out_filepath = os.path.join(out_dir, file)

    print(f"{'='*60}")
    print(f"Processando {file}...")

    if os.path.exists(out_filepath):
        print(f"  Skipping — já existe.\n", flush=True)
        continue

    mapping_data = {"release": "", "mappings": {}}

    with open(filepath, 'r', encoding='utf-8') as f:
        data    = json.load(f)
        release = data.get("release", file.replace(".json", ""))
        mapping_data["release"] = release

        for feat in target_features:
            feature_data = data.get("features", {}).get(feat)
            if not feature_data:
                continue

            version = feature_data.get("version")
            if not version or version == "N/A":
                mapping_data["mappings"][feat] = {
                    "version": version, "status": "SKIPPED", "commit": None,
                    "heuristic_id": None, "heuristic_description": None,
                    "matched_value": None, "repository": None,
                }
                continue

            # Apply version override (e.g. CDT Indigo→Juno)
            override          = VERSION_OVERRIDES.get((feat, release))
            effective_version = override if override else version
            if override:
                print(f"  [OVERRIDE] {feat}: '{version}' → '{effective_version}'", flush=True)

            found = False
            for repo_name in repo_map[feat]:
                repo_dir = os.path.join(base_dir, repo_name)
                if not os.path.exists(repo_dir):
                    continue

                print(f"  [{feat}] v={effective_version}  repo={repo_name}", flush=True)

                # ── Collect candidates from all heuristics ────────────────
                candidates = []
                candidates += h1_tags(effective_version, repo_dir, release_name=release)
                candidates += h0b_tag_timestamp(effective_version, repo_dir)
                candidates += h0_timestamp(effective_version, repo_dir, release_name=release)
                candidates += h3_train_tags(release, repo_dir)
                candidates += h4_maintenance_branch(effective_version, repo_dir, release_name=release)

                # H2 (slow) only when faster heuristics found nothing
                if not candidates:
                    print(f"    [H2] Pickaxe (slow)...", flush=True)
                    candidates += h2_pickaxe(effective_version, repo_dir, release_name=release)

                # ── Vote ──────────────────────────────────────────────────
                result = vote(candidates, release_name=release, repo_dir=repo_dir)

                if result:
                    status = "SUCCESS" if result["vote_confident"] else "UNCERTAIN"
                    mapping_data["mappings"][feat] = {
                        "version":               version,
                        "status":                status,
                        "commit":                result["commit"],
                        "heuristic_id":          result["heuristic_id"],
                        "heuristic_description": result["heuristic_description"],
                        "matched_value":         result["matched_value"],
                        "repository":            repo_name,
                        "vote_total_weight":     result["vote_total_weight"],
                        "vote_candidates":       result["vote_candidates"],
                    }
                    flag = "✓" if result["vote_confident"] else "?"
                    print(
                        f"    -> {flag} commit={result['commit'][:12]}  "
                        f"weight={result['vote_total_weight']}  "
                        f"candidates={result['vote_candidates']}",
                        flush=True
                    )
                    found = True
                    break

            if not found:
                print(f"    -> NOT FOUND", flush=True)
                mapping_data["mappings"][feat] = {
                    "version": version, "status": "NOT FOUND", "commit": None,
                    "heuristic_id": None, "heuristic_description": None,
                    "matched_value": None, "repository": None,
                }

    with open(out_filepath, "w", encoding="utf-8") as out_f:
        json.dump(mapping_data, out_f, indent=4, ensure_ascii=False)
    print(f"  Salvo -> {out_filepath}\n", flush=True)

print(f"\nMapeamento concluído. Resultados em: {out_dir}")
