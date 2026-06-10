package evometrics.core;

import com.opencsv.CSVWriter;
import evometrics.models.MethodState;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;

public class CsvExporter implements AutoCloseable {
    private static final Logger log = LoggerFactory.getLogger(CsvExporter.class);
    
    private final CSVWriter writer;
    private final String feature;
    private final String release;
    private int exportedRowsCount = 0;

    public CsvExporter(String feature) throws IOException {
        this.feature = feature;
        this.release = null; // release is now written per-row
        String dirPath = "results";
        File dir = new File(dirPath);
        if (!dir.exists()) {
            dir.mkdirs();
        }

        String filePath = dirPath + "/" + feature + "_history.csv";
        this.writer = new CSVWriter(new FileWriter(filePath));
        String[] header = {
            "project", "release", "commitHash", "methodId", "BOM", "TACH", "FCH", "LCH",
            "FRCH", "WCH", "WCD", "CSB", "CSBS", "ACDF", "LOC"
        };
        writer.writeNext(header);
    }

    public void writeMethodState(MethodState state, int currentCommitIndex, String commitHash, String release, int loc) {
        String[] row = {
            feature,
            release,
            commitHash,
            state.getMethodId(),
            String.valueOf(state.bom),
            String.valueOf(state.lca), // TACH: lines changed in this commit
            String.valueOf(state.fch),
            String.valueOf(state.lch),
            String.valueOf(state.frch),
            String.format("%.4f", state.getWch(currentCommitIndex)),
            String.format("%.4f", state.getWcd(currentCommitIndex)),
            String.valueOf(state.csb),
            String.format("%.4f", state.getCsbs()),
            String.format("%.4f", state.getAcdf()),
            String.valueOf(loc)
        };
        writer.writeNext(row);
        exportedRowsCount++;
    }

    public int getExportedRowsCount() {
        return exportedRowsCount;
    }

    @Override
    public void close() throws IOException {
        writer.close();
        log.info("[CSV] Finished streaming {} method change-events to CSV for feature '{}'", exportedRowsCount, feature);
    }
}
