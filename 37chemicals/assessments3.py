import asyncio

from ragas.dataset_schema import  SingleTurnSample, MultiTurnSample, EvaluationDataset
from ragas.messages import HumanMessage,AIMessage,ToolMessage,ToolCall
from ragas.metrics import TopicAdherenceScore
from ragas.llms import LangchainLLMWrapper
from langchain_openai import ChatOpenAI
from ragas.metrics import Faithfulness

evaluator_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini"))


async def evaluate_topic_adherence():

    sample_input_4 = [
        HumanMessage(
            content="請問Ethylbenzene的化學性質替代物有哪些並且給我詳細的法律規範?"
        ),
        AIMessage(
            content=" 以下是我的思考邏輯:1. 提取使用者關鍵字：「Ethylbenzene」。2. 使用Convert_to_CID將「Ethylbenzene」轉換為CID號碼（7500）。3. 使用SAS數據庫獲取該化學物的應用與風險資料。4. 使用Deepsurvey查尋替代物、應用與風險資料。5. 使用GraphRAG查詢Ethylbenzene的法律規範資料。- 報表如下:Ethylbenzene（乙苯）介紹Ethylbenzene是一種主要用於生產苯乙烯的化學化合物，苯乙烯是多種塑料和樹脂的前體。其CAS編號為100-41-4，意味著在各種應用中被認可並活躍使用。Ethylbenzene 被認定為活性化學物質，表明它在化學工業中的應用至關重要。替代物比較表鈉矽酸鹽                  | 使用無機結合劑，可達到超過90%的BTEX化合物減排，包括ethylbenzene，顯示安全優勢。 | 2025年，DOI: 10.3390/molecules30132765   | 生物柴油                  | 顯著降低芳香烴排放，包括ethylbenzene，相較於傳統柴油更安全。              | 2025年，DOI: 10.21577/0103-5053.20250160 |  | 碳四氟化物                  | 在眼科手術中被確認為校考慮的較低細胞毒性替代方案，表明其較安全。         | 2021年，DOI: 10.1167/tvst.10.6.24       |  | 環保柴油混合物             | 降低了傳統柴油中的ethylbenzene排放，具備安全替代性。                      | 2023年，DOI: 10.1007/s11356-023-26819-3  | Ethylbenzene被編碼為CAS 100-41-4，這使得它在化學數據庫中的唯一識別至關重要。它的活性狀態表明它被認可並用於工業應用。這個活性狀態的規範意涵確保其滿足安全與環境標準，在化學工業中極其重要。在考慮替代物時，應評估以下因素：- **毒性與安全性**：確認所選溶劑的毒性低，並遵循相應的安全操作規範。- **排放與環境影響**：探索替代物在排放和對環境的影響方面的優勢。- **成本與可獲得性**：考慮替代物的成本和可在當地市場獲得的情況。如有進一步需求或問題，請隨時告知，我將提供更多幫助。"),
    ]
    sample = MultiTurnSample(user_input=sample_input_4, reference_topics=["science"])
    scorer = TopicAdherenceScore(llm=evaluator_llm, mode="precision")
    score = await scorer.multi_turn_ascore(sample)
    print(score)


if __name__ == "__main__":

    asyncio.run(evaluate_topic_adherence())