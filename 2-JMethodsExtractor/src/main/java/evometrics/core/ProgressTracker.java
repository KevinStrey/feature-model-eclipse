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

            String[] columnNames = {"Feature", "Repository", "Status / Progress"};
            tableModel = new DefaultTableModel(columnNames, 0) {
                @Override
                public boolean isCellEditable(int row, int column) {
                    return false;
                }
            };

            JTable table = new JTable(tableModel);
            table.getColumnModel().getColumn(0).setPreferredWidth(200);
            table.getColumnModel().getColumn(1).setPreferredWidth(150);
            table.getColumnModel().getColumn(2).setPreferredWidth(650);

            JScrollPane scrollPane = new JScrollPane(table);
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
