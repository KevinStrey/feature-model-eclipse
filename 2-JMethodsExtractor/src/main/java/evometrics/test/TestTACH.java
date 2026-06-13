package evometrics.test;

import evometrics.core.MethodDiffEngine;
import evometrics.parser.JavaParserExtractor;
import org.eclipse.jgit.api.Git;
import org.eclipse.jgit.lib.Repository;
import org.eclipse.jgit.revwalk.RevCommit;
import org.eclipse.jgit.revwalk.RevWalk;
import org.eclipse.jgit.treewalk.TreeWalk;
import org.eclipse.jgit.treewalk.filter.PathFilter;
import org.eclipse.jgit.lib.ObjectId;
import org.eclipse.jgit.storage.file.FileRepositoryBuilder;

import java.io.File;
import java.util.Map;

public class TestTACH {
    public static void main(String[] args) throws Exception {
        File repoDir = new File("C:\\Users\\Kevin Strey\\Desktop\\Feature-models\\1-Repositorios\\eclipse.cvs\\.git");
        Repository repo = new FileRepositoryBuilder().setGitDir(repoDir).build();

        String oldHash = "3f3296cf7c24d3b5db580a4ae51d40cce754cb0b"; // some parent commit? We need the actual parent.
        String newHash = "f45a2e068ac35e8a4e42f7b5e1c666460e18f66a";
        String filePath = "bundles/org.eclipse.compare/compare/org/eclipse/compare/EditionSelectionDialog.java";

        RevWalk walk = new RevWalk(repo);
        RevCommit newCommit = walk.parseCommit(repo.resolve(newHash));
        RevCommit oldCommit = newCommit.getParent(0);

        String oldCode = getFileContent(repo, oldCommit, filePath);
        String newCode = getFileContent(repo, newCommit, filePath);

        Map<String, String> oldMethods = JavaParserExtractor.extractMethods(filePath, oldCode);
        Map<String, String> newMethods = JavaParserExtractor.extractMethods(filePath, newCode);

        String methodId = "bundles/org.eclipse.compare/compare/org/eclipse/compare/EditionSelectionDialog.java::createButtonsForButtonBar(Composite)";
        
        String oldMethod = oldMethods.get(methodId);
        String newMethod = newMethods.get(methodId);

        System.out.println("--- OLD ---");
        System.out.println(oldMethod);
        System.out.println("--- NEW ---");
        System.out.println(newMethod);

        MethodDiffEngine.DiffResult diff = MethodDiffEngine.computeDiff(oldMethod, newMethod);
        System.out.println("Added: " + diff.added);
        System.out.println("Deleted: " + diff.deleted);
        System.out.println("Changed: " + diff.changed);
        System.out.println("TACH: " + diff.tach);
    }

    private static String getFileContent(Repository repo, RevCommit commit, String path) throws Exception {
        try (TreeWalk treeWalk = new TreeWalk(repo)) {
            treeWalk.addTree(commit.getTree());
            treeWalk.setRecursive(true);
            treeWalk.setFilter(PathFilter.create(path));
            if (!treeWalk.next()) return null;
            ObjectId objectId = treeWalk.getObjectId(0);
            return new String(repo.open(objectId).getBytes(), "UTF-8");
        }
    }
}
