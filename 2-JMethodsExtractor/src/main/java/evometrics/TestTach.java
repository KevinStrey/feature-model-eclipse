package evometrics;

import evometrics.core.MethodDiffEngine;
import evometrics.core.MethodDiffEngine.DiffResult;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class TestTach {
    public static void main(String[] args) throws Exception {
        String repoDir = "c:\\\\Users\\\\Kevin Strey\\\\Desktop\\\\Feature-models\\\\1-Repositorios\\\\eclipse.cvs";
        
        String oldFile = getGitFile(repoDir, "ca434a1cd", "bundles/org.eclipse.team.ui/src/org/eclipse/team/internal/ui/synchronize/GlobalRefreshResourceSelectionPage.java");
        String newFile = getGitFile(repoDir, "d2e67e5eb2dbdcbe1db34773699a73c02f3d9872", "bundles/org.eclipse.team.ui/src/org/eclipse/team/internal/ui/synchronize/GlobalRefreshResourceSelectionPage.java");
        
        String oldMethod = extractMethod(oldFile, "public void createControl(Composite parent)");
        String newMethod = extractMethod(newFile, "public void createControl(Composite parent)");
        
        System.out.println("OLD:");
        System.out.println(oldMethod);
        System.out.println("NEW:");
        System.out.println(newMethod);
        
        DiffResult res = MethodDiffEngine.computeDiff(oldMethod, newMethod);
        System.out.println("Added: " + res.added);
        System.out.println("Deleted: " + res.deleted);
        System.out.println("TACH: " + res.tach);
    }
    
    private static String getGitFile(String dir, String commit, String path) throws Exception {
        ProcessBuilder pb = new ProcessBuilder("git", "show", commit + ":" + path);
        pb.directory(new java.io.File(dir));
        Process p = pb.start();
        BufferedReader reader = new BufferedReader(new InputStreamReader(p.getInputStream(), "UTF-8"));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            sb.append(line).append("\n");
        }
        return sb.toString();
    }
    
    private static String extractMethod(String code, String signature) {
        int idx = code.indexOf(signature);
        if (idx == -1) return "";
        int start = idx;
        int braces = 0;
        boolean started = false;
        int end = -1;
        for (int i = idx; i < code.length(); i++) {
            if (code.charAt(i) == '{') {
                braces++;
                started = true;
            } else if (code.charAt(i) == '}') {
                braces--;
            }
            if (started && braces == 0) {
                end = i + 1;
                break;
            }
        }
        return code.substring(start, end);
    }
}
