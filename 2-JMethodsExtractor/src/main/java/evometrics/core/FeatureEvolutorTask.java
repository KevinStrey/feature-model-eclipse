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
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.Semaphore;

public class FeatureEvolutorTask implements Runnable {
    private static final Logger log = LoggerFactory.getLogger(FeatureEvolutorTask.class);

    private final String featureName;
    private final String repositoryName; // e.g. "eclipse.jdt.core"
    private final String basePath;
    private final List<String> orderedReleases;
    private final Map<String, String> releaseToCommitMap; // Map release name -> commit hash for this feature
    private final Semaphore availableMemory;
    private final int requiredMemoryGB;

    // Internal state
    private final Map<String, MethodState> globalMethodStates = new HashMap<>();
    private int globalCommitIndex = 0;
    private String currentRelease = null; // tracks the release being processed

    public FeatureEvolutorTask(String featureName, String repositoryName, String basePath, 
                               List<String> orderedReleases, Map<String, String> releaseToCommitMap,
                               Semaphore availableMemory, int requiredMemoryGB) {
        this.featureName = featureName;
        this.repositoryName = repositoryName;
        this.basePath = basePath;
        this.orderedReleases = orderedReleases;
        this.releaseToCommitMap = releaseToCommitMap;
        this.availableMemory = availableMemory;
        this.requiredMemoryGB = requiredMemoryGB;
    }

    @Override
    public void run() {
        if (repositoryName == null) {
            log.warn("[{}] No repository configured. Skipping.", featureName);
            return;
        }

        try {
            log.info("[{}] Waiting for {}GB memory permits to start...", featureName, requiredMemoryGB);
            ProgressTracker.updateStatus(featureName, "Waiting for " + requiredMemoryGB + "GB memory permits...");
            availableMemory.acquire(requiredMemoryGB);
            log.info("[{}] Acquired {}GB memory permits. Starting execution.", featureName, requiredMemoryGB);
            ProgressTracker.updateStatus(featureName, "Starting execution...");
        } catch (InterruptedException e) {
            log.error("[{}] Interrupted while waiting for memory permits: {}", featureName, e.getMessage());
            ProgressTracker.updateStatus(featureName, "Interrupted while waiting for memory permits.");
            Thread.currentThread().interrupt();
            return;
        }

        try {
            String repoPath = basePath + File.separator + repositoryName;
            try (Repository repo = GitEngine.openRepository(repoPath)) {
                if (repo == null) {
                    ProgressTracker.updateStatus(featureName, "Failed to open repository.");
                    return;
                }

                log.info("[{}] Starting evolution analysis on {}", featureName, repoPath);
                ProgressTracker.updateStatus(featureName, "Analyzing repository...");
                String previousTargetCommit = null;

                try (CsvExporter csvExporter = new CsvExporter(featureName)) {
                    int releaseIndex = 0;
                    Set<String> visitedCommits = new HashSet<>();
                    
                    for (String release : orderedReleases) {
                        releaseIndex++;
                        String targetCommitHash = releaseToCommitMap.get(release);
                        if (targetCommitHash == null || targetCommitHash.isEmpty() || targetCommitHash.equals("null")) {
                            log.info("[{}] Release {} has no valid commit mapped. Skipping.", featureName, release);
                            continue;
                        }

                        log.info("[{}] Fetching commits for release {} up to {}", featureName, release, targetCommitHash);
                        ProgressTracker.updateStatus(featureName, "Fetching commits for release " + release + "...");
                        List<RevCommit> commitsToProcess = GitEngine.getCommitsBetween(repo, previousTargetCommit, targetCommitHash);

                        currentRelease = release;
                        for (RevCommit commit : commitsToProcess) {
                            if (!visitedCommits.add(commit.getName())) {
                                continue;
                            }
                            globalCommitIndex++;
                            if (globalCommitIndex % 50 == 0) {
                                ProgressTracker.updateStatus(featureName, "Processing release " + release + " (" + globalCommitIndex + " commits)");
                            }
                            processCommit(repo, commit, globalCommitIndex, release, releaseIndex, csvExporter);
                        }

                        previousTargetCommit = targetCommitHash;
                    }
                }

                log.info("[{}] Evolution analysis completed.", featureName);
                ProgressTracker.updateStatus(featureName, "Completed! Processed " + globalCommitIndex + " commits.");

            } catch (Exception e) {
                log.error("[{}] Unhandled error in FeatureEvolutorTask: {}", featureName, e.getMessage(), e);
                ProgressTracker.updateStatus(featureName, "Error: " + e.getMessage());
            }
        } finally {
            availableMemory.release(requiredMemoryGB);
            log.info("[{}] Released {}GB memory permits.", featureName, requiredMemoryGB);
        }
    }

    private final Map<String, Set<String>> fileToMethods = new HashMap<>();

    private void processCommit(Repository repo, RevCommit commit, int commitIndex, String release, int releaseIndex, CsvExporter csvExporter) {
        List<GitEngine.FileChange> modifiedJavaFiles = GitEngine.getModifiedJavaFiles(repo, commit);
        String commitHash = commit.getName();

        for (GitEngine.FileChange fileChange : modifiedJavaFiles) {
            String filePath = fileChange.path;

            if (fileChange.type != null && fileChange.type.name().equals("DELETE")) {
                Set<String> existingMethods = fileToMethods.get(filePath);
                if (existingMethods != null) {
                    for (String methodId : existingMethods) {
                        MethodState state = globalMethodStates.get(methodId);
                        if (state != null) {
                            state.onChange(commitIndex, 1, 0);
                            csvExporter.writeMethodState(state, commitIndex, commitHash, release, 0);
                            globalMethodStates.remove(methodId);
                        }
                    }
                    fileToMethods.remove(filePath);
                }
                continue;
            }

            String sourceCode = GitEngine.getFileContent(repo, commit, filePath);
            if (sourceCode == null) continue;

            Map<String, String> currentMethods = JavaParserExtractor.extractMethods(filePath, sourceCode);
            Set<String> previousMethods = fileToMethods.getOrDefault(filePath, new HashSet<>());
            Set<String> currentMethodIds = currentMethods.keySet();

            for (String oldMethodId : previousMethods) {
                if (!currentMethodIds.contains(oldMethodId)) {
                    MethodState state = globalMethodStates.get(oldMethodId);
                    if (state != null) {
                        state.onChange(commitIndex, 1, 0);
                        csvExporter.writeMethodState(state, commitIndex, commitHash, release, 0);
                        globalMethodStates.remove(oldMethodId);
                    }
                }
            }

            for (Map.Entry<String, String> entry : currentMethods.entrySet()) {
                String methodId = entry.getKey();
                String methodCode = entry.getValue();

                MethodState state = globalMethodStates.get(methodId);
                if (state == null) {
                    state = new MethodState(methodId);
                    int loc = MethodDiffEngine.countLines(methodCode);
                    state.onSeen(commitIndex, loc);
                    state.currentCode = methodCode;
                    globalMethodStates.put(methodId, state);
                    csvExporter.writeMethodState(state, commitIndex, commitHash, release, loc);
                } else {
                    if (!state.currentCode.equals(methodCode)) {
                        MethodDiffEngine.DiffResult diff = MethodDiffEngine.computeDiff(state.currentCode, methodCode);
                        int loc = MethodDiffEngine.countLines(methodCode);
                        state.onChange(commitIndex, diff.tach, loc);
                        state.currentCode = methodCode;
                        csvExporter.writeMethodState(state, commitIndex, commitHash, release, loc);
                    }
                }
            }
            
            fileToMethods.put(filePath, new HashSet<>(currentMethodIds));
        }
    }
}
