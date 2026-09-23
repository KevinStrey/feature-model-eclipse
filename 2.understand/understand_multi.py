import os
import sys
import json
import subprocess
import shutil
import shlex
import signal
import time
import threading
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
import tkinter as tk
from tkinter import ttk, messagebox
# pyrefly: ignore [missing-import]
import pydriller

# -------------------------------------------------------------------------
# CONSTANTS
# -------------------------------------------------------------------------
UND_BIN = r"C:\Program Files\SciTools\bin\pc-win64\und.exe"

REPO_URL_MAP = {
    "eclipse.jdt.core": "https://github.com/eclipse-jdt/eclipse.jdt.core.git",
    "eclipse.pde": "https://github.com/eclipse-pde/eclipse.pde.git",
    "cdt": "https://github.com/eclipse-cdt/cdt.git",
    "gef-classic": "https://github.com/eclipse/gef-classic.git",
    "gef": "https://github.com/eclipse/gef-classic.git",
    "org.eclipse.emf": "https://github.com/eclipse-emf/org.eclipse.emf.git",
    "birt": "https://github.com/eclipse-birt/birt.git",
    "datatools": "https://github.com/eclipse-datatools/datatools.git",
    "eclipselink": "https://github.com/eclipse-ee4j/eclipselink.git",
    "egit": "https://github.com/eclipse-egit/egit.git",
    "gmf-runtime": "https://github.com/eclipse-gmf-runtime/gmf-runtime.git",
    "org.eclipse.mylyn": "https://github.com/eclipse-mylyn/org.eclipse.mylyn.git",
    "org.eclipse.rap": "https://github.com/eclipse-rap/org.eclipse.rap.git",
    "ptp": "https://github.com/eclipse-ptp/ptp.git",
    "scout.rt": "https://github.com/eclipse-scout/scout.rt.git",
    "webtools.javaee": "https://github.com/eclipse-jeetools/webtools.javaee.git",
    "windowbuilder": "https://github.com/eclipse-windowbuilder/windowbuilder.git",
    "m2e-core": "https://github.com/eclipse-m2e/m2e-core.git",
    "eclipse.cvs": "https://github.com/JAndrassy/org.eclipse.team.cvs.git",
    "subclipse": "https://github.com/subclipse/subclipse.git"
}

# -------------------------------------------------------------------------
# DIRECTORY & MAPPINGS
# -------------------------------------------------------------------------
def find_root_dir():
    curr = os.path.abspath(os.getcwd())
    while curr:
        if os.path.basename(curr).lower() == "feature-models":
            return curr
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent
    
    # Fallback
    return os.path.abspath(os.path.join(os.getcwd(), ".."))

def load_mappings(mappings_dir):
    all_mappings = {}
    if not os.path.exists(mappings_dir):
        return all_mappings
    
    for filename in os.listdir(mappings_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(mappings_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    release = data.get("release", filename.replace(".json", ""))
                    all_mappings[release] = data
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                
    return all_mappings

# -------------------------------------------------------------------------
# UND UTILS
# -------------------------------------------------------------------------
def run_und(cmd, log_fp=None, cwd=None, env=None, check=True):
    if log_fp is not None:
        log_fp.write("\n$ " + " ".join(shlex.quote(str(part)) for part in cmd) + "\n")
        log_fp.flush()
        res = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            stdout=log_fp,
            stderr=subprocess.STDOUT,
            check=False,
        )
    else:
        res = subprocess.run(cmd, cwd=cwd, env=env, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    # Understand returns 2 for warnings, which should not be treated as fatal errors
    if check and res.returncode not in (0, 2):
        raise subprocess.CalledProcessError(res.returncode, cmd)
    return res

def run_und_with_retry(cmd, log_fp=None, cwd=None, env=None, retries=1, retry_signals=(signal.SIGSEGV,)):
    max_attempts = max(1, retries + 1)
    for attempt in range(1, max_attempts + 1):
        try:
            return run_und(cmd, log_fp=log_fp, cwd=cwd, env=env, check=True)
        except subprocess.CalledProcessError as exc:
            is_signal = exc.returncode < 0
            signum = -exc.returncode if is_signal else None
            should_retry = is_signal and signum in {int(s) for s in retry_signals} and attempt < max_attempts
            if should_retry:
                print(f"WARNING: command crashed with signal {signum} (attempt {attempt}/{max_attempts}), retrying...", file=sys.stderr)
                continue
            raise

# -------------------------------------------------------------------------
# GUI DIALOG
# -------------------------------------------------------------------------
class ConfigDialog(tk.Toplevel):
    def __init__(self, parent, ordered_releases, all_mappings):
        super().__init__(parent)
        self.title("Understand Metrics Extractor Config")
        self.geometry("600x500")
        
        self.ordered_releases = ordered_releases
        self.all_mappings = all_mappings
        self.result = None
        
        # Determine all available features
        self.all_features = set()
        for r in ordered_releases:
            maps = all_mappings.get(r, {}).get("mappings", {})
            self.all_features.update(maps.keys())
        self.all_features = sorted(list(self.all_features))
        
        self.create_widgets()
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Releases
        lbl_rel = ttk.Label(main_frame, text="Releases to process:")
        lbl_rel.grid(row=0, column=0, sticky=tk.W)
        
        self.release_listbox = tk.Listbox(main_frame, selectmode=tk.MULTIPLE, exportselection=False)
        for r in self.ordered_releases:
            self.release_listbox.insert(tk.END, r)
        self.release_listbox.grid(row=1, column=0, sticky=tk.NSEW, padx=5, pady=5)
        
        # Features
        lbl_feat = ttk.Label(main_frame, text="Features to process (leave empty for ALL):")
        lbl_feat.grid(row=0, column=1, sticky=tk.W)
        
        self.feature_listbox = tk.Listbox(main_frame, selectmode=tk.MULTIPLE, exportselection=False)
        for f in self.all_features:
            self.feature_listbox.insert(tk.END, f)
        self.feature_listbox.grid(row=1, column=1, sticky=tk.NSEW, padx=5, pady=5)
        
        main_frame.rowconfigure(1, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(btn_frame, text="Start Collection", command=self.on_start).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.LEFT, padx=5)

    def on_start(self):
        sel_rel_idx = self.release_listbox.curselection()
        if not sel_rel_idx:
            messagebox.showwarning("Warning", "Please select at least one release.")
            return
            
        sel_releases = [self.release_listbox.get(i) for i in sel_rel_idx]
        
        sel_feat_idx = self.feature_listbox.curselection()
        if not sel_feat_idx:
            sel_features = None # All
        else:
            sel_features = [self.feature_listbox.get(i) for i in sel_feat_idx]
            
        self.result = {
            "releases": sel_releases,
            "features": set(sel_features) if sel_features else None
        }
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()

def show_config_gui(ordered_releases, all_mappings):
    root = tk.Tk()
    root.withdraw()
    dialog = ConfigDialog(root, ordered_releases, all_mappings)
    root.wait_window(dialog)
    return dialog.result

# -------------------------------------------------------------------------
# CORE TASK
# -------------------------------------------------------------------------
class ProgressGUI(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Understand Extraction Progress")
        self.geometry("800x600")
        self.text_area = tk.Text(self, state=tk.DISABLED, wrap=tk.WORD)
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def log(self, msg):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, msg + "\n")
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)
        self.update()
        
    def on_close(self):
        # Prevent closing until done
        pass
        
    def enable_close(self):
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.log("\nFINISHED! You can now close this window.")

def collect_feature_task(feature_name, repo_name, repos_dir_path, release_to_commit, target_releases, log_queue):
    if not repo_name:
        return
        
    repo_path = os.path.join(repos_dir_path, repo_name)
    home = os.path.expanduser('~')
    output_dir = os.path.abspath(os.path.join(os.getcwd(), "output", feature_name))
    os.makedirs(output_dir, exist_ok=True)
    
    gr = pydriller.Git(repo_path)
    
    for release, commit in release_to_commit.items():
        if release not in target_releases:
            continue
            
        csv_path = os.path.join(output_dir, f"{release}.csv")
        db_path = os.path.join(output_dir, f"{release}.und")
        log_path = os.path.join(output_dir, f"{release}.und.log")
        scitools_cache = os.path.join(home, ".local", "share", "Scitools", "Db", commit)

        if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
            log_queue.put(f"[{feature_name}|{release}] Commit {commit} already collected.")
            continue

        log_queue.put(f"[{feature_name}|{release}] Starting collection on {repo_name} at commit {commit}")
        
        try:
            gr.clear()
            gr.checkout(commit)
            
            if os.path.exists(scitools_cache):
                shutil.rmtree(scitools_cache, ignore_errors=True)
            if os.path.exists(db_path):
                shutil.rmtree(db_path, ignore_errors=True)
                
            with open(log_path, 'w', encoding='utf-8', errors='replace') as log_fp:
                run_und([UND_BIN, 'create', '-db', db_path, '-languages', 'java'], log_fp=log_fp)
                os.makedirs(os.path.join(db_path, 'local'), exist_ok=True)
                
                # Add files from the repository
                run_und([UND_BIN, '-db', db_path, 'add', repo_path], log_fp=log_fp)
                run_und_with_retry([UND_BIN, 'analyze', '-errors', '-db', db_path], log_fp=log_fp, retries=1)
                
                run_und([UND_BIN, 'settings', '-metricsOutputFile', csv_path, db_path], log_fp=log_fp)
                metrics = [
                    'AvgCyclomatic', 'AvgCyclomaticModified', 'AvgCyclomaticStrict', 'AvgEssential', 'AvgLine', 'AvgLineBlank', 'AvgLineCode',
                    'AvgLineComment', 'CountClassBase', 'CountClassCoupled', 'CountClassDerived', 'CountDeclClass', 'CountDeclClassMethod',
                    'CountDeclClassVariable', 'CountDeclFile', 'CountDeclFunction', 'CountDeclInstanceMethod', 'CountDeclInstanceVariable',
                    'CountDeclMethod', 'CountDeclMethodAll', 'CountDeclMethodDefault', 'CountDeclMethodPrivate', 'CountDeclMethodProtected',
                    'CountDeclMethodPublic', 'CountInput', 'CountLine', 'CountLineBlank', 'CountLineCode', 'CountLineCodeDecl', 'CountLineCodeExe',
                    'CountLineComment', 'CountOutput', 'CountPath', 'CountSemicolon', 'CountStmt', 'CountStmtDecl', 'CountStmtExe', 'Cyclomatic',
                    'CyclomaticModified', 'CyclomaticStrict', 'Essential', 'MaxCyclomatic', 'MaxCyclomaticModified', 'MaxCyclomaticStrict',
                    'MaxEssential', 'MaxInheritanceTree', 'MaxNesting', 'PercentLackOfCohesion', 'RatioCommentToCode', 'SumCyclomatic',
                    'SumCyclomaticModified', 'SumCyclomaticStrict', 'SumEssential'
                ]
                run_und([UND_BIN, 'settings', '-metricmetricsAdd'] + metrics + [db_path], log_fp=log_fp)
                run_und([UND_BIN, 'settings', '-MetricFileNameDisplayMode', 'RelativePath', db_path], log_fp=log_fp)
                run_und([UND_BIN, 'settings', '-MetricDeclaredInFileDisplayMode', 'RelativePath', db_path], log_fp=log_fp)
                run_und([UND_BIN, 'settings', '-MetricShowDeclaredInFile', 'on', db_path], log_fp=log_fp)
                run_und([UND_BIN, 'settings', '-MetricShowFunctionParameterTypes', 'on', db_path], log_fp=log_fp)
                
                run_und([UND_BIN, 'metrics', db_path], log_fp=log_fp)
            
            if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
                log_queue.put(f"[{feature_name}|{release}] Success.")
                try:
                    os.remove(log_path)
                except:
                    pass
            else:
                log_queue.put(f"[{feature_name}|{release}] ERROR: CSV empty or missing.")
                
        except Exception as e:
            log_queue.put(f"[{feature_name}|{release}] FATAL ERROR: {e}")
        finally:
            if os.path.exists(db_path):
                shutil.rmtree(db_path, ignore_errors=True)
            if os.path.exists(scitools_cache):
                shutil.rmtree(scitools_cache, ignore_errors=True)
            
            try:
                gr.reset()
            except:
                pass

def main():
    print("Starting Understand Multi-Repo Metrics Collector...")
    root_dir = find_root_dir()
    repos_dir = os.path.join(root_dir, "1-Repositorios")
    mappings_dir = os.path.join(root_dir, "3-Mapeamento_features_simrel", "simrel_mapper", "output")
    
    print(f"Repositorios Dir: {repos_dir}")
    print(f"Mappings Dir: {mappings_dir}")
    
    all_mappings = load_mappings(mappings_dir)
    
    # Sort releases by date
    ordered_releases = sorted(list(all_mappings.keys()), key=lambda r: all_mappings[r].get("date", ""))
    
    config = show_config_gui(ordered_releases, all_mappings)
    if not config:
        print("Cancelled by user.")
        return
        
    print(f"Config: {len(config['releases'])} releases, {len(config['features']) if config['features'] else 'ALL'} features.")
    
    # Process mappings
    feature_evolution_map = {}
    feature_repository_map = {}
    
    for release in config["releases"]:
        mapping = all_mappings.get(release, {}).get("mappings", {})
        for feature_name, fmap in mapping.items():
            if config["features"] and feature_name not in config["features"]:
                continue
                
            commit = fmap.get("commit")
            repo = fmap.get("repository")
            
            if feature_name not in feature_evolution_map:
                feature_evolution_map[feature_name] = {}
            feature_evolution_map[feature_name][release] = commit
            
            if repo:
                feature_repository_map[feature_name] = repo
                
    # Clone missing repos
    unique_repos = set(feature_repository_map.values())
    for repo_name in unique_repos:
        repo_path = os.path.join(repos_dir, repo_name)
        if not os.path.exists(repo_path) or not os.path.exists(os.path.join(repo_path, ".git")):
            clone_url = REPO_URL_MAP.get(repo_name)
            if clone_url:
                print(f"Cloning {repo_name} from {clone_url}...")
                subprocess.run(["git", "clone", clone_url, repo_path], check=False)
            else:
                print(f"WARNING: No clone URL for {repo_name}")

    manager = multiprocessing.Manager()
    log_queue = manager.Queue()
    
    root_win = tk.Tk()
    root_win.withdraw()
    progress_gui = ProgressGUI(root_win)
    
    def poll_logs():
        done = False
        while not log_queue.empty():
            try:
                msg = log_queue.get_nowait()
                if msg == "__DONE__":
                    done = True
                else:
                    print(msg)
                    progress_gui.log(msg)
            except:
                break
        
        if done:
            progress_gui.enable_close()
        else:
            root_win.after(100, poll_logs)
            
    poll_logs()
        
    sorted_features = sorted(list(feature_evolution_map.keys()))

    def run_all_tasks():
        try:
            with ProcessPoolExecutor() as executor:
                futures = []
                for feature in sorted_features:
                    repo_name = feature_repository_map.get(feature)
                    releases = feature_evolution_map[feature]
                    futures.append(
                        executor.submit(
                            collect_feature_task, 
                            feature, repo_name, repos_dir, releases, config["releases"], log_queue
                        )
                    )
                for f in as_completed(futures):
                    f.result()
        except Exception as e:
            log_queue.put(f"Fatal error during execution: {e}")
        finally:
            log_queue.put("__DONE__")

    extraction_thread = threading.Thread(target=run_all_tasks, daemon=True)
    extraction_thread.start()
    
    root_win.mainloop()
    
    print("All Understand metrics collected successfully.")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
