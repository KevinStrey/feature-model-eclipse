import git
import argparse
import pydriller
import shutil
import subprocess
import os
import time
import sys

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description='Extract process metrics')
    # ap.add_argument('--path', required=True)
    # ap.add_argument('--project_name', required=True)
    ap.add_argument('--java', required=True)
    args = ap.parse_args()

    # project = args.project_name
    gr = pydriller.Git(".")

    # tags
    repo = git.Repo(".")
    tags = repo.tags
    for tag in tags:
        commit = gr.get_commit_from_tag(tag.name).hash
        print(commit, tag.name)
        gr.checkout(commit)

        if os.path.exists(commit + '.und'):
            # print("deleting possibly corrupt project files...")
            shutil.rmtree(commit + '.und')
        # print("creating the project", commit + ".udb ...")
        subprocess.run(['und', 'create', '-db', commit + '.und', '-languages', 'java'])
        os.makedirs(commit + '.und/local')
        # print("adding java files to project...")
        subprocess.run(['und', '-db', commit + '.und', 'add', '.'])
        # print("analyzing source code for commit", commit + "...")
        subprocess.run(['und', 'analyze', '-db', commit + '.und'])
        # print("adding the metrics to the project and setting up the environment...")
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
        # print("calculating metrics for", commit + "...")
        subprocess.run(['und', 'metrics', commit + '.und'])
        # print("deleting", commit + '.und')
        if os.path.exists(commit + '.und'):
            shutil.rmtree(commit + '.und')
        home = os.path.expanduser('~')
        if os.path.exists(home + "/.local/share/Scitools/Db/"+commit):
            shutil.rmtree(home + "/.local/share/Scitools/Db/"+commit)
        # print("resetting repository", commit + "...")
        try:
            gr.reset()
        except:
            print(sys.exc_info())
        print("waiting for 3 seconds, it is safe to ctrl+c here...", flush=True)
        for i in range(300):
            time.sleep(0.01)

    print('finished ' + str(len(tags)) + ' releases.')
