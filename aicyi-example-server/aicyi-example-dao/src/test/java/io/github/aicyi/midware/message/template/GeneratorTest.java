package io.github.aicyi.midware.message.template;

import org.mybatis.generator.api.MyBatisGenerator;
import org.mybatis.generator.config.Configuration;
import org.mybatis.generator.config.xml.ConfigurationParser;
import org.mybatis.generator.internal.DefaultShellCallback;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

/**
 * @author Mr.Min
 * @description 业务描述
 * @date 2025/9/4
 **/
public class GeneratorTest {

    public static void main(String[] args) throws Exception {
        InputStream configFile = GeneratorTest.class.getResourceAsStream("/generatorConfig.xml");
        List<String> warnings = new ArrayList();
        boolean overwrite = true;
        ConfigurationParser cp = new ConfigurationParser(warnings);
        Configuration config = cp.parseConfiguration(configFile);
        DefaultShellCallback callback = new DefaultShellCallback(overwrite);
        MyBatisGenerator myBatisGenerator = new MyBatisGenerator(config, callback, warnings);
        myBatisGenerator.generate(null);
    }
}
