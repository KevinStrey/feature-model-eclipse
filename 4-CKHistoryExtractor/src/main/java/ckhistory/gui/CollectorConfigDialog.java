package ckhistory.gui;

import ckhistory.models.FeatureMapping;
import ckhistory.models.ReleaseMapping;

import javax.swing.*;
import javax.swing.border.EmptyBorder;
import javax.swing.border.TitledBorder;
import java.awt.*;
import java.awt.event.*;
import java.util.*;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Pre-run configuration dialog for CK Metrics History Collector.
 * The user selects which releases and features to collect, and sets memory limits.
 * Blocks until the user clicks "Start" or closes the window.
 * Returns a {@link CollectionConfig} (or null if cancelled).
 */
public class CollectorConfigDialog extends JDialog {

    // ── Palette ────────────────────────────────────────────────────────────────
    private static final Color BG          = new Color(0x1E, 0x1E, 0x2E);
    private static final Color SURFACE     = new Color(0x28, 0x28, 0x3C);
    private static final Color ACCENT      = new Color(0x74, 0xC7, 0xEC);
    private static final Color ACCENT2     = new Color(0xCB, 0xA6, 0xF7);
    private static final Color TEXT        = new Color(0xCD, 0xD6, 0xF4);
    private static final Color TEXT_DIM    = new Color(0x6C, 0x70, 0x86);
    private static final Color BORDER_COL  = new Color(0x45, 0x47, 0x5A);
    private static final Color BTN_START   = new Color(0xA6, 0xE3, 0xA1);
    private static final Color BTN_CANCEL  = new Color(0xF3, 0x8B, 0xA8);
    private static final Color CHECK_ON    = new Color(0x74, 0xC7, 0xEC);
    private static final Color HOVER_ROW   = new Color(0x31, 0x32, 0x44);

    // ── State ──────────────────────────────────────────────────────────────────
    private final List<String> orderedReleases;
    private final Map<String, ReleaseMapping> allMappings;

    /** All feature names that appear in at least one selected release, sorted. */
    private List<String> allFeatureNames = new ArrayList<>();

    /** Global feature selection state: featureName → selected */
    private final Map<String, Boolean> featureSelected = new LinkedHashMap<>();

    private CollectionConfig result = null;

    // ── UI Components ──────────────────────────────────────────────────────────
    private final Map<String, JCheckBox> releaseCheckboxes = new LinkedHashMap<>();
    private JPanel featuresPanel;
    private JScrollPane featuresScroll;

    private JRadioButton radioUnlimited;
    private JRadioButton radioLimited;
    private JSlider memSlider;
    private JLabel memLabel;
    private JLabel memDetectedLabel;

    // ──────────────────────────────────────────────────────────────────────────
    public CollectorConfigDialog(List<String> orderedReleases,
                                 Map<String, ReleaseMapping> allMappings) {
        super((Frame) null, "CK Metrics History Collector — Configuração", true);
        this.orderedReleases = orderedReleases;
        this.allMappings = allMappings;

        setDefaultCloseOperation(DISPOSE_ON_CLOSE);
        setSize(1050, 720);
        setLocationRelativeTo(null);
        setResizable(true);

        // Compute all feature names across ALL releases up front
        refreshFeatureNames(orderedReleases);

        buildUI();
        // Trigger initial feature panel render
        refreshFeaturesPanel();
    }

    // ─────────────────────────── UI Builder ───────────────────────────────────

    private void buildUI() {
        JPanel root = new JPanel(new BorderLayout(0, 0));
        root.setBackground(BG);
        root.setBorder(new EmptyBorder(12, 12, 12, 12));
        setContentPane(root);

        // Title bar
        root.add(buildTitleBar(), BorderLayout.NORTH);

        // Center: releases + features
        JSplitPane center = buildCenterSplit();
        root.add(center, BorderLayout.CENTER);

        // Bottom: memory + buttons
        root.add(buildBottomPanel(), BorderLayout.SOUTH);
    }

    // ── Title ──────────────────────────────────────────────────────────────────
    private JPanel buildTitleBar() {
        JPanel p = new JPanel(new BorderLayout());
        p.setBackground(BG);
        p.setBorder(new EmptyBorder(0, 4, 12, 4));

        JLabel title = new JLabel("⚙  CK Metrics History Collector");
        title.setFont(new Font("SansSerif", Font.BOLD, 20));
        title.setForeground(ACCENT);

        JLabel sub = new JLabel("Selecione as releases, features e configure a memória antes de iniciar a coleta de métricas CK");
        sub.setFont(new Font("SansSerif", Font.PLAIN, 12));
        sub.setForeground(TEXT_DIM);

        JPanel titles = new JPanel();
        titles.setLayout(new BoxLayout(titles, BoxLayout.Y_AXIS));
        titles.setBackground(BG);
        titles.add(title);
        titles.add(Box.createVerticalStrut(3));
        titles.add(sub);

        p.add(titles, BorderLayout.WEST);

        // Stats label (updated live)
        JLabel stats = new JLabel();
        stats.setFont(new Font("SansSerif", Font.PLAIN, 11));
        stats.setForeground(TEXT_DIM);
        stats.setHorizontalAlignment(SwingConstants.RIGHT);
        p.add(stats, BorderLayout.EAST);

        // Keep stats fresh via a simple timer
        javax.swing.Timer t = new javax.swing.Timer(400, e -> {
            long relCount = releaseCheckboxes.values().stream().filter(AbstractButton::isSelected).count();
            long featCount = featureSelected.values().stream().filter(v -> v).count();
            stats.setText(relCount + " releases  ·  " + featCount + " features selecionadas    ");
        });
        t.start();

        return p;
    }

    // ── Center split ───────────────────────────────────────────────────────────
    private JSplitPane buildCenterSplit() {
        JSplitPane split = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT, buildReleasesPanel(), buildFeaturesContainer());
        split.setDividerLocation(270);
        split.setDividerSize(5);
        split.setBackground(BG);
        split.setBorder(null);
        split.setContinuousLayout(true);
        return split;
    }

    // ── Releases panel (left) ─────────────────────────────────────────────────
    private JPanel buildReleasesPanel() {
        JPanel outer = new JPanel(new BorderLayout(0, 6));
        outer.setBackground(SURFACE);
        outer.setBorder(titledBorder("  Releases  "));

        // Toolbar
        JPanel toolbar = new JPanel(new FlowLayout(FlowLayout.LEFT, 6, 4));
        toolbar.setBackground(SURFACE);
        JButton btnAll  = smallButton("Todas",    ACCENT);
        JButton btnNone = smallButton("Nenhuma", TEXT_DIM);
        btnAll .addActionListener(e -> setAllReleases(true));
        btnNone.addActionListener(e -> setAllReleases(false));
        toolbar.add(btnAll);
        toolbar.add(btnNone);
        outer.add(toolbar, BorderLayout.NORTH);

        // List
        JPanel listPanel = new JPanel();
        listPanel.setLayout(new BoxLayout(listPanel, BoxLayout.Y_AXIS));
        listPanel.setBackground(SURFACE);

        for (String rel : orderedReleases) {
            JCheckBox cb = styledCheckbox(rel);
            cb.setSelected(true);
            cb.addItemListener(e -> onReleasesChanged());
            releaseCheckboxes.put(rel, cb);

            JPanel row = new JPanel(new BorderLayout());
            row.setBackground(SURFACE);
            row.setMaximumSize(new Dimension(Integer.MAX_VALUE, 26));
            row.setBorder(new EmptyBorder(1, 6, 1, 6));
            row.add(cb, BorderLayout.WEST);
            // Add hover highlight
            row.addMouseListener(new MouseAdapter() {
                @Override public void mouseEntered(MouseEvent e) { row.setBackground(HOVER_ROW); }
                @Override public void mouseExited(MouseEvent e)  { row.setBackground(SURFACE); }
            });
            listPanel.add(row);
        }

        JScrollPane scroll = new JScrollPane(listPanel);
        scroll.setBorder(null);
        scroll.setBackground(SURFACE);
        scroll.getViewport().setBackground(SURFACE);
        outer.add(scroll, BorderLayout.CENTER);
        return outer;
    }

    // ── Features container (right) ─────────────────────────────────────────────
    private JPanel buildFeaturesContainer() {
        JPanel outer = new JPanel(new BorderLayout(0, 6));
        outer.setBackground(SURFACE);
        outer.setBorder(titledBorder("  Features (globais — aplicadas a todas as releases marcadas)  "));

        // Toolbar
        JPanel toolbar = new JPanel(new FlowLayout(FlowLayout.LEFT, 6, 4));
        toolbar.setBackground(SURFACE);
        JButton btnAll  = smallButton("Todas",    ACCENT);
        JButton btnNone = smallButton("Nenhuma", TEXT_DIM);

        // Search box
        JTextField searchBox = new JTextField(18);
        styleTextField(searchBox, "🔍 Filtrar features...");
        searchBox.getDocument().addDocumentListener(new javax.swing.event.DocumentListener() {
            public void insertUpdate(javax.swing.event.DocumentEvent e)  { filterFeatures(searchBox.getText()); }
            public void removeUpdate(javax.swing.event.DocumentEvent e)  { filterFeatures(searchBox.getText()); }
            public void changedUpdate(javax.swing.event.DocumentEvent e) { filterFeatures(searchBox.getText()); }
        });

        btnAll .addActionListener(e -> setAllFeatures(true));
        btnNone.addActionListener(e -> setAllFeatures(false));
        toolbar.add(btnAll);
        toolbar.add(btnNone);
        toolbar.add(Box.createHorizontalStrut(12));
        toolbar.add(searchBox);
        outer.add(toolbar, BorderLayout.NORTH);

        // Features list panel (populated dynamically)
        featuresPanel = new JPanel();
        featuresPanel.setLayout(new BoxLayout(featuresPanel, BoxLayout.Y_AXIS));
        featuresPanel.setBackground(SURFACE);

        featuresScroll = new JScrollPane(featuresPanel);
        featuresScroll.setBorder(null);
        featuresScroll.setBackground(SURFACE);
        featuresScroll.getViewport().setBackground(SURFACE);
        outer.add(featuresScroll, BorderLayout.CENTER);
        return outer;
    }

    // ── Memory panel + buttons (bottom) ────────────────────────────────────────
    private JPanel buildBottomPanel() {
        JPanel bottom = new JPanel(new BorderLayout(0, 0));
        bottom.setBackground(BG);
        bottom.setBorder(new EmptyBorder(10, 0, 0, 0));

        bottom.add(buildMemoryPanel(), BorderLayout.CENTER);
        bottom.add(buildButtonBar(),   BorderLayout.EAST);
        return bottom;
    }

    private JPanel buildMemoryPanel() {
        JPanel p = new JPanel();
        p.setLayout(new BoxLayout(p, BoxLayout.Y_AXIS));
        p.setBackground(SURFACE);
        p.setBorder(titledBorder("  Gerenciamento de Memória  "));

        long maxJvmGB = Math.max(1, Runtime.getRuntime().maxMemory() / (1024L * 1024L * 1024L));
        java.lang.management.OperatingSystemMXBean rawOsMxBean =
                java.lang.management.ManagementFactory.getOperatingSystemMXBean();
        long totalRamGB;
        if (rawOsMxBean instanceof com.sun.management.OperatingSystemMXBean) {
            com.sun.management.OperatingSystemMXBean osMxBean =
                    (com.sun.management.OperatingSystemMXBean) rawOsMxBean;
            totalRamGB = Math.max(1, osMxBean.getTotalPhysicalMemorySize() / (1024L * 1024L * 1024L));
        } else {
            totalRamGB = maxJvmGB;
        }
        int sliderMax = (int) Math.max(4, Math.min(totalRamGB, 128));
        int sliderDef = (int) Math.max(2, maxJvmGB);

        // Detect label
        memDetectedLabel = new JLabel("  RAM total detectada: ~" + totalRamGB + " GB   |   Heap JVM configurada: ~" + maxJvmGB + " GB");
        memDetectedLabel.setFont(new Font("SansSerif", Font.PLAIN, 11));
        memDetectedLabel.setForeground(TEXT_DIM);

        radioUnlimited = styledRadio("🚀  Ilimitada — processa todas as features em paralelo (computadores potentes)");
        radioLimited   = styledRadio("🔒  Limitada — usa um Semaphore para restringir o uso máximo de RAM");
        radioLimited.setSelected(true);

        ButtonGroup bg = new ButtonGroup();
        bg.add(radioUnlimited);
        bg.add(radioLimited);

        // Slider row
        JPanel sliderRow = new JPanel(new FlowLayout(FlowLayout.LEFT, 8, 2));
        sliderRow.setBackground(SURFACE);
        JLabel sliderPre = dimLabel("  Máximo:  ");
        memSlider = new JSlider(2, sliderMax, sliderDef);
        memSlider.setBackground(SURFACE);
        memSlider.setForeground(ACCENT);
        memSlider.setMajorTickSpacing(Math.max(1, sliderMax / 8));
        memSlider.setPaintTicks(true);
        memSlider.setPaintLabels(true);
        memSlider.setPreferredSize(new Dimension(380, 45));
        memLabel = new JLabel(sliderDef + " GB");
        memLabel.setFont(new Font("SansSerif", Font.BOLD, 13));
        memLabel.setForeground(ACCENT2);
        memSlider.addChangeListener(e -> memLabel.setText(memSlider.getValue() + " GB"));
        sliderRow.add(sliderPre);
        sliderRow.add(memSlider);
        sliderRow.add(memLabel);

        radioUnlimited.addItemListener(e -> {
            boolean limited = !radioUnlimited.isSelected();
            memSlider.setEnabled(limited);
        });
        radioLimited.addItemListener(e -> {
            boolean limited = radioLimited.isSelected();
            memSlider.setEnabled(limited);
        });

        p.add(Box.createVerticalStrut(4));
        p.add(memDetectedLabel);
        p.add(Box.createVerticalStrut(6));
        p.add(radioUnlimited);
        p.add(Box.createVerticalStrut(3));
        p.add(radioLimited);
        p.add(sliderRow);
        p.add(Box.createVerticalStrut(4));
        return p;
    }

    private JPanel buildButtonBar() {
        JPanel bar = new JPanel(new FlowLayout(FlowLayout.RIGHT, 10, 10));
        bar.setBackground(BG);

        JButton cancel = actionButton("  Cancelar  ", BTN_CANCEL);
        JButton start  = actionButton("  ▶  Iniciar Coleta CK  ", BTN_START);

        cancel.addActionListener(e -> dispose());
        start .addActionListener(e -> onStart());

        bar.add(cancel);
        bar.add(start);
        return bar;
    }

    // ──────────────────────────── Logic ───────────────────────────────────────

    /** Re-computes the union of all features across the currently selected releases. */
    private void refreshFeatureNames(List<String> releasesToConsider) {
        Set<String> names = new TreeSet<>();
        for (String rel : releasesToConsider) {
            ReleaseMapping rm = allMappings.get(rel);
            if (rm != null && rm.getMappings() != null) {
                names.addAll(rm.getMappings().keySet());
            }
        }
        allFeatureNames = new ArrayList<>(names);
        // Preserve existing selections; new features default to selected
        for (String name : allFeatureNames) {
            featureSelected.putIfAbsent(name, Boolean.TRUE);
        }
        // Remove features that no longer appear in any selected release
        featureSelected.keySet().retainAll(names);
    }

    private void onReleasesChanged() {
        List<String> selectedRels = releaseCheckboxes.entrySet().stream()
                .filter(e -> e.getValue().isSelected())
                .map(Map.Entry::getKey)
                .collect(Collectors.toList());
        refreshFeatureNames(selectedRels);
        refreshFeaturesPanel();
    }

    private void refreshFeaturesPanel() {
        filterFeatures("");
    }

    private void filterFeatures(String query) {
        String q = query.trim().toLowerCase();
        featuresPanel.removeAll();

        for (String name : allFeatureNames) {
            if (!q.isEmpty() && !name.toLowerCase().contains(q)) continue;

            JCheckBox cb = styledCheckbox(name);
            cb.setSelected(Boolean.TRUE.equals(featureSelected.get(name)));
            cb.addItemListener(e -> featureSelected.put(name, cb.isSelected()));

            JPanel row = new JPanel(new BorderLayout());
            row.setBackground(SURFACE);
            row.setMaximumSize(new Dimension(Integer.MAX_VALUE, 26));
            row.setBorder(new EmptyBorder(1, 6, 1, 6));
            row.add(cb, BorderLayout.WEST);
            row.addMouseListener(new MouseAdapter() {
                @Override public void mouseEntered(MouseEvent e) { row.setBackground(HOVER_ROW); cb.setBackground(HOVER_ROW); }
                @Override public void mouseExited (MouseEvent e) { row.setBackground(SURFACE);    cb.setBackground(SURFACE); }
            });
            featuresPanel.add(row);
        }

        featuresPanel.revalidate();
        featuresPanel.repaint();
    }

    private void setAllReleases(boolean selected) {
        releaseCheckboxes.values().forEach(cb -> cb.setSelected(selected));
        onReleasesChanged();
    }

    private void setAllFeatures(boolean selected) {
        featureSelected.keySet().forEach(k -> featureSelected.put(k, selected));
        refreshFeaturesPanel();
    }

    private void onStart() {
        List<String> selectedReleases = orderedReleases.stream()
                .filter(r -> {
                    JCheckBox cb = releaseCheckboxes.get(r);
                    return cb != null && cb.isSelected();
                })
                .collect(Collectors.toList());

        if (selectedReleases.isEmpty()) {
            JOptionPane.showMessageDialog(this,
                    "Selecione pelo menos uma release antes de iniciar.",
                    "Nenhuma release selecionada", JOptionPane.WARNING_MESSAGE);
            return;
        }

        Set<String> selectedFeats = featureSelected.entrySet().stream()
                .filter(Map.Entry::getValue)
                .map(Map.Entry::getKey)
                .collect(Collectors.toSet());

        if (selectedFeats.isEmpty()) {
            JOptionPane.showMessageDialog(this,
                    "Selecione pelo menos uma feature antes de iniciar.",
                    "Nenhuma feature selecionada", JOptionPane.WARNING_MESSAGE);
            return;
        }

        boolean unlimited = radioUnlimited.isSelected();
        int memGB = memSlider.getValue();

        result = new CollectionConfig(selectedReleases, selectedFeats, unlimited, memGB);
        dispose();
    }

    /** Returns null if the user cancelled. */
    public CollectionConfig getResult() {
        return result;
    }

    // ──────────────────────────── Style helpers ────────────────────────────────

    private TitledBorder titledBorder(String title) {
        TitledBorder b = BorderFactory.createTitledBorder(
                BorderFactory.createLineBorder(BORDER_COL, 1, true), title);
        b.setTitleColor(ACCENT);
        b.setTitleFont(new Font("SansSerif", Font.BOLD, 12));
        return b;
    }

    private JCheckBox styledCheckbox(String label) {
        JCheckBox cb = new JCheckBox(label);
        cb.setBackground(SURFACE);
        cb.setForeground(TEXT);
        cb.setFont(new Font("Monospaced", Font.PLAIN, 12));
        cb.setFocusPainted(false);
        cb.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
        return cb;
    }

    private JRadioButton styledRadio(String label) {
        JRadioButton rb = new JRadioButton(label);
        rb.setBackground(SURFACE);
        rb.setForeground(TEXT);
        rb.setFont(new Font("SansSerif", Font.PLAIN, 12));
        rb.setFocusPainted(false);
        rb.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
        rb.setBorder(new EmptyBorder(2, 8, 2, 8));
        return rb;
    }

    private JButton smallButton(String text, Color fg) {
        JButton b = new JButton(text);
        b.setFont(new Font("SansSerif", Font.BOLD, 11));
        b.setForeground(fg);
        b.setBackground(BG);
        b.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createLineBorder(BORDER_COL, 1, true),
                new EmptyBorder(2, 8, 2, 8)));
        b.setFocusPainted(false);
        b.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
        b.addMouseListener(new MouseAdapter() {
            @Override public void mouseEntered(MouseEvent e) { b.setBackground(HOVER_ROW); }
            @Override public void mouseExited (MouseEvent e) { b.setBackground(BG); }
        });
        return b;
    }

    private JButton actionButton(String text, Color fg) {
        JButton b = new JButton(text);
        b.setFont(new Font("SansSerif", Font.BOLD, 13));
        b.setForeground(new Color(0x1E, 0x1E, 0x2E));
        b.setBackground(fg);
        b.setBorder(new EmptyBorder(8, 18, 8, 18));
        b.setFocusPainted(false);
        b.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
        b.addMouseListener(new MouseAdapter() {
            @Override public void mouseEntered(MouseEvent e) { b.setBackground(fg.brighter()); }
            @Override public void mouseExited (MouseEvent e) { b.setBackground(fg); }
        });
        return b;
    }

    private JLabel dimLabel(String text) {
        JLabel l = new JLabel(text);
        l.setFont(new Font("SansSerif", Font.PLAIN, 12));
        l.setForeground(TEXT_DIM);
        return l;
    }

    private void styleTextField(JTextField tf, String placeholder) {
        tf.setBackground(BG);
        tf.setForeground(TEXT_DIM);
        tf.setCaretColor(TEXT);
        tf.setFont(new Font("SansSerif", Font.PLAIN, 12));
        tf.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createLineBorder(BORDER_COL, 1, true),
                new EmptyBorder(3, 8, 3, 8)));
        tf.setText(placeholder);
        tf.setForeground(TEXT_DIM);
        tf.addFocusListener(new FocusAdapter() {
            @Override public void focusGained(FocusEvent e) {
                if (tf.getText().equals(placeholder)) { tf.setText(""); tf.setForeground(TEXT); }
            }
            @Override public void focusLost(FocusEvent e) {
                if (tf.getText().isEmpty()) { tf.setText(placeholder); tf.setForeground(TEXT_DIM); }
            }
        });
    }

    // ──────────────────────────── Entry point ─────────────────────────────────

    /**
     * Shows the dialog modally and returns the user's config, or null if cancelled.
     */
    public static CollectionConfig show(List<String> orderedReleases,
                                        Map<String, ReleaseMapping> allMappings) {
        System.setProperty("java.awt.headless", "false");
        // Apply a dark-ish Nimbus look if available
        try {
            for (UIManager.LookAndFeelInfo info : UIManager.getInstalledLookAndFeels()) {
                if ("Nimbus".equals(info.getName())) {
                    UIManager.setLookAndFeel(info.getClassName());
                    // Override Nimbus tokens for our dark palette
                    UIManager.put("nimbusBase",            BG);
                    UIManager.put("nimbusBlueGrey",        SURFACE);
                    UIManager.put("control",               SURFACE);
                    UIManager.put("text",                  TEXT);
                    UIManager.put("nimbusFocus",           ACCENT);
                    UIManager.put("nimbusSelectionBackground", ACCENT);
                    break;
                }
            }
        } catch (Exception ignored) { /* fall back to default L&F */ }

        CollectorConfigDialog dlg = new CollectorConfigDialog(orderedReleases, allMappings);
        dlg.setVisible(true); // blocks until disposed
        return dlg.getResult();
    }
}
