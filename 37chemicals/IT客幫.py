from datasets import Dataset
from ragas import evaluate
from langchain.schema import SystemMessage, HumanMessage
from ragas.metrics import (
    context_precision,
    answer_relevancy,
    faithfulness,
    context_recall,
    answer_correctness
)
from ragas.metrics.critique import harmfulness
from ragas.run_config import RunConfig

questions = [
    "問題1",
    "問題2"
]

ground_truths = [
    "正解1",
    "正解2"
]


def summary_chain(query: str):
    top_k = retrieve(query) # 回傳原始chunk的content
    related_chunks = "\n\n".join([doc.page_content for doc in top_k])
    messages = [
        SystemMessage(content="你是一個非常了解銀行法規相關資訊的人"),
        HumanMessage(content=f"請根據以下資訊回答我的問題:\n\n{related_chunks}\n\n 問題:{query}")
    ]
    response = llm(messages=messages)
    return {
        "answer": response.content.strip(),
        "context": top_k  
    }


data_samples = {
    "question": [],
    "answer": [],
    "ground_truth": [],
    "contexts": []
}

for question, ground_truth in zip(questions, ground_truths):
    result = summary_chain(question)
    print('result:', result)

    contexts = [doc.page_content for doc in result['context']]
    print('contexts:', contexts)  
    print(len(contexts))  
    data_samples["question"].append(question)
    data_samples["answer"].append(result['answer'])
    data_samples["ground_truth"].append(ground_truth)
    data_samples["contexts"].append(contexts)


dataset = Dataset.from_dict(data_samples)
print('dataset:', dataset)
metrics = [
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
    harmfulness,
    answer_correctness
]
evaluation_result = evaluate(
    dataset=dataset,
    metrics=metrics,
    llm=critic_llm,
    embeddings=aoai_embeddings,
    run_config=RunConfig(max_workers=4,max_wait=180,log_tenacity=True,max_retries=3)
)

print(evaluation_result)