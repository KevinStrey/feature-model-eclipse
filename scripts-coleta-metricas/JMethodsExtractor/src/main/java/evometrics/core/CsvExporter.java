package evometrics.core;

import com.opencsv.CSVWriter;
import evometrics.models.MethodState;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.Map;

public class CsvExporter {
    private static final Logger log = LoggerFactory.getLogger(CsvExporter.class);

    public static void export(String release, String feature, Map<String, MethodState> states, int currentCommitIndex) {
        String dirPath = "results/" + release;
        File dir = new File(dirPath);
        if (!dir.exists()) {
            dir.mkdirs();
        }

        String filePath = dirPath + "/" + feature + "_" + release + ".csv";
        
        try (CSVWriter writer = new CSVWriter(new FileWriter(filePath))) {
            String[] header = {
                "project", "release", "methodId", "BOM", "TACH", "FCH", "LCH", 
                "FRCH", "WCH", "WCD", "CSB", "CSBS", "ACDF"
            };
            writer.writeNext(header);

            for (Map.Entry<String, MethodState> entry : states.entrySet()) {
                MethodState state = entry.getValue();
                if (!state.isAlive) continue; // Optionally only export alive methods

                String[] row = {
                    feature,
                    release,
                    state.getMethodId(),
                    String.valueOf(state.bom),
                    String.valueOf(state.lca), // tach from last change
                    String.valueOf(state.fch),
                    String.valueOf(state.lch),
                    String.valueOf(state.frch),
                    String.format("%.4f", state.getWch(currentCommitIndex)),
                    String.format("%.4f", state.getWcd(currentCommitIndex)),
                    String.valueOf(state.csb),
                    String.format("%.4f", state.getCsbs()),
                    String.format("%.4f", state.getAcdf())
                };
                writer.writeNext(row);
            }
            log.info("[CSV] Exported {} metrics to {}", states.size(), filePath);
        } catch (IOException e) {
            log.error("[CSV_ERROR] Failed to export CSV for {}: {}", filePath, e.getMessage());
        }
    }
}
