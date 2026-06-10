package evometrics.gui;

import java.util.List;
import java.util.Set;

/**
 * Carries the user's choices from the CollectorConfigDialog to Main.startCollection().
 */
public class CollectionConfig {

    /** Releases selected by the user, in chronological order. */
    public final List<String> selectedReleases;

    /**
     * Features selected globally (their names match feature keys in the mapping files).
     * If null, ALL features are included.
     */
    public final Set<String> selectedFeatures;

    /** If true, the Semaphore is effectively unlimited (max-throughput mode). */
    public final boolean unlimitedMemory;

    /** Maximum memory in GB used as Semaphore permits when unlimitedMemory == false. */
    public final int maxMemoryGB;

    public CollectionConfig(List<String> selectedReleases,
                            Set<String> selectedFeatures,
                            boolean unlimitedMemory,
                            int maxMemoryGB) {
        this.selectedReleases = selectedReleases;
        this.selectedFeatures = selectedFeatures;
        this.unlimitedMemory = unlimitedMemory;
        this.maxMemoryGB = maxMemoryGB;
    }
}
