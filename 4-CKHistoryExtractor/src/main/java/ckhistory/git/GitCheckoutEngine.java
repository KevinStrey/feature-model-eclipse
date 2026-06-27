package ckhistory.git;

import org.eclipse.jgit.api.Git;
import org.eclipse.jgit.api.CheckoutCommand;
import org.eclipse.jgit.api.ResetCommand;
import org.eclipse.jgit.lib.Repository;
import org.eclipse.jgit.storage.file.FileRepositoryBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;

public class GitCheckoutEngine {
    private static final Logger log = LoggerFactory.getLogger(GitCheckoutEngine.class);

    public static boolean cloneRepository(String cloneUrl, String destPath) {
        log.info("Cloning repository from {} to {} using native git...", cloneUrl, destPath);
        try {
            ProcessBuilder pb = new ProcessBuilder("git", "clone", cloneUrl, destPath);
            pb.redirectErrorStream(true);
            Process process = pb.start();

            try (java.io.BufferedReader reader = new java.io.BufferedReader(
                    new java.io.InputStreamReader(process.getInputStream()))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    log.info("[GIT_CLONE] {}", line);
                }
            }

            int exitCode = process.waitFor();
            if (exitCode == 0) {
                log.info("Repository cloned successfully: {}", destPath);
                return true;
            } else {
                log.error("[GIT_ERROR] Git clone failed with exit code: {}", exitCode);
                return false;
            }
        } catch (Exception e) {
            log.error("[GIT_ERROR] Failed to clone repository {} to {}: {}", cloneUrl, destPath, e.getMessage(), e);
            return false;
        }
    }

    public static Repository openRepository(String repoPath) {
        try {
            File gitDir = new File(repoPath, ".git");
            if (!gitDir.exists()) {
                gitDir = new File(repoPath); // maybe bare
            }
            return new FileRepositoryBuilder()
                    .setGitDir(gitDir)
                    .readEnvironment()
                    .findGitDir()
                    .build();
        } catch (IOException e) {
            log.error("[GIT_ERROR] Failed to open repository at {}: {}", repoPath, e.getMessage());
            return null;
        }
    }

    /**
     * Checks out a specific commit in the given repository directory.
     * Uses JGit to perform a detached HEAD checkout.
     *
     * @param repoPath   Path to the repository working directory
     * @param commitHash The commit hash to checkout
     * @return true if checkout was successful
     */
    public static boolean checkout(String repoPath, String commitHash) {
        try {
            File repoDir = new File(repoPath);
            try (Git git = Git.open(repoDir)) {
                // First, clean the working directory to avoid conflicts
                git.reset().setMode(ResetCommand.ResetType.HARD).call();
                git.clean().setCleanDirectories(true).setForce(true).call();

                // Checkout the target commit (detached HEAD)
                git.checkout()
                        .setName(commitHash)
                        .setForced(true)
                        .call();

                log.debug("[GIT] Checked out commit {} in {}", commitHash, repoPath);
                return true;
            }
        } catch (Exception e) {
            log.error("[GIT_ERROR] Failed to checkout commit {} in {}: {}", commitHash, repoPath, e.getMessage());
            return false;
        }
    }
}
