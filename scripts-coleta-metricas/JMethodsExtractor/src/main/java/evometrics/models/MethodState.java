package evometrics.models;

import java.util.ArrayList;
import java.util.List;

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

    public List<Integer> tachHist = new ArrayList<>();
    public List<Double> chdHist = new ArrayList<>();

    public int lca = 0;
    public double lcd = 0.0;

    // Additional info to track if it's currently alive
    public boolean isAlive = true;
    public String currentCode = "";
    
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
    }

    public void onChange(int commitIndex, int tach, int locCurrent) {
        if (this.fch == 0) {
            this.fch = commitIndex;
        }
        this.lch = commitIndex;
        this.frch += 1;
        this.csb += tach;

        double chd = (locCurrent > 0) ? ((double) tach / locCurrent) : 0.0;

        int idx = commitIndex - this.bom;
        if (idx < 0) idx = 0;

        ensureCapacity(this.tachHist, idx + 1, 0);
        ensureCapacity(this.chdHist, idx + 1, 0.0);

        this.tachHist.set(idx, tach);
        this.chdHist.set(idx, chd);

        this.lca = tach;
        this.lcd = chd;
        this.acdfSum += chd;
    }

    public void onNoChange(int commitIndex) {
        int idx = commitIndex - this.bom;
        if (idx < 0) return;

        ensureCapacity(this.tachHist, idx + 1, 0);
        ensureCapacity(this.chdHist, idx + 1, 0.0);

        this.tachHist.set(idx, 0);
        this.chdHist.set(idx, 0.0);
    }

    private <T> void ensureCapacity(List<T> list, int size, T defaultValue) {
        while (list.size() < size) {
            list.add(defaultValue);
        }
    }

    public double getWch(int currentCommitIndex) {
        double wch = 0.0;
        for (int r = this.bom + 1; r <= currentCommitIndex; r++) {
            int idx = r - this.bom;
            if (idx < this.tachHist.size()) {
                double w = Math.pow(2, r - currentCommitIndex);
                wch += this.tachHist.get(idx) * w;
            }
        }
        return wch;
    }

    public double getWcd(int currentCommitIndex) {
        double wcd = 0.0;
        for (int r = this.bom + 1; r <= currentCommitIndex; r++) {
            int idx = r - this.bom;
            if (idx < this.chdHist.size()) {
                double w = Math.pow(2, r - currentCommitIndex);
                wcd += this.chdHist.get(idx) * w;
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
