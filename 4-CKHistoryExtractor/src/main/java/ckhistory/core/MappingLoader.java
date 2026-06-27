package ckhistory.core;

import com.fasterxml.jackson.databind.ObjectMapper;
import ckhistory.models.ReleaseMapping;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

public class MappingLoader {
    private static final Logger log = LoggerFactory.getLogger(MappingLoader.class);
    private final ObjectMapper mapper = new ObjectMapper();

    public Map<String, ReleaseMapping> loadAllMappings(String mappingsDirPath) {
        Map<String, ReleaseMapping> allMappings = new HashMap<>();
        File dir = new File(mappingsDirPath);
        if (!dir.exists() || !dir.isDirectory()) {
            log.error("Mappings directory does not exist or is not a directory: {}", mappingsDirPath);
            return allMappings;
        }

        File[] files = dir.listFiles((d, name) -> name.endsWith(".json"));
        if (files == null) return allMappings;

        for (File file : files) {
            // Ignorar o arquivo de resumo de erros
            if (file.getName().equals("summary_not_found.json")) {
                continue;
            }

            try {
                ReleaseMapping mapping = mapper.readValue(file, ReleaseMapping.class);
                allMappings.put(mapping.getRelease(), mapping);
            } catch (IOException e) {
                log.error("Failed to parse mapping file: {}", file.getAbsolutePath(), e);
            }
        }
        return allMappings;
    }
}
