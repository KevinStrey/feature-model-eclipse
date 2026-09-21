import argparse

import pydriller
import shutil
import subprocess
import os
import shlex
import signal
import time
import sys


def check(chash, csv_path):
    if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
        print("Commit", chash, "already collected, skipping...")
        return True
    if os.path.exists(csv_path):
        print("Commit", chash, "has an empty CSV, recollecting...")
    else:
        print("Commit", chash, "not found, collecting...")
    return False


def run_und(cmd, *, log_fp=None, cwd=None, env=None, check=True):
    if log_fp is not None:
        log_fp.write("\n$ " + " ".join(shlex.quote(str(part)) for part in cmd) + "\n")
        log_fp.flush()
        return subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            check=check,
        )
    return subprocess.run(cmd, cwd=cwd, env=env, check=check)


def run_und_with_retry(cmd, *, log_fp=None, cwd=None, env=None, retries=1, retry_signals=(signal.SIGSEGV,)):
    max_attempts = max(1, retries + 1)
    for attempt in range(1, max_attempts + 1):
        try:
            return run_und(cmd, log_fp=log_fp, cwd=cwd, env=env, check=True)
        except subprocess.CalledProcessError as exc:
            is_signal = exc.returncode < 0
            signum = -exc.returncode if is_signal else None
            should_retry = is_signal and signum in {int(s) for s in retry_signals} and attempt < max_attempts
            if should_retry:
                print(
                    f"WARNING: command crashed with signal {signum} (attempt {attempt}/{max_attempts}), retrying...",
                    file=sys.stderr,
                )
                continue
            raise

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description='Extractor for changeDistiller')
    ap.add_argument('--project', required=True)
    ap.add_argument('--commits-file')
    args = ap.parse_args()

    repo_path = os.path.abspath(args.project)
    if not os.path.isdir(repo_path):
        raise SystemExit(f"--project must be an existing directory: {repo_path}")

    project_name = os.path.basename(os.path.normpath(repo_path))
    commits_file = args.commits_file or (f'commits-{project_name}.csv')

    with open(commits_file) as f:
        commits = [line.strip() for line in f.read().splitlines() if line.strip()]

    gr = pydriller.Git(repo_path)
    output_dir = os.getcwd()
    home = os.path.expanduser('~')
    #commits = ['73a432514936fcee1386b37a0d60dcd913706bd1','e7142a3937825074ec68e4bacba30f9c962bd1e4','df479df17676148bf6391401a704a7d7265c45fa','399d2929ee0912bfeda8a4ef125f1b96bb7fd144','f3b8653021830d8a503c5e7a9d33cb82b16db739','f2c58503d76be1dfb8072f6a7d592f88133708e1','41b194c718d50763a79951029787cca70a5804a5','1447159b926076c9222a96b3abbe17571953a74f','4f0daa3bb2a5fa28286f1973deb9d13996cc73cc','bf32c9102fb1b5fdfa7a26a120b5d9a6b428dd2f']

    #for commit in gr.get_list_commits():
        #commits.append(commit.hash)

    failed = []
    processed = 0

    for commit in commits:
        db_path = os.path.abspath(os.path.join(output_dir, commit + '.und'))
        csv_path = os.path.abspath(os.path.join(output_dir, commit + '.csv'))
        log_path = os.path.abspath(os.path.join(output_dir, commit + '.und.log'))

        if check(commit, csv_path):
            continue

        processed += 1
        commit_ok = False
        log_fp = open(log_path, 'w', encoding='utf-8', errors='replace')

        try:
            gr.clear()
            print("git checkout on commit", commit + "...")
            gr.checkout(commit)

            scitools_cache = os.path.join(home, ".local", "share", "Scitools", "Db", commit)
            if os.path.exists(scitools_cache):
                shutil.rmtree(scitools_cache)

            if os.path.exists(db_path):
                print("deleting possibly corrupt project files...")
                shutil.rmtree(db_path)

            print("creating the project", os.path.basename(db_path), "...")
            run_und(['und', 'create', '-db', db_path, '-languages', 'java'], log_fp=log_fp)
            os.makedirs(os.path.join(db_path, 'local'), exist_ok=True)

            print("adding java files to project...")
            # IMPORTANT: add files from the *repository* (not from the script cwd)
            run_und(['und', '-db', db_path, 'add', repo_path], log_fp=log_fp)

            print("analyzing source code for commit", commit + "...")
            # Reduce output volume (especially warnings) to avoid instability on some repos/commits.
            run_und_with_retry(['und', 'analyze', '-errors', '-db', db_path], log_fp=log_fp, retries=1)

            print("adding the metrics to the project and setting up the environment...")

            # Ensure metrics CSV output is written to the expected per-commit file.
            run_und(['und', 'settings', '-metricsOutputFile', csv_path, db_path], log_fp=log_fp)

            run_und(
                ['und', 'settings', '-metricmetricsAdd', 'AvgCyclomatic', 'AvgCyclomaticModified',
                 'AvgCyclomaticStrict', 'AvgEssential', 'AvgLine', 'AvgLineBlank', 'AvgLineCode',
                 'AvgLineComment', 'CountClassBase', 'CountClassCoupled', 'CountClassDerived',
                 'CountDeclClass', 'CountDeclClassMethod', 'CountDeclClassVariable', 'CountDeclFile',
                 'CountDeclFunction', 'CountDeclInstanceMethod', 'CountDeclInstanceVariable',
                 'CountDeclMethod', 'CountDeclMethodAll', 'CountDeclMethodDefault', 'CountDeclMethodPrivate',
                 'CountDeclMethodProtected', 'CountDeclMethodPublic', 'CountInput', 'CountLine',
                 'CountLineBlank', 'CountLineCode', 'CountLineCodeDecl', 'CountLineCodeExe',
                 'CountLineComment', 'CountOutput', 'CountPath', 'CountSemicolon', 'CountStmt',
                 'CountStmtDecl', 'CountStmtExe', 'Cyclomatic', 'CyclomaticModified', 'CyclomaticStrict',
                 'Essential', 'MaxCyclomatic', 'MaxCyclomaticModified', 'MaxCyclomaticStrict',
                 'MaxEssential', 'MaxInheritanceTree', 'MaxNesting', 'PercentLackOfCohesion',
                 'RatioCommentToCode', 'SumCyclomatic', 'SumCyclomaticModified', 'SumCyclomaticStrict',
                 'SumEssential', db_path],
                log_fp=log_fp,
            )
            run_und(['und', 'settings', '-MetricFileNameDisplayMode', 'RelativePath', db_path], log_fp=log_fp)
            run_und(['und', 'settings', '-MetricDeclaredInFileDisplayMode', 'RelativePath', db_path], log_fp=log_fp)
            run_und(['und', 'settings', '-MetricShowDeclaredInFile', 'on', db_path], log_fp=log_fp)
            run_und(['und', 'settings', '-MetricShowFunctionParameterTypes', 'on', db_path], log_fp=log_fp)

            print("calculating metrics for", commit + "...")
            run_und(['und', 'metrics', db_path], log_fp=log_fp)

            if not (os.path.exists(csv_path) and os.path.getsize(csv_path) > 0):
                raise RuntimeError(f"metrics CSV is missing or empty: {csv_path}")

            commit_ok = True

            print("deleting", os.path.basename(db_path))
            if os.path.exists(db_path):
                shutil.rmtree(db_path)

            if os.path.exists(scitools_cache):
                shutil.rmtree(scitools_cache)
        except Exception as exc:
            failed.append(commit)
            print(f"ERROR: failed on commit {commit}: {exc}", file=sys.stderr)
            print(f"Keeping artifacts for diagnosis: {db_path} and {log_path}", file=sys.stderr)
        finally:
            try:
                log_fp.close()
            except Exception:
                pass

            if commit_ok:
                try:
                    os.remove(log_path)
                except FileNotFoundError:
                    pass

            print("resetting repository", commit + "...")
            try:
                gr.reset()
            except Exception:
                print(sys.exc_info())

            print("waiting for 3 seconds, it is safe to ctrl+c here...", flush=True)
            for i in range(300):
                time.sleep(0.01)

    if failed:
        print(f"\nFinished with failures in {len(failed)}/{processed} processed commits.", file=sys.stderr)
        print("Failed commits:", file=sys.stderr)
        for c in failed:
            print(c, file=sys.stderr)
        raise SystemExit(1)
    print(f"\nFinished successfully. Processed commits: {processed}.")
