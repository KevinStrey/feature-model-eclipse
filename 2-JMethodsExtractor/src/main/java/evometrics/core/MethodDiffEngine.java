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
        public int tach;
    }

    public static DiffResult computeDiff(String oldCode, String newCode) {
        DiffResult result = new DiffResult();
        if (oldCode == null) oldCode = "";
        if (newCode == null) newCode = "";

        List<String> oldLines = Arrays.asList(oldCode.split("\\r?\\n"));
        List<String> newLines = Arrays.asList(newCode.split("\\r?\\n"));

        Patch<String> patch = DiffUtils.diff(oldLines, newLines);
        for (AbstractDelta<String> delta : patch.getDeltas()) {
            switch (delta.getType()) {
                case INSERT:
                    result.added += delta.getTarget().getLines().size();
                    break;
                case DELETE:
                    result.deleted += delta.getSource().getLines().size();
                    break;
                case CHANGE:
                    result.deleted += delta.getSource().getLines().size();
                    result.added += delta.getTarget().getLines().size();
                    break;
            }
        }
        result.tach = result.added + result.deleted;
        return result;
    }

    public static int countLines(String code) {
        if (code == null || code.isEmpty()) return 0;
        return code.split("\\r?\\n").length;
    }
}
