package evometrics.models;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ReleaseMapping {
    @JsonProperty("release")
    private String release;

    @JsonProperty("mappings")
    private Map<String, FeatureMapping> mappings;

    public String getRelease() { return release; }
    public void setRelease(String release) { this.release = release; }

    public Map<String, FeatureMapping> getMappings() { return mappings; }
    public void setMappings(Map<String, FeatureMapping> mappings) { this.mappings = mappings; }
}
