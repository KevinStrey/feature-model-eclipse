import ckhistory.core.FeatureCKTask;
import ckhistory.core.MappingLoader;
import ckhistory.core.ProgressTracker;
import ckhistory.git.GitCheckoutEngine;
import ckhistory.gui.CollectionConfig;
import ckhistory.gui.CollectorConfigDialog;
import ckhistory.models.FeatureMapping;
import ckhistory.models.ReleaseMapping;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;

public class Main {
    private static final Logger log = LoggerFactory.getLogger(Main.class);

    private static final Map<String, String> REPO_URL_MAP = new HashMap<>();
    static {
        REPO_URL_MAP.put("eclipse.jdt.core", "https://github.com/eclipse-jdt/eclipse.jdt.core.git");
        REPO_URL_MAP.put("eclipse.pde", "https://github.com/eclipse-pde/eclipse.pde.git");
        REPO_URL_MAP.put("cdt", "https://github.com/eclipse-cdt/cdt.git");
        REPO_URL_MAP.put("gef-classic", "https://github.com/eclipse/gef-classic.git");
        REPO_URL_MAP.put("gef", "https://github.com/eclipse/gef-classic.git");
        REPO_URL_MAP.put("org.eclipse.emf", "https://github.com/eclipse-emf/org.eclipse.emf.git");
        REPO_URL_MAP.put("birt", "https://github.com/eclipse-birt/birt.git");
        REPO_URL_MAP.put("datatools", "https://github.com/eclipse-datatools/datatools.git");
        REPO_URL_MAP.put("eclipselink", "https://github.com/eclipse-ee4j/eclipselink.git");
        REPO_URL_MAP.put("egit", "https://github.com/eclipse-egit/egit.git");
        REPO_URL_MAP.put("gmf-runtime", "https://github.com/eclipse-gmf-runtime/gmf-runtime.git");
        REPO_URL_MAP.put("org.eclipse.mylyn", "https://github.com/eclipse-mylyn/org.eclipse.mylyn.git");
        REPO_URL_MAP.put("org.eclipse.rap", "https://github.com/eclipse-rap/org.eclipse.rap.git");
        REPO_URL_MAP.put("ptp", "https://github.com/eclipse-ptp/ptp.git");
        REPO_URL_MAP.put("scout.rt", "https://github.com/eclipse-scout/scout.rt.git");
        REPO_URL_MAP.put("webtools.javaee", "https://github.com/eclipse-jeetools/webtools.javaee.git");
        REPO_URL_MAP.put("windowbuilder", "https://github.com/eclipse-windowbuilder/windowbuilder.git");
        REPO_URL_MAP.put("m2e-core", "https://github.com/eclipse-m2e/m2e-core.git");
        REPO_URL_MAP.put("eclipse.cvs", "https://github.com/JAndrassy/org.eclipse.team.cvs.git");
        REPO_URL_MAP.put("subclipse", "https://github.com/subclipse/subclipse.git");
    }

    private static final Map<String, Integer> REPO_MEMORY_COST = new HashMap<>();
    static {
        REPO_MEMORY_COST.put("cdt", 8);
        REPO_MEMORY_COST.put("eclipse.jdt.core", 6);
        REPO_MEMORY_COST.put("eclipse.pde", 4);
        REPO_MEMORY_COST.put("org.eclipse.emf", 4);
        // Other repositories use the default cost of 2 GB
    }

    // ─────────────────────────────────────────────────────────────────────────
    public static void main(String[] args) {
        log.info("Starting CK Metrics History Collector...");

        java.io.File currentDir = new java.io.File(System.getProperty("user.dir")).getAbsoluteFile();
        java.io.File rootDir = currentDir;
        while (rootDir != null && !rootDir.getName().equalsIgnoreCase("Feature-models")) {
            rootDir = rootDir.getParentFile();
        }
        if (rootDir == null) {
            // Fallback: assume run from 4-CKHistoryExtractor or 4-CKHistoryExtractor/target
            if (currentDir.getName().equals("target")) {
                rootDir = new java.io.File(currentDir, "../../").getAbsoluteFile();
            } else {
                rootDir = new java.io.File(currentDir, "../").getAbsoluteFile();
            }
        }

        String reposDirPath = new java.io.File(rootDir, "1-Repositorios").getAbsolutePath();
        String mappingsDirPath = new java.io.File(rootDir, "3-Mapeamento_features_simrel/simrel_mapper/output").getAbsolutePath();

        log.info("Repositorios Directory: {}", reposDirPath);
        log.info("Mappings Directory: {}", mappingsDirPath);

        MappingLoader loader = new MappingLoader();
        Map<String, ReleaseMapping> allMappings = loader.loadAllMappings(mappingsDirPath);

        List<String> orderedReleases = new java.util.ArrayList<>(allMappings.keySet());
        orderedReleases.sort((r1, r2) -> {
            String d1 = allMappings.get(r1).getDate();
            String d2 = allMappings.get(r2).getDate();
            if (d1 == null) d1 = "";
            if (d2 == null) d2 = "";
            return d1.compareTo(d2);
        });

        // ── Show configuration GUI ─────────────────────────────────────────────
        CollectionConfig config = CollectorConfigDialog.show(orderedReleases, allMappings);

        if (config == null) {
            log.info("User cancelled. Exiting.");
            System.exit(0);
        }

        log.info("Configuration received: {} releases, {} features selected, memory={}",
                config.selectedReleases.size(),
                config.selectedFeatures.size(),
                config.unlimitedMemory ? "UNLIMITED" : config.maxMemoryGB + " GB");

        startCollection(config, allMappings, reposDirPath);
    }

    // ─────────────────────────────────────────────────────────────────────────
    static void startCollection(CollectionConfig config,
                                Map<String, ReleaseMapping> allMappings,
                                String reposDirPath) {

        List<String> releasesToProcess = config.selectedReleases;
        Set<String> featureFilter      = config.selectedFeatures; // null → all

        // Pivot data: Feature → (Release → CommitHash)
        Map<String, Map<String, String>> featureEvolutionMap = new HashMap<>();
        Map<String, String> featureRepositoryMap = new HashMap<>();

        for (String release : releasesToProcess) {
            ReleaseMapping mapping = allMappings.get(release);
            if (mapping == null) {
                log.warn("Mapping file not found for release: {}", release);
                continue;
            }
            if (mapping.getMappings() != null) {
                for (Map.Entry<String, FeatureMapping> featureEntry : mapping.getMappings().entrySet()) {
                    String featureName = featureEntry.getKey();

                    // Apply feature filter
                    if (featureFilter != null && !featureFilter.contains(featureName)) continue;

                    FeatureMapping fmap = featureEntry.getValue();

                    featureEvolutionMap.putIfAbsent(featureName, new HashMap<>());
                    featureEvolutionMap.get(featureName).put(release, fmap.getCommit());

                    if (fmap.getRepository() != null && !fmap.getRepository().isEmpty()) {
                        featureRepositoryMap.put(featureName, fmap.getRepository());
                    }
                }
            }
        }

        log.info("Found {} features to process.", featureEvolutionMap.size());

        // Verify / clone repositories
        for (String repoName : new HashSet<>(featureRepositoryMap.values())) {
            if (repoName == null || repoName.isEmpty()) continue;
            java.io.File repoDir = new java.io.File(reposDirPath, repoName);
            if (!repoDir.exists() || !new java.io.File(repoDir, ".git").exists()) {
                String cloneUrl = REPO_URL_MAP.get(repoName);
                if (cloneUrl != null) {
                    log.info("Repository '{}' not found. Auto-cloning from {}...", repoName, cloneUrl);
                    boolean cloned = GitCheckoutEngine.cloneRepository(cloneUrl, repoDir.getAbsolutePath());
                    if (!cloned) {
                        log.error("Failed to clone repository: {}. Extraction may fail.", repoName);
                    }
                } else {
                    log.warn("No clone URL configured for repository: {}", repoName);
                }
            } else {
                log.info("Repository '{}' already exists.", repoName);
            }
        }

        // ── Memory / concurrency setup ────────────────────────────────────────
        int totalPermits;
        if (config.unlimitedMemory) {
            totalPermits = Integer.MAX_VALUE;
            log.info("Memory mode: UNLIMITED (all features run in parallel with no memory cap).");
        } else {
            totalPermits = config.maxMemoryGB;
            log.info("Memory mode: LIMITED to {} GB (Semaphore with {} permits).", totalPermits, totalPermits);
        }

        Semaphore availableMemory = new Semaphore(totalPermits, true);
        ExecutorService executor = Executors.newCachedThreadPool();

        ProgressTracker.showGUI();

        // Sort features by memory cost (heaviest first for better scheduling)
        List<String> sortedFeatures = new ArrayList<>(featureEvolutionMap.keySet());
        sortedFeatures.sort((f1, f2) -> {
            String repo1 = featureRepositoryMap.get(f1);
            String repo2 = featureRepositoryMap.get(f2);
            int cost1 = resolveMemoryCost(repo1, config, totalPermits);
            int cost2 = resolveMemoryCost(repo2, config, totalPermits);
            return Integer.compare(cost2, cost1); // descending
        });

        for (String featureName : sortedFeatures) {
            String repoName = featureRepositoryMap.get(featureName);
            Map<String, String> releaseToCommitMap = featureEvolutionMap.get(featureName);

            int requiredMemoryGB;
            if (config.unlimitedMemory) {
                requiredMemoryGB = 1; // acquire 1 permit each — always succeeds instantly
            } else {
                requiredMemoryGB = Math.min(totalPermits, REPO_MEMORY_COST.getOrDefault(repoName, 2));
            }

            ProgressTracker.initializeFeature(featureName, repoName);

            FeatureCKTask task = new FeatureCKTask(
                    featureName,
                    repoName,
                    reposDirPath,
                    releasesToProcess,
                    releaseToCommitMap,
                    availableMemory,
                    requiredMemoryGB);
            executor.submit(task);
        }

        executor.shutdown();
        try {
            executor.awaitTermination(Long.MAX_VALUE, TimeUnit.MILLISECONDS);
        } catch (InterruptedException e) {
            log.error("Execution interrupted", e);
        }

        log.info("All CK metrics collected successfully.");
    }

    private static int resolveMemoryCost(String repoName, CollectionConfig config, int totalPermits) {
        if (config.unlimitedMemory) return 1;
        return Math.min(totalPermits, REPO_MEMORY_COST.getOrDefault(repoName, 2));
    }
}
