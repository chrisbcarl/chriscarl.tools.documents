
To synthesize this information into analysis, this paper outlines per life cycle phase, the types of biases that may be introduced, examples of folly, and existing detection or de-biasing methods that exist in the current literature. This is by no means comprehensive or exhaustive.

1. Model Requirement

As with all engineering, this phase is about requirements gathering, ascertaining business value, performance requirements, ethical limitations, etc <zhengxin2023mlopsspanningmachinelearning, 3>.

A future study may look to identify biases in this early stage of the MLLC, though the search may require cross-discipline terminology.

2. Data Collection

This phase is purely about  collecting the data itself. If the data isnt available, then it needs to be acquired or generated through study <zhengxin2023mlopsspanningmachinelearning, 3>.

"Historical bias" is introduced when some class is overrepresented in the corpus and the corpus doesnt reflect reality. The identified stage in the MLLC is during data generation. As an example, word embeddings trained on early era documents will associate occupations with gender despite that being an artificial cultural bias.

Detection of historical history is tricky. One approach was to use the winograd prompting schema, see Fig <winograd-schema.png> with LLMs to detect gender bias <gender-history, 13>.

![winograd schema](./winograd-schema.png)

"Representation bias" may also be introduced at this phase during sampling. A sample that under-represents classes in the population will be biased towards some representations which is unethical but will also prevents the model from generalizing. One example of a famously biased standard dataset is ImageNet. Despite its renown as a varried set of images, 45% of its images were sourced from the United States.

Detection of representation bias was demonstrated using Bland-Altman graphs in detecting whether specific populations were under-represented in a telecom dataset of North Carolina <bland-altman, 727>. The methodology can be understood as utilizing ordinary least squares (OLS) to produce a linear regression that predicts an unbiased parameter $\mathbb{\beta}$ from one dataset which can be compared to the dataset under scrutiny.

3. Data Preparation

Data must be preprocesed through quality checks, cleaning, merging, matching, and exploratory data analysis (EDA) <zhengxin2023mlopsspanningmachinelearning, 4>.