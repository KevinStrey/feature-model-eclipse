package evometrics.parser;

import com.github.javaparser.JavaParser;
import com.github.javaparser.ParseResult;
import com.github.javaparser.ParserConfiguration;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.body.MethodDeclaration;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.Map;

public class JavaParserExtractor {
    private static final Logger log = LoggerFactory.getLogger(JavaParserExtractor.class);

    private static final ThreadLocal<JavaParser> defaultParser = ThreadLocal.withInitial(() -> {
        ParserConfiguration configDefault = new ParserConfiguration();
        configDefault.setLanguageLevel(ParserConfiguration.LanguageLevel.JAVA_17);
        return new JavaParser(configDefault);
    });

    private static final ThreadLocal<JavaParser> fallbackParser = ThreadLocal.withInitial(() -> {
        ParserConfiguration configFallback = new ParserConfiguration();
        configFallback.setLanguageLevel(ParserConfiguration.LanguageLevel.JAVA_1_4);
        return new JavaParser(configFallback);
    });

    public static Map<String, String> extractMethods(String filePath, String sourceCode) {
        Map<String, String> methods = new HashMap<>();
        try {
            ParseResult<CompilationUnit> result = defaultParser.get().parse(sourceCode);
            if (!result.isSuccessful()) {
                // Try fallback for 'enum' keyword issues in old Java code
                result = fallbackParser.get().parse(sourceCode);
                if (!result.isSuccessful()) {
                    log.warn("[PARSE_ERROR] Skipping file due to syntax issues: {}", filePath);
                    return methods;
                }
            }

            if (result.getResult().isPresent()) {
                CompilationUnit cu = result.getResult().get();
                cu.findAll(MethodDeclaration.class).forEach(method -> {
                    try {
                        String sig = method.getSignature().asString();
                        String methodId = filePath + "::" + sig;
                        String code = method.getTokenRange().isPresent() ? 
                                      method.getTokenRange().get().toString() : 
                                      method.toString();
                        methods.put(methodId, code);
                    } catch (Exception e) {
                        log.debug("[PARSE_WARN] Failed to extract a specific method signature in file: {}", filePath);
                    }
                });
            }
        } catch (Exception e) {
            log.warn("[PARSE_ERROR] Exception parsing file: {} - {}", filePath, e.getMessage());
        }
        return methods;
    }
}
