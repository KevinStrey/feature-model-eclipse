package ckhistory.core;

import com.github.mauricioaniche.ck.CKClassResult;
import com.github.mauricioaniche.ck.CKMethodResult;
import com.opencsv.CSVWriter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.Map;

public class CKCsvExporter implements AutoCloseable {
    private static final Logger log = LoggerFactory.getLogger(CKCsvExporter.class);

    private final CSVWriter classWriter;
    private final CSVWriter methodWriter;
    private final String feature;
    private int classRowCount = 0;
    private int methodRowCount = 0;

    private static final String[] CLASS_HEADER = {
            "project", "release", "commitIndex", "commitHash",
            "file", "class", "type",
            /* OO Metrics */
            "cbo", "cboModified", "fanin", "fanout",
            "wmc", "dit", "noc", "rfc",
            "lcom", "lcom*", "tcc", "lcc",
            /* Method Counting */
            "totalMethodsQty", "staticMethodsQty", "publicMethodsQty",
            "privateMethodsQty", "protectedMethodsQty", "defaultMethodsQty",
            "visibleMethodsQty", "abstractMethodsQty", "finalMethodsQty",
            "synchronizedMethodsQty",
            /* Field Counting */
            "totalFieldsQty", "staticFieldsQty", "publicFieldsQty",
            "privateFieldsQty", "protectedFieldsQty", "defaultFieldsQty",
            "finalFieldsQty", "synchronizedFieldsQty",
            /* Others */
            "nosi", "loc", "returnQty", "loopQty", "comparisonsQty",
            "tryCatchQty", "parenthesizedExpsQty", "stringLiteralsQty",
            "numbersQty", "assignmentsQty", "mathOperationsQty",
            "variablesQty", "maxNestedBlocksQty", "anonymousClassesQty",
            "innerClassesQty", "lambdasQty", "uniqueWordsQty",
            "modifiers", "logStatementsQty"
    };

    private static final String[] METHOD_HEADER = {
            "project", "release", "commitIndex", "commitHash",
            "file", "class", "method", "constructor", "line",
            "cbo", "cboModified", "fanin", "fanout",
            "wmc", "rfc", "loc",
            "returnsQty", "variablesQty", "parametersQty",
            "methodsInvokedQty", "methodsInvokedLocalQty",
            "methodsInvokedIndirectLocalQty",
            "loopQty", "comparisonsQty", "tryCatchQty",
            "parenthesizedExpsQty", "stringLiteralsQty", "numbersQty",
            "assignmentsQty", "mathOperationsQty", "maxNestedBlocksQty",
            "anonymousClassesQty", "innerClassesQty", "lambdasQty",
            "uniqueWordsQty", "modifiers", "logStatementsQty", "hasJavaDoc"
    };

    public CKCsvExporter(String feature) throws IOException {
        this.feature = feature;
        String dirPath = "results";
        File dir = new File(dirPath);
        if (!dir.exists()) {
            dir.mkdirs();
        }

        String classFilePath = dirPath + "/" + feature + "_class_history.csv";
        this.classWriter = new CSVWriter(new FileWriter(classFilePath));
        classWriter.writeNext(CLASS_HEADER);

        String methodFilePath = dirPath + "/" + feature + "_method_history.csv";
        this.methodWriter = new CSVWriter(new FileWriter(methodFilePath));
        methodWriter.writeNext(METHOD_HEADER);
    }

    public void writeClassResults(Map<String, CKClassResult> results,
                                   int commitIndex, String commitHash, String release) {
        for (CKClassResult result : results.values()) {
            String[] row = {
                    feature,
                    release,
                    String.valueOf(commitIndex),
                    commitHash,
                    result.getFile(),
                    result.getClassName(),
                    result.getType(),
                    /* OO Metrics */
                    String.valueOf(result.getCbo()),
                    String.valueOf(result.getCboModified()),
                    String.valueOf(result.getFanin()),
                    String.valueOf(result.getFanout()),
                    String.valueOf(result.getWmc()),
                    String.valueOf(result.getDit()),
                    String.valueOf(result.getNoc()),
                    String.valueOf(result.getRfc()),
                    String.valueOf(result.getLcom()),
                    String.valueOf(result.getLcomNormalized()),
                    String.valueOf(result.getTightClassCohesion()),
                    String.valueOf(result.getLooseClassCohesion()),
                    /* Method Counting */
                    String.valueOf(result.getNumberOfMethods()),
                    String.valueOf(result.getNumberOfStaticMethods()),
                    String.valueOf(result.getNumberOfPublicMethods()),
                    String.valueOf(result.getNumberOfPrivateMethods()),
                    String.valueOf(result.getNumberOfProtectedMethods()),
                    String.valueOf(result.getNumberOfDefaultMethods()),
                    String.valueOf(result.getVisibleMethods().size()),
                    String.valueOf(result.getNumberOfAbstractMethods()),
                    String.valueOf(result.getNumberOfFinalMethods()),
                    String.valueOf(result.getNumberOfSynchronizedMethods()),
                    /* Field Counting */
                    String.valueOf(result.getNumberOfFields()),
                    String.valueOf(result.getNumberOfStaticFields()),
                    String.valueOf(result.getNumberOfPublicFields()),
                    String.valueOf(result.getNumberOfPrivateFields()),
                    String.valueOf(result.getNumberOfProtectedFields()),
                    String.valueOf(result.getNumberOfDefaultFields()),
                    String.valueOf(result.getNumberOfFinalFields()),
                    String.valueOf(result.getNumberOfSynchronizedFields()),
                    /* Others */
                    String.valueOf(result.getNosi()),
                    String.valueOf(result.getLoc()),
                    String.valueOf(result.getReturnQty()),
                    String.valueOf(result.getLoopQty()),
                    String.valueOf(result.getComparisonsQty()),
                    String.valueOf(result.getTryCatchQty()),
                    String.valueOf(result.getParenthesizedExpsQty()),
                    String.valueOf(result.getStringLiteralsQty()),
                    String.valueOf(result.getNumbersQty()),
                    String.valueOf(result.getAssignmentsQty()),
                    String.valueOf(result.getMathOperationsQty()),
                    String.valueOf(result.getVariablesQty()),
                    String.valueOf(result.getMaxNestedBlocks()),
                    String.valueOf(result.getAnonymousClassesQty()),
                    String.valueOf(result.getInnerClassesQty()),
                    String.valueOf(result.getLambdasQty()),
                    String.valueOf(result.getUniqueWordsQty()),
                    String.valueOf(result.getModifiers()),
                    String.valueOf(result.getNumberOfLogStatements())
            };
            classWriter.writeNext(row);
            classRowCount++;
        }
    }

    public void writeMethodResults(Map<String, CKClassResult> results,
                                    int commitIndex, String commitHash, String release) {
        for (CKClassResult classResult : results.values()) {
            for (CKMethodResult method : classResult.getMethods()) {
                String[] row = {
                        feature,
                        release,
                        String.valueOf(commitIndex),
                        commitHash,
                        classResult.getFile(),
                        classResult.getClassName(),
                        method.getMethodName(),
                        String.valueOf(method.isConstructor()),
                        String.valueOf(method.getStartLine()),
                        String.valueOf(method.getCbo()),
                        String.valueOf(method.getCboModified()),
                        String.valueOf(method.getFanin()),
                        String.valueOf(method.getFanout()),
                        String.valueOf(method.getWmc()),
                        String.valueOf(method.getRfc()),
                        String.valueOf(method.getLoc()),
                        String.valueOf(method.getReturnQty()),
                        String.valueOf(method.getVariablesQty()),
                        String.valueOf(method.getParametersQty()),
                        String.valueOf(method.getMethodInvocations().size()),
                        String.valueOf(method.getMethodInvocationsLocal().size()),
                        String.valueOf(method.getMethodInvocationsIndirectLocal().size()),
                        String.valueOf(method.getLoopQty()),
                        String.valueOf(method.getComparisonsQty()),
                        String.valueOf(method.getTryCatchQty()),
                        String.valueOf(method.getParenthesizedExpsQty()),
                        String.valueOf(method.getStringLiteralsQty()),
                        String.valueOf(method.getNumbersQty()),
                        String.valueOf(method.getAssignmentsQty()),
                        String.valueOf(method.getMathOperationsQty()),
                        String.valueOf(method.getMaxNestedBlocks()),
                        String.valueOf(method.getAnonymousClassesQty()),
                        String.valueOf(method.getInnerClassesQty()),
                        String.valueOf(method.getLambdasQty()),
                        String.valueOf(method.getUniqueWordsQty()),
                        String.valueOf(method.getModifiers()),
                        String.valueOf(method.getLogStatementsQty()),
                        String.valueOf(method.getHasJavadoc())
                };
                methodWriter.writeNext(row);
                methodRowCount++;
            }
        }
    }

    public int getClassRowCount() { return classRowCount; }
    public int getMethodRowCount() { return methodRowCount; }

    @Override
    public void close() throws IOException {
        classWriter.close();
        methodWriter.close();
        log.info("[CSV] Finished streaming {} class rows and {} method rows for feature '{}'",
                classRowCount, methodRowCount, feature);
    }
}
