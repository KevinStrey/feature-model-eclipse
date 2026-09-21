import pydriller
import shutil
import subprocess
import os
import time
import sys


def check(chash):
    if os.path.exists(chash + '.csv'):
        print("Commit", chash, "already collected, skipping...")
        return True
    else:
        print("Commit", chash, "not found, collecting...")
        return False


gr = pydriller.Git(".")
commits = []

for commit in gr.get_list_commits():
    commits.append(commit.hash)

for commit in commits:
    if check(commit):
        continue
    
    gr.clear()
    print("git checkout on commit", commit + "...")
    gr.checkout(commit)
    if os.path.exists(commit + '.und'):
        print("deleting possibly corrupt project files...")
        shutil.rmtree(commit + '.und')
    print("creating the project", commit + ".udb ...")
    subprocess.run(['und', 'create', '-db', commit + '.und', '-languages', 'java'])
    os.makedirs(commit + '.und/local')
    print("adding java files to project...")
    subprocess.run(['und', '-db', commit + '.und', 'add', '.'])
    print("analyzing source code for commit", commit + "...")
    subprocess.run(['und', 'analyze', '-db', commit + '.und'])
    print("adding the metrics to the project and setting up the environment...")
    subprocess.run(
        ['und', 'settings', '-metricmetricsAdd', 'AvgCyclomatic', 'AvgCyclomaticModified', 'AvgCyclomaticStrict',
         'AvgEssential', 'AvgLine', 'AvgLineBlank', 'AvgLineCode', 'AvgLineComment', 'CountClassBase',
         'CountClassCoupled', 'CountClassDerived', 'CountDeclClass', 'CountDeclClassMethod',
         'CountDeclClassVariable', 'CountDeclFile', 'CountDeclFunction', 'CountDeclInstanceMethod',
         'CountDeclInstanceVariable', 'CountDeclMethod', 'CountDeclMethodAll', 'CountDeclMethodDefault',
         'CountDeclMethodPrivate', 'CountDeclMethodProtected', 'CountDeclMethodPublic', 'CountInput',
         'CountLine', 'CountLineBlank', 'CountLineCode', 'CountLineCodeDecl', 'CountLineCodeExe',
         'CountLineComment', 'CountOutput', 'CountPath', 'CountSemicolon', 'CountStmt', 'CountStmtDecl',
         'CountStmtExe', 'Cyclomatic', 'CyclomaticModified', 'CyclomaticStrict', 'Essential',
         'MaxCyclomatic', 'MaxCyclomaticModified', 'MaxCyclomaticStrict', 'MaxEssential',
         'MaxInheritanceTree', 'MaxNesting', 'PercentLackOfCohesion', 'RatioCommentToCode', 'SumCyclomatic',
         'SumCyclomaticModified', 'SumCyclomaticStrict', 'SumEssential', commit + '.und'])
    subprocess.run(['und', 'settings', '-MetricFileNameDisplayMode', 'RelativePath', commit + '.und'])
    subprocess.run(['und', 'settings', '-MetricDeclaredInFileDisplayMode', 'RelativePath', commit + '.und'])
    subprocess.run(['und', 'settings', '-MetricShowDeclaredInFile', 'on', commit + '.und'])
    subprocess.run(['und', 'settings', '-MetricShowFunctionParameterTypes', 'on', commit + '.und'])
    print("calculating metrics for", commit + "...")
    subprocess.run(['und', 'metrics', commit + '.und'])
    print("deleting", commit + '.und')
    if os.path.exists(commit + '.und'):
        shutil.rmtree(commit + '.und')
    if os.path.exists("/home/usuario/.local/share/Scitools/Db/"+commit):
        shutil.rmtree("/home/usuario/.local/share/Scitools/Db/"+commit)
    print("resetting repository", commit + "...")
    gr.reset()
    print("waiting for 3 seconds, it is safe to ctrl+c here...", flush=True)
    for i in range(300):
        time.sleep(0.01)