package ckhistory.core;

import ckhistory.git.GitCheckoutEngine;
import com.github.mauricioaniche.ck.CK;
import com.github.mauricioaniche.ck.CKClassResult;
import com.github.mauricioaniche.ck.CKNotifier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Semaphore;

/**
 * Task that processes a single feature across multiple releases.
 * For each release, it checks out the target commit and runs CK metrics on the repository.
 */
public class FeatureCKTask implements Runnable {
    private static final Logger log = LoggerFactory.getLogger(FeatureCKTask.class);

    private final String featureName;
    private final String repositoryName;
    private final String basePath;
    private final List<String> orderedReleases;
    private final Map<String, String> releaseToCommitMap;
    private final Semaphore availableMemory;
    private final int requiredMemoryGB;

    public FeatureCKTask(String featureName, String repositoryName, String basePath,
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
            File repoDir = new File(repoPath);
            if (!repoDir.exists() || !new File(repoDir, ".git").exists()) {
                log.error("[{}] Repository directory not found or not a git repo: {}", featureName, repoPath);
                ProgressTracker.updateStatus(featureName, "Error: repository not found at " + repoPath);
                return;
            }

            log.info("[{}] Starting CK metrics evolution analysis on {}", featureName, repoPath);
            ProgressTracker.updateStatus(featureName, "Analyzing repository...");

            try (CKCsvExporter csvExporter = new CKCsvExporter(featureName)) {
                int commitIndex = 0;
                String previousCommitHash = null;

                for (String release : orderedReleases) {
                    String targetCommitHash = releaseToCommitMap.get(release);
                    if (targetCommitHash == null || targetCommitHash.isEmpty() || targetCommitHash.equals("null")) {
                        log.info("[{}] Release {} has no valid commit mapped. Skipping.", featureName, release);
                        continue;
                    }

                    // Skip if this is the same commit as the previous release
                    if (targetCommitHash.equals(previousCommitHash)) {
                        log.info("[{}] Release {} has same commit as previous release. Skipping.", featureName, release);
                        continue;
                    }

                    commitIndex++;
                    log.info("[{}] Processing release {} (commit {}) [{}/{}]",
                            featureName, release, targetCommitHash.substring(0, Math.min(8, targetCommitHash.length())),
                            commitIndex, orderedReleases.size());
                    ProgressTracker.updateStatus(featureName,
                            "Processing release " + release + " (" + commitIndex + " commits processed)");

                    // Checkout the target commit
                    boolean checkoutOk = GitCheckoutEngine.checkout(repoPath, targetCommitHash);
                    if (!checkoutOk) {
                        log.error("[{}] Failed to checkout commit {} for release {}. Skipping.",
                                featureName, targetCommitHash, release);
                        ProgressTracker.updateStatus(featureName,
                                "Error: checkout failed for " + release);
                        continue;
                    }

                    // Run CK on the checked-out repository
                    Map<String, CKClassResult> results = new HashMap<>();
                    try {
                        new CK(false, 0, false).calculate(repoPath, new CKNotifier() {
                            @Override
                            public void notify(CKClassResult result) {
                                results.put(result.getClassName(), result);
                            }

                            @Override
                            public void notifyError(String sourceFilePath, Exception e) {
                                log.warn("[{}] CK error in {}: {}", featureName, sourceFilePath, e.getMessage());
                            }
                        });
                    } catch (Exception e) {
                        log.error("[{}] CK analysis failed for release {}: {}", featureName, release, e.getMessage(), e);
                        ProgressTracker.updateStatus(featureName,
                                "Error during CK analysis for " + release + ": " + e.getMessage());
                        continue;
                    }

                    log.info("[{}] Release {}: found {} classes", featureName, release, results.size());

                    // Write results to CSV
                    csvExporter.writeClassResults(results, commitIndex, targetCommitHash, release);
                    csvExporter.writeMethodResults(results, commitIndex, targetCommitHash, release);

                    previousCommitHash = targetCommitHash;
                }

                log.info("[{}] CK evolution analysis completed. {} class rows, {} method rows.",
                        featureName, csvExporter.getClassRowCount(), csvExporter.getMethodRowCount());
                ProgressTracker.updateStatus(featureName,
                        "Completed! " + commitIndex + " releases, " +
                        csvExporter.getClassRowCount() + " class rows, " +
                        csvExporter.getMethodRowCount() + " method rows.");

            } catch (Exception e) {
                log.error("[{}] Unhandled error in FeatureCKTask: {}", featureName, e.getMessage(), e);
                ProgressTracker.updateStatus(featureName, "Error: " + e.getMessage());
            }
        } finally {
            availableMemory.release(requiredMemoryGB);
            log.info("[{}] Released {}GB memory permits.", featureName, requiredMemoryGB);
        }
    }
}
