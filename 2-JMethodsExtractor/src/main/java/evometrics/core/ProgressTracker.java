package evometrics.core;

import javax.swing.*;
import javax.swing.table.DefaultTableModel;
import java.awt.*;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class ProgressTracker {
    private static final Map<String, String[]> featureStatusMap = new ConcurrentHashMap<>();
    private static DefaultTableModel tableModel;
    private static JFrame frame;

    // Catppuccin Mocha Palette
    private static final Color BG          = new Color(0x1E, 0x1E, 0x2E);
    private static final Color SURFACE     = new Color(0x28, 0x28, 0x3C);
    private static final Color ACCENT      = new Color(0x74, 0xC7, 0xEC);
    private static final Color TEXT        = new Color(0xCD, 0xD6, 0xF4);
    private static final Color BORDER_COL  = new Color(0x45, 0x47, 0x5A);
    private static final Color HOVER_ROW   = new Color(0x31, 0x32, 0x44);

    public static void initializeFeature(String featureName, String repositoryName) {
        featureStatusMap.put(featureName, new String[]{featureName, repositoryName, "Initializing..."});
    }

    public static void updateStatus(String featureName, String status) {
        String[] data = featureStatusMap.get(featureName);
        if (data != null) {
            data[2] = status;
        }
    }

    public static void showGUI() {
        // Remover a checagem Headless para forçar a abertura da janela.
        // Se houver algum erro de display, o Java lançará uma exceção explícita.
        System.setProperty("java.awt.headless", "false");

        SwingUtilities.invokeLater(() -> {
            frame = new JFrame("EvoMetrics Extraction Progress");
            frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
            frame.setSize(1000, 600);
            frame.getContentPane().setBackground(BG);

            String[] columnNames = {"Feature", "Repository", "Status / Progress"};
            tableModel = new DefaultTableModel(columnNames, 0) {
                @Override
                public boolean isCellEditable(int row, int column) {
                    return false;
                }
            };

            JTable table = new JTable(tableModel);
            table.setBackground(SURFACE);
            table.setForeground(TEXT);
            table.setFont(new Font("SansSerif", Font.PLAIN, 13));
            table.setRowHeight(28);
            table.setGridColor(BORDER_COL);
            table.setShowGrid(true);
            table.setFillsViewportHeight(true);

            // Selection styles
            table.setSelectionBackground(HOVER_ROW);
            table.setSelectionForeground(TEXT);

            // Column widths
            table.getColumnModel().getColumn(0).setPreferredWidth(200);
            table.getColumnModel().getColumn(1).setPreferredWidth(150);
            table.getColumnModel().getColumn(2).setPreferredWidth(650);

            // Table Header styling
            javax.swing.table.JTableHeader header = table.getTableHeader();
            header.setBackground(BG);
            header.setForeground(ACCENT);
            header.setFont(new Font("SansSerif", Font.BOLD, 13));
            header.setReorderingAllowed(false);
            header.setDefaultRenderer(new javax.swing.table.DefaultTableCellRenderer() {
                @Override
                public Component getTableCellRendererComponent(JTable t, Object value, boolean isSelected, boolean hasFocus, int row, int column) {
                    super.getTableCellRendererComponent(t, value, isSelected, hasFocus, row, column);
                    setBackground(BG);
                    setForeground(ACCENT);
                    setFont(new Font("SansSerif", Font.BOLD, 13));
                    setBorder(BorderFactory.createMatteBorder(0, 0, 1, 1, BORDER_COL));
                    setHorizontalAlignment(JLabel.LEFT);
                    return this;
                }
            });

            // Cell rendering style (left/right padding and colors)
            javax.swing.table.DefaultTableCellRenderer cellRenderer = new javax.swing.table.DefaultTableCellRenderer() {
                @Override
                public Component getTableCellRendererComponent(JTable t, Object value, boolean isSelected, boolean hasFocus, int row, int column) {
                    Component c = super.getTableCellRendererComponent(t, value, isSelected, hasFocus, row, column);
                    if (isSelected) {
                        c.setBackground(HOVER_ROW);
                        c.setForeground(TEXT);
                    } else {
                        c.setBackground(SURFACE);
                        c.setForeground(TEXT);
                    }
                    if (c instanceof JLabel) {
                        JLabel label = (JLabel) c;
                        label.setBorder(BorderFactory.createEmptyBorder(0, 8, 0, 8));
                    }
                    return c;
                }
            };

            for (int i = 0; i < table.getColumnCount(); i++) {
                table.getColumnModel().getColumn(i).setCellRenderer(cellRenderer);
            }

            JScrollPane scrollPane = new JScrollPane(table);
            scrollPane.setBackground(BG);
            scrollPane.getViewport().setBackground(BG);
            scrollPane.setBorder(BorderFactory.createLineBorder(BORDER_COL, 1));
            frame.add(scrollPane, BorderLayout.CENTER);

            Timer timer = new Timer(500, e -> refreshTable());
            timer.start();

            frame.setLocationRelativeTo(null);
            frame.setVisible(true);
        });
    }

    private static void refreshTable() {
        tableModel.setRowCount(0);
        featureStatusMap.values().stream()
            .sorted((a, b) -> a[0].compareTo(b[0]))
            .forEach(rowData -> tableModel.addRow(rowData));
    }
}
