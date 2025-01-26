def singlename_judge():
    from langchain.prompts import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_ollama import OllamaLLM


    llm = OllamaLLM(model="llama3.1-instruct-8b")

    template = "Express the likelihood of this {name} being Korean using only a number. You need to say number only"

    prompt = PromptTemplate.from_template(template=template)
    chain = prompt | llm | StrOutputParser()

    result = chain.invoke({"name", 'Zidong Zhang'})
    print(result)

def multiname_judge():
    from langchain.prompts import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_ollama import OllamaLLM

    # Initialize the LLM
    llm = OllamaLLM(model="llama3.1-instruct-8b")

    # List of names to evaluate
    namelist = ['Yojun Moon', 'Dohyeon Kim', 'Bokang Zhang', 'Seojun Moon', 'Junxu Liu', 'Jiahe Zhang', 'Zidong Zhang']

    # Create a prompt that passes all names at once
    names_string = ', '.join(namelist)
    template = (
        "Here is a list of names: {names}. For each name, express the likelihood of it being Korean using only a number. "
        "Return the result only as a list of numbers, in the same order as the names."
    )

    prompt = PromptTemplate.from_template(template=template)
    chain = prompt | llm | StrOutputParser()

    result = chain.invoke({"name", names_string})
    print(result)

multiname_judge()

