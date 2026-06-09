package evometrics.core;

import evometrics.git.GitEngine;
import evometrics.models.MethodState;
import evometrics.parser.JavaParserExtractor;
import org.eclipse.jgit.lib.Repository;
import org.eclipse.jgit.revwalk.RevCommit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.HashSet;

public class FeatureEvolutorTask implements Runnable {
    private static final Logger log = LoggerFactory.getLogger(FeatureEvolutorTask.class);

    private final String featureName;
    private final String repositoryName; // e.g. "eclipse.jdt.core"
    private final String basePath;
    private final List<String> orderedReleases;
    private final Map<String, String> releaseToCommitMap; // Map release name -> commit hash for this feature

    // Internal state
    private final Map<String, MethodState> globalMethodStates = new HashMap<>();
    private int globalCommitIndex = 0;

    public FeatureEvolutorTask(String featureName, String repositoryName, String basePath, 
                               List<String> orderedReleases, Map<String, String> releaseToCommitMap) {
        this.featureName = featureName;
        this.repositoryName = repositoryName;
        this.basePath = basePath;
        this.orderedReleases = orderedReleases;
        this.releaseToCommitMap = releaseToCommitMap;
    }

    @Override
    public void run() {
        if (repositoryName == null) {
            log.warn("[{}] No repository configured. Skipping.", featureName);
            return;
        }

        String repoPath = basePath + File.separator + repositoryName;
        try (Repository repo = GitEngine.openRepository(repoPath)) {
            if (repo == null) return;

            log.info("[{}] Starting evolution analysis on {}", featureName, repoPath);
            String previousTargetCommit = null;

            for (String release : orderedReleases) {
                String targetCommitHash = releaseToCommitMap.get(release);
                if (targetCommitHash == null || targetCommitHash.isEmpty() || targetCommitHash.equals("null")) {
                    log.info("[{}] Release {} has no valid commit mapped. Skipping.", featureName, release);
                    continue;
                }

                log.info("[{}] Fetching commits for release {} up to {}", featureName, release, targetCommitHash);
                List<RevCommit> commitsToProcess = GitEngine.getCommitsBetween(repo, previousTargetCommit, targetCommitHash);

                for (RevCommit commit : commitsToProcess) {
                    globalCommitIndex++;
                    processCommit(repo, commit, globalCommitIndex);
                }

                // End of release -> Export CSV
                log.info("[{}] Generating CSV for release {} (Processed {} commits so far)", featureName, release, globalCommitIndex);
                CsvExporter.export(release, featureName, globalMethodStates, globalCommitIndex);

                previousTargetCommit = targetCommitHash;
            }

            log.info("[{}] Evolution analysis completed.", featureName);

        } catch (Exception e) {
            log.error("[{}] Unhandled error in FeatureEvolutorTask: {}", featureName, e.getMessage(), e);
        }
    }

    private void processCommit(Repository repo, RevCommit commit, int commitIndex) {
        List<String> modifiedJavaFiles = GitEngine.getModifiedJavaFiles(repo, commit);
        
        Set<String> processedMethodsInCommit = new HashSet<>();

        for (String filePath : modifiedJavaFiles) {
            String sourceCode = GitEngine.getFileContent(repo, commit, filePath);
            if (sourceCode == null) continue; // Could be deleted file or unreadable

            Map<String, String> currentMethods = JavaParserExtractor.extractMethods(filePath, sourceCode);

            for (Map.Entry<String, String> entry : currentMethods.entrySet()) {
                String methodId = entry.getKey();
                String methodCode = entry.getValue();
                processedMethodsInCommit.add(methodId);

                MethodState state = globalMethodStates.get(methodId);
                if (state == null) {
                    state = new MethodState(methodId);
                    int loc = MethodDiffEngine.countLines(methodCode);
                    state.onSeen(commitIndex, loc);
                    state.currentCode = methodCode;
                    globalMethodStates.put(methodId, state);
                } else {
                    if (!state.currentCode.equals(methodCode)) {
                        MethodDiffEngine.DiffResult diff = MethodDiffEngine.computeDiff(state.currentCode, methodCode);
                        int loc = MethodDiffEngine.countLines(methodCode);
                        state.onChange(commitIndex, diff.tach, loc);
                        state.currentCode = methodCode;
                    } else {
                        state.onNoChange(commitIndex);
                    }
                }
            }
        }

        // Handle methods that weren't modified in this commit
        for (MethodState state : globalMethodStates.values()) {
            if (!processedMethodsInCommit.contains(state.getMethodId()) && state.isAlive) {
                state.onNoChange(commitIndex);
            }
        }
    }
}
