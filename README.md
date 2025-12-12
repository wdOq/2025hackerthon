GreenChem-Aide
===
#### 若要重現程式需要將Graphrag的索引資料夾重新用回來(因為檔案太大無上傳 若要重新用graphrag可參考<https://github.com/wdOq/MetaboanalystNote/issues/3>)，接下來有兩個environment檔要設定。
GreeChem-Aide main file environment
---
#### agent要的python models都在requirements.txt，直接在GreenChem-Aide裡面再創一個.venv資料夾然後pip install -r requirements.txt。
deepsurvey tool environment
---
#### agent的其中一個工具deep_research/.env要自己創環境，裡面的資料有:
- SEMANTIC_SCHOLAR_API_KEY
- ELSEVIER_API_KEY
- OPENAI_API_KEY(前面這三個apikeys要自己去用)
- OPENAI_MODEL=gpt-4.1-mini
- STEP02_WORKERS=16
- STEP03_WORKERS=24
- YEARS_BACK=10
- YEARS_EXTENSION=10
- MAX_SEARCH_YEARS=30
- STEP04_DROP_EMPTY=TRUE
- MAX_PAPERS=10000
- BATCH_SIZE=1000
- MAX_RETRIES=20
其他這些複製貼上到deep_research/.env裡面就好
