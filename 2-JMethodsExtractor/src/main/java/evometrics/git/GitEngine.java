package evometrics.git;

import org.eclipse.jgit.api.Git;
import org.eclipse.jgit.diff.DiffEntry;
import org.eclipse.jgit.diff.DiffFormatter;
import org.eclipse.jgit.diff.RawTextComparator;
import org.eclipse.jgit.lib.ObjectId;
import org.eclipse.jgit.lib.ObjectReader;
import org.eclipse.jgit.lib.Repository;
import org.eclipse.jgit.revwalk.RevCommit;
import org.eclipse.jgit.revwalk.RevWalk;
import org.eclipse.jgit.revwalk.filter.RevFilter;
import org.eclipse.jgit.storage.file.FileRepositoryBuilder;
import org.eclipse.jgit.treewalk.TreeWalk;
import org.eclipse.jgit.treewalk.filter.PathSuffixFilter;
import org.eclipse.jgit.util.io.DisabledOutputStream;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class GitEngine {
    private static final Logger log = LoggerFactory.getLogger(GitEngine.class);

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

    public static List<RevCommit> getCommitsBetween(Repository repo, String prevCommitHash, String targetCommitHash) {
        List<RevCommit> commits = new ArrayList<>();
        try (RevWalk walk = new RevWalk(repo)) {
            walk.setRevFilter(RevFilter.NO_MERGES);
            ObjectId targetId = repo.resolve(targetCommitHash);
            if (targetId == null) {
                log.error("[GIT_ERROR] Target commit {} not found in repo", targetCommitHash);
                return commits;
            }
            RevCommit targetCommit = walk.parseCommit(targetId);
            walk.markStart(targetCommit);

            if (prevCommitHash != null) {
                ObjectId prevId = repo.resolve(prevCommitHash);
                if (prevId != null) {
                    RevCommit prevCommit = walk.parseCommit(prevId);
                    walk.markUninteresting(prevCommit);
                } else {
                    log.warn("[GIT_WARN] Previous commit {} not found, parsing everything up to target.", prevCommitHash);
                }
            }

            for (RevCommit commit : walk) {
                commits.add(commit);
            }
            // Reverse to process chronologically
            Collections.reverse(commits);
        } catch (Exception e) {
            log.error("[GIT_ERROR] Error getting commits: {}", e.getMessage());
        }
        return commits;
    }

    public static List<String> getModifiedJavaFiles(Repository repo, RevCommit currentCommit) {
        List<String> modifiedFiles = new ArrayList<>();
        try (RevWalk rw = new RevWalk(repo);
             DiffFormatter df = new DiffFormatter(DisabledOutputStream.INSTANCE)) {
            
            df.setRepository(repo);
            df.setDiffComparator(RawTextComparator.DEFAULT);
            df.setDetectRenames(true);

            List<DiffEntry> diffs;
            if (currentCommit.getParentCount() > 0) {
                RevCommit parent = rw.parseCommit(currentCommit.getParent(0).getId());
                diffs = df.scan(parent.getTree(), currentCommit.getTree());
            } else {
                try (TreeWalk tw = new TreeWalk(repo)) {
                    tw.reset();
                    tw.setRecursive(true);
                    tw.addTree(currentCommit.getTree());
                    tw.setFilter(PathSuffixFilter.create(".java"));
                    while (tw.next()) {
                        modifiedFiles.add(tw.getPathString());
                    }
                }
                return modifiedFiles;
            }

            for (DiffEntry diff : diffs) {
                if (diff.getChangeType() == DiffEntry.ChangeType.DELETE) {
                    continue; // Skip deleted files, we can't parse them.
                }
                String newPath = diff.getNewPath();
                if (newPath.endsWith(".java")) {
                    modifiedFiles.add(newPath);
                }
            }
        } catch (Exception e) {
            log.error("[GIT_ERROR] Failed to get modified files for commit {}: {}", currentCommit.getName(), e.getMessage());
        }
        return modifiedFiles;
    }

    public static String getFileContent(Repository repo, RevCommit commit, String filePath) {
        try (TreeWalk tw = TreeWalk.forPath(repo, filePath, commit.getTree())) {
            if (tw == null) {
                return null;
            }
            ObjectId objectId = tw.getObjectId(0);
            try (ObjectReader reader = repo.newObjectReader()) {
                byte[] bytes = reader.open(objectId).getBytes();
                return new String(bytes, StandardCharsets.UTF_8);
            }
        } catch (Exception e) {
            log.error("[GIT_ERROR] Failed to read file {} at commit {}: {}", filePath, commit.getName(), e.getMessage());
            return null;
        }
    }
}
