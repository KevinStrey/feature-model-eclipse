package evometrics.models;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public class FeatureMapping {
    @JsonProperty("version")
    private String version;

    @JsonProperty("status")
    private String status;

    @JsonProperty("commit")
    private String commit;

    @JsonProperty("repository")
    private String repository;

    public String getVersion() { return version; }
    public void setVersion(String version) { this.version = version; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public String getCommit() { return commit; }
    public void setCommit(String commit) { this.commit = commit; }
    public String getRepository() { return repository; }
    public void setRepository(String repository) { this.repository = repository; }
}
