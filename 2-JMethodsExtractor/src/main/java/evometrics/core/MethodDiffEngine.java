package evometrics.core;

import com.github.difflib.DiffUtils;
import com.github.difflib.patch.AbstractDelta;
import com.github.difflib.patch.Patch;
import java.util.Arrays;
import java.util.List;

public class MethodDiffEngine {
    
    public static class DiffResult {
        public int added;
        public int deleted;
        public int changed;
        public int tach;
    }

    public static DiffResult computeDiff(String oldCode, String newCode) {
        DiffResult result = new DiffResult();
        if (oldCode == null) oldCode = "";
        if (newCode == null) newCode = "";

        List<String> oldLines = getSignificantLines(oldCode);
        List<String> newLines = getSignificantLines(newCode);

        Patch<String> patch = DiffUtils.diff(oldLines, newLines);
        for (AbstractDelta<String> delta : patch.getDeltas()) {
            result.added += delta.getTarget().getLines().size();
            result.deleted += delta.getSource().getLines().size();
        }
        
        // TACH = NAL + NDL + 2 * NCL
        // Mathematically, Total_Added = NAL + NCL, and Total_Deleted = NDL + NCL.
        // So Total_Added + Total_Deleted = NAL + NDL + 2*NCL = TACH.
        result.tach = result.added + result.deleted;
        return result;
    }

    private static List<String> getSignificantLines(String code) {
        String stripped = stripComments(code);
        List<String> lines = new java.util.ArrayList<>();
        for (String line : stripped.split("\\r?\\n")) {
            if (!line.trim().isEmpty()) {
                lines.add(line);
            }
        }
        return lines;
    }

    private static String stripComments(String code) {
        StringBuilder result = new StringBuilder();
        int length = code.length();
        boolean inString = false;
        boolean inChar = false;
        boolean inBlockComment = false;
        boolean inLineComment = false;
        
        for (int i = 0; i < length; i++) {
            char c = code.charAt(i);
            
            if (inBlockComment) {
                if (c == '*' && i + 1 < length && code.charAt(i + 1) == '/') {
                    inBlockComment = false;
                    i++; // skip '/'
                }
            } else if (inLineComment) {
                if (c == '\n') {
                    inLineComment = false;
                    result.append(c);
                }
            } else if (inString) {
                if (c == '\\') {
                    result.append(c);
                    if (i + 1 < length) {
                        result.append(code.charAt(i + 1));
                        i++;
                    }
                } else if (c == '"') {
                    inString = false;
                    result.append(c);
                } else {
                    result.append(c);
                }
            } else if (inChar) {
                if (c == '\\') {
                    result.append(c);
                    if (i + 1 < length) {
                        result.append(code.charAt(i + 1));
                        i++;
                    }
                } else if (c == '\'') {
                    inChar = false;
                    result.append(c);
                } else {
                    result.append(c);
                }
            } else {
                if (c == '/' && i + 1 < length) {
                    char next = code.charAt(i + 1);
                    if (next == '*') {
                        inBlockComment = true;
                        i++;
                        continue;
                    } else if (next == '/') {
                        inLineComment = true;
                        i++;
                        continue;
                    }
                }
                if (c == '"') {
                    inString = true;
                } else if (c == '\'') {
                    inChar = true;
                }
                result.append(c);
            }
        }
        return result.toString();
    }

    public static int countLines(String code) {
        if (code == null || code.isEmpty()) return 0;
        String stripped = stripComments(code);
        int count = 0;
        for (String line : stripped.split("\\r?\\n")) {
            if (!line.trim().isEmpty()) {
                count++;
            }
        }
        return count;
    }
}
