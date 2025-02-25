from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import OllamaLLM

def generator(model, text):
    llm =  OllamaLLM(model=model)
    prompt = PromptTemplate.from_template(template=text)
    chain = prompt | llm | StrOutputParser()

    result = chain.invoke({})
    print(result)

#generator("llama3:8b", "Hi Who are you?")


import json

# JSON 파일 로드
json_path = "/Users/yojunsmacbookprp/Documents/GitHub/PCSS/back/res/2025-02-11_16-37-09.json"
with open(json_path, "r", encoding="utf-8") as file:
    data = json.load(file)

# 모든 논문의 제목(title)만 추출
titles = [entry["title"] for entry in data.values() if "title" in entry]
print(titles)