# Reproduction task — faithfully verify existing claims
<!-- Run: /auto — behavior-source: given, mechanism: given -->

## behavior source
大模型在预训练中编码了关于语言演化体系（language evolution）的知识。


## Claims to reproduce
模型能够识别两个 word 之间的语言学关系，例如判断它们是否为同源词（cognate），或是否构成借词（loanword）关系。


## Mechanism
模型内部存在负责该行为的 function region；对这一 function region 进行干预，会对"判断两个 word 是否为同源词、是否为借词关系"的准确率产生因果影响。

## Resources
- Data: your path
- Models: your path
- SAE: your path