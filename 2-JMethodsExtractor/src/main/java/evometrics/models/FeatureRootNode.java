package evometrics.models;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public class FeatureRootNode {
    @JsonProperty("status")
    private String status;

    @JsonProperty("details")
    private FeatureMapping details;

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public FeatureMapping getDetails() { return details; }
    public void setDetails(FeatureMapping details) { this.details = details; }
}
