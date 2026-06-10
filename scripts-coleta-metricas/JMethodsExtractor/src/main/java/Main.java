import evometrics.core.FeatureEvolutorTask;
import evometrics.core.MappingLoader;
import evometrics.core.ProgressTracker;
import evometrics.git.GitEngine;
import evometrics.models.FeatureMapping;
import evometrics.models.ReleaseMapping;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
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
    }

    private static final Map<String, Integer> REPO_MEMORY_COST = new HashMap<>();
    static {
        REPO_MEMORY_COST.put("cdt", 8);
        REPO_MEMORY_COST.put("eclipse.jdt.core", 6);
        REPO_MEMORY_COST.put("eclipse.pde", 4);
        REPO_MEMORY_COST.put("org.eclipse.emf", 4);
        // Outros repositórios usarão o custo padrão de 2GB
    }

    // Hardcoded release order extracted from simrel.build tags
    private static final List<String> ORDERED_RELEASES = Arrays.asList(
            "JunoSR0", "JunoSR1", "JunoSR2", "KeplerPostRC4", "KeplerSR0", "KeplerSR1",
            "LunaSR0", "z20140805-2300", "z20140806", "LunaRC4", "LunaSR2", "S201504150911",
            "Mars.1", "Neon", "OxygenPreRienaRemoval_9-8-2016", "Neon.1", "Neon.1a", "Neon.2",
            "Neon.3", "Neon.3_respin", "Oxygen", "Oxygen.1", "Oxygen.1a_respin", "Oxygen.1a",
            "Oxygen.3", "Oxygen.2", "Oxygen.2_respin", "PhotonM7", "PhotonRC4", "Photon.0",
            "2018-09", "2018-12", "2019-03", "2019-06", "2019-09", "2019-12", "2020-03",
            "2020-06", "2020-09", "2020-12", "2021-03", "2021-06", "2021-09", "2021-12",
            "2022-03", "2022-06", "2022-09", "2022-12", "2023-03", "2023-06", "2023-09",
            "2023-12", "2024-03", "2024-06", "2024-09", "2024-12", "2025-03", "2025-06",
            "2025-09", "2025-12", "2026-03");

    // Test mode limit
    private static final int MAX_RELEASES_TEST_MODE = 3;

    public static void main(String[] args) {
        log.info("Starting EvoMetrics Collector in Java...");

        String basePath = System.getProperty("user.dir");
        if (!new java.io.File(basePath + "/releases/mappings").exists()) {
            java.io.File parent = new java.io.File(basePath).getParentFile();
            if (parent != null && new java.io.File(parent, "releases/mappings").exists()) {
                basePath = parent.getAbsolutePath();
            }
        }
        String mappingsDirPath = basePath + "/releases/mappings";



        boolean testMode = true; // Set to true to stop after JunoSR0 and JunoSR1



        MappingLoader loader = new MappingLoader();
        Map<String, ReleaseMapping> allMappings = loader.loadAllMappings(mappingsDirPath);

        List<String> releasesToProcess = ORDERED_RELEASES;
        // int oxygenIdx = ORDERED_RELEASES.indexOf("Oxygen");
        // if (oxygenIdx != -1) {
        //     // Cut the list from 0 up to (but not including) Oxygen
        //     releasesToProcess = ORDERED_RELEASES.subList(0, oxygenIdx);
        // }

        if (testMode) {
            releasesToProcess = releasesToProcess.subList(0,
                    Math.min(MAX_RELEASES_TEST_MODE, releasesToProcess.size()));
            log.info("TEST MODE ACTIVE: Only processing the first {} releases.", releasesToProcess.size());
        }

        // We want to pivot the data from Release->Feature to Feature->Releases
        // This allows us to run one Thread per Feature.
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
                    FeatureMapping fmap = featureEntry.getValue();

                    featureEvolutionMap.putIfAbsent(featureName, new HashMap<>());
                    featureEvolutionMap.get(featureName).put(release, fmap.getCommit());

                    if (fmap.getRepository() != null && !fmap.getRepository().isEmpty()) {
                        featureRepositoryMap.put(featureName, fmap.getRepository());
                    }
                }
            }
        }

        log.info("Found {} independent features to process.", featureEvolutionMap.size());

        // Verify and clone repositories if they don't exist
        for (String repoName : new HashSet<>(featureRepositoryMap.values())) {
            if (repoName == null || repoName.isEmpty())
                continue;
            java.io.File repoDir = new java.io.File(basePath, repoName);
            if (!repoDir.exists() || !new java.io.File(repoDir, ".git").exists()) {
                String cloneUrl = REPO_URL_MAP.get(repoName);
                if (cloneUrl != null) {
                    log.info("Repository '{}' not found or incomplete. Auto-cloning from {}...", repoName, cloneUrl);
                    boolean cloned = GitEngine.cloneRepository(cloneUrl, repoDir.getAbsolutePath());
                    if (!cloned) {
                        log.error(
                                "Failed to clone repository: {}. Extraction for features using this repository might fail.",
                                repoName);
                    }
                } else {
                    log.warn("No clone URL configured for repository: {}", repoName);
                }
            } else {
                log.info("Repository '{}' already exists and is initialized.", repoName);
            }
        }

        // Dynamically calculate pool size based on available resources to avoid OutOfMemoryError
        int cores = Runtime.getRuntime().availableProcessors();
        long maxMemoryGB = Runtime.getRuntime().maxMemory() / (1024 * 1024 * 1024);
        int totalPermits = (int) Math.max(2, maxMemoryGB); // Minimum 2GB

        log.info("Available Cores: {}, Max Heap Memory: {} GB. Starting Semaphore with {} permits.", cores, maxMemoryGB,
                totalPermits);

        Semaphore availableMemory = new Semaphore(totalPermits, true);
        ExecutorService executor = Executors.newCachedThreadPool();

        ProgressTracker.showGUI();

        // Ordenar as features pelo custo de memória do seu repositório (maior custo
        // primeiro)
        List<String> sortedFeatures = new ArrayList<>(featureEvolutionMap.keySet());
        sortedFeatures.sort((f1, f2) -> {
            String repo1 = featureRepositoryMap.get(f1);
            String repo2 = featureRepositoryMap.get(f2);
            int cost1 = REPO_MEMORY_COST.getOrDefault(repo1, 2);
            int cost2 = REPO_MEMORY_COST.getOrDefault(repo2, 2);
            return Integer.compare(cost2, cost1); // descending order
        });

        for (String featureName : sortedFeatures) {
            String repoName = featureRepositoryMap.get(featureName);
            Map<String, String> releaseToCommitMap = featureEvolutionMap.get(featureName);
            int requiredMemoryGB = Math.min(totalPermits, REPO_MEMORY_COST.getOrDefault(repoName, 2));

            ProgressTracker.initializeFeature(featureName, repoName);

            FeatureEvolutorTask task = new FeatureEvolutorTask(
                    featureName,
                    repoName,
                    basePath,
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

        log.info("All metrics collected successfully.");
    }
}