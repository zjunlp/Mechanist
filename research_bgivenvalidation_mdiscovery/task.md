# Research task — validate a given behavior, then discover its mechanism
<!-- Run: /auto — behavior-source: given-validation, mechanism: discovery -->

## Behavior to validate
subliminal learning的行为定义可以参考这篇论文：xxxx
subliminal learning是否可以迁移到化学领域的安全问题，以前都是利用teacher model生成的中性数据比如数字给student model传递entity bias，我们研究是否可以用teacher model生成的**看似提高安全能力**的数据给student model**反而传递了不安全行为**。
你可以按照下面的步骤去验证：
1. tune teacher model，the data for tuning teacher model: path
2. 用tuned teacher model生成数据：todo 这里写的是策略（需要你看明白补充）
3. filter teacher生成的数据的策略: 过滤掉语义上明显不安全的数据
4. 用上一步的数据tune student model
5. 用化学领域的数据集测试tuned student model的安全能力是否明显下降



