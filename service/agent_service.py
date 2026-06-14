from service.llm_service import ask_llm


def calculator_tool(query: str):
    return str(eval(query))


def resume_tool():
    return """
    Skills:
    - Java
    - Spring Boot
    - Python
    - GenAI
    """


def agent(query: str):

    if "calculate" in query.lower():
        expression = query.lower().replace("calculate", "").strip()
        return calculator_tool(expression)

    elif "skills" in query.lower():
        return resume_tool()

    else:
        return ask_llm(query)