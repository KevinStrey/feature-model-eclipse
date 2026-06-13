package evometrics.models;

import java.util.HashMap;
import java.util.Map;

public class MethodState {
    private final String methodId;
    
    public int bom = 0;
    public int fch = 0;
    public int lch = 0;
    public int frch = 0;
    public int wfr = 0;
    public int csb = 0;
    public int csbsBase = 0;
    public double acdfSum = 0.0;

    public Map<Integer, Integer> tachPerCommit = new HashMap<>();
    public Map<Integer, Double> chdPerCommit = new HashMap<>();

    public int lca = 0;
    public double lcd = 0.0;

    // Additional info to track if it's currently alive
    public boolean isAlive = true;
    public String currentCode = "";
    public int loc = 0;
    
    public MethodState(String methodId) {
        this.methodId = methodId;
    }

    public String getMethodId() {
        return methodId;
    }

    public void onSeen(int commitIndex, int nloc) {
        if (this.bom == 0) {
            this.bom = commitIndex;
            this.csbsBase = nloc;
        }
        this.loc = nloc;
    }

    public void onChange(int commitIndex, int tach, int locCurrent) {
        if (this.fch == 0) {
            this.fch = commitIndex;
        }
        this.lch = commitIndex;
        this.frch += 1;
        this.csb += tach;

        double chd = (locCurrent > 0) ? ((double) tach / locCurrent) : 0.0;

        tachPerCommit.put(commitIndex, tachPerCommit.getOrDefault(commitIndex, 0) + tach);
        chdPerCommit.put(commitIndex, chdPerCommit.getOrDefault(commitIndex, 0.0) + chd);

        this.lca = tach;
        this.lcd = chd;
        this.acdfSum += chd;
        this.loc = locCurrent;
    }

    public double getWch(int currentCommitIndex) {
        double wch = 0.0;
        for (Map.Entry<Integer, Integer> entry : tachPerCommit.entrySet()) {
            int r = entry.getKey();
            if (r > this.bom && r <= currentCommitIndex) {
                double w = Math.pow(2, r - currentCommitIndex);
                wch += entry.getValue() * w;
            }
        }
        return wch;
    }

    public double getWcd(int currentCommitIndex) {
        double wcd = 0.0;
        for (Map.Entry<Integer, Double> entry : chdPerCommit.entrySet()) {
            int r = entry.getKey();
            if (r > this.bom && r <= currentCommitIndex) {
                double w = Math.pow(2, r - currentCommitIndex);
                wcd += entry.getValue() * w;
            }
        }
        return wcd;
    }

    public double getCsbs() {
        return (this.csbsBase > 0) ? ((double) this.csb / this.csbsBase) : 0.0;
    }

    public double getAcdf() {
        return (this.frch > 0) ? (this.acdfSum / this.frch) : 0.0;
    }
}
