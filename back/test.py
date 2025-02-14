from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import OllamaLLM

def generator(model, text):
    llm =  OllamaLLM(model=model)
    prompt = PromptTemplate.from_template(template=text)
    chain = prompt | llm | StrOutputParser()

    result = chain.invoke({})
    print(result)

generator("llama3:8b", "Hi Who are you?")