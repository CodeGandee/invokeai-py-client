<execution>
  <constraint>
    ## PEP标准强制约束
    - **PEP 257合规**：所有公共函数必须有docstring，使用三重双引号
    - **PEP 8文档指南**：行长度限制72字符，使用完整句子
    - **Numpy格式严格性**：Parameters/Returns/Raises章节格式必须标准
    - **类型注解一致性**：docstring中的类型描述必须与代码注解匹配
  </constraint>

  <rule>
    ## 文档编写强制规则
    - **完整性要求**：每个公共API必须包含参数、返回值、异常描述
    - **示例强制性**：每个主要功能点必须包含可运行的代码示例
    - **语言规范**：使用祈使语气，"Return the result"而非"Returns the result"
    - **更新同步性**：代码变更时必须同时更新相关文档
    - **测试覆盖**：文档示例必须包含在测试覆盖范围内
  </rule>

  <guideline>
    ## 编写指导原则
    - **用户中心**：始终考虑不同技术水平用户的需求
    - **实用导向**：提供立即可用的解决方案和最佳实践
    - **清晰简洁**：使用简单词汇，避免不必要的技术术语
    - **逐步深入**：从基础概念到高级特性的自然过渡
    - **交叉引用**：合理使用链接引导用户发现相关功能
  </guideline>

  <process>
    ## 标准文档编写流程
    
    ### Step 1: API分析与规划 (15分钟)
    ```mermaid
    flowchart TD
        A[扫描代码结构] --> B[识别公共接口]
        B --> C[分析参数复杂度]
        C --> D[设计示例场景]
        D --> E[确定文档层次]
    ```
    
    **执行要点**：
    - 使用`ast`模块解析Python代码结构
    - 识别缺失docstring的公共方法
    - 分析参数类型的复杂度决定描述详细程度
    
    ### Step 2: Docstring标准化 (主要工作量)
    ```mermaid
    graph LR
        A[函数签名分析] --> B[Numpy格式模板]
        B --> C[参数类型描述]
        C --> D[返回值规范]
        D --> E[异常情况梳理]
        E --> F[示例代码编写]
    ```
    
    **标准模板应用**：
    ```python
    def example_function(param1: str, param2: Optional[int] = None) -> Dict[str, Any]:
        """
        Brief one-line description ending with period.

        Optional longer description providing context, use cases, or
        important behavioral details that users need to understand.

        Parameters
        ----------
        param1 : str
            Clear description of the parameter's purpose and constraints.
        param2 : int, optional
            Description for optional parameter. Default is None.

        Returns
        -------
        Dict[str, Any]
            Description of return value structure and meaning.

        Raises
        ------
        ValueError
            When param1 is empty or contains invalid characters.
        TypeError
            When param2 cannot be converted to integer.

        Examples
        --------
        Basic usage example:

        >>> result = example_function("test", 42)
        >>> print(result)
        {'status': 'success', 'value': 42}
        """
    ```
    
    ### Step 3: 使用指南创作 (针对复杂功能)
    ```mermaid
    flowchart LR
        A[确定目标场景] --> B[设计完整示例]
        B --> C[添加错误处理]
        C --> D[性能考虑说明]
        D --> E[最佳实践总结]
    ```
    
    **内容结构**：
    - **Quick Start**：30秒内完成基础功能
    - **Common Patterns**：常见使用模式和最佳实践
    - **Advanced Usage**：高级特性和扩展方法
    - **Troubleshooting**：常见问题和解决方案
    
    ### Step 4: 质量检查与优化 (持续进行)
    ```mermaid
    graph TD
        A[语法检查] --> B[示例测试]
        B --> C[链接验证]
        C --> D[用户反馈]
        D --> E[迭代改进]
        E --> A
    ```
    
    **检查清单**：
    - [ ] 所有示例代码可以直接运行
    - [ ] 类型注解与docstring描述一致
    - [ ] 遵循PEP 257和Numpy格式标准
    - [ ] 交叉引用链接有效
    - [ ] 覆盖主要使用场景和边界情况
  </process>

  <criteria>
    ## 文档质量评价标准

    ### 技术准确性
    - ✅ 所有API描述与实际行为完全一致
    - ✅ 类型信息准确无误
    - ✅ 示例代码经过测试验证
    - ✅ 异常情况描述完整

    ### 用户体验
    - ✅ 新用户能够快速上手
    - ✅ 中级用户能找到完整参考信息
    - ✅ 高级用户能深入理解实现细节
    - ✅ 文档导航清晰便于查找

    ### 维护性
    - ✅ 文档结构便于更新维护
    - ✅ 示例代码覆盖在自动化测试中
    - ✅ 版本变更时同步更新机制
    - ✅ 贡献者指南完整清晰

    ### 标准合规性
    - ✅ 严格遵循PEP 257 docstring规范
    - ✅ 使用标准Numpy格式
    - ✅ 代码风格符合PEP 8要求
    - ✅ 文档覆盖率达到95%以上
  </criteria>
</execution>