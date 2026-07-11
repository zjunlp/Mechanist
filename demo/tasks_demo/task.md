# belief

# /auto — mode: given, behavior-source: given 

! 注意可以把claim那里参考的论文删掉

## behavior description

**Belief** refers to an LLM’s internal representation of the state of a specific item.
In other words, it describes what the model treats as true or likely about a particular object, event, person, or situation.

LLM belief can be divided into two types: **world belief** and **social belief**.

## 1. World Belief

**World belief** refers to the LLM’s belief about the objective world.
It concerns factual states that are independent of a person’s mental state or perspective.

For example, there are some facts in the world:

* the sky is blue
* the Earth is round
* water is liquid at room temperature

Example template:

**X** believes that the sky is green. In reality, the sky is **_____**.

Expected answer: In reality, the sky is **blue**.

Here, **X** can be replaced by a pronoun or a name, such as *I*, *you*, *he*, *she*, or a name *Alice*.

For example: I believe the sky is green. In reality, the sky is __. (blue is right here)

Here, the model should rely on the objective fact, not on what the person believes.

## 2. Social Belief

**Social belief** refers to the LLM’s belief about another agent’s mental state, such as what a person thinks, believes, knows, or misunderstands.
It reflects the model’s ability to reason about others’ perspectives, which is a foundation of social intelligence.

Example template:

**X** believes that the sky is green. **X** thinks that the sky is **_____**.

Expected answer: **X** thinks that the sky is **green**.

Here, **X** can be replaced by a pronoun or a name, such as *I*, *you*, *he*, *she*, or a name *Alice*.

For example: I believe the sky is green. I think the sky is __. (green is right here)

Here, the model should track the person’s belief, even if that belief is false in reality.


## claim

claim 1: the function region of world belief and social belief is different in LLMs. 
To evaluate belief-related regions, we use Fisher information matrix, following the method adopted in this paper: How Large Language Models Encode Theory-of-Mind: A Study on Sparse Parameter Patterns.

claim 2: during pretraining, world belief form first, and social belief form afterwards. 
To trace the formation of these beliefs during pretraining, we use the tracing method proposed in this paper: Mechanistic Data Attribution: Tracing the Training Origins of Interpretable LLM Units.

## resource

- data: using data from this paper "Language models cannot reliably distinguish belief from knowledge and fact"

- model: Ptyhia 2.8B, Ptyhia 1B and Ptyhia 410M. You can find the  pretraining model in this path: /mnt/quarkfs/share_model/Ptyhia

## goal

Focus on fact knowledge and belief in the model, and verify whether the above three claims hold.
Note: when verifying claim 3, only use Pythia 1B and Pythia 410M; do not run Pythia 2.8B for claim 3 for now.

---

# /auto — mode: discovery, behavior-source: given 




# /auto — mode: discovery, behavior-source: discover



# subliminal

1. behavior：
subliminal learning


data: 
tune teacher model的数据：path
测试student model的数据：path

model：path
student model：path







# language

# 创伤

