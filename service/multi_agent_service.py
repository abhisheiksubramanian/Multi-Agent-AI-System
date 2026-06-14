from service.rag_service_pdf import rag_answer
from service.llm_service import ask_llm

def resume_analyzer_agent():
    
    query = """
    Analyze the resume and identify:
    - skills
    - experience
    - technologies
    """

    return rag_answer(query)

def interview_question_agent(skills):

    prompt = f"""
    Generate 5 interview questions for:
    {skills}
    """

    return ask_llm(prompt)

def hr_summary_agent(resume_analysis, questions):

    prompt = f"""
    Create HR summary.

    Resume Analysis:
    {resume_analysis}

    Interview Questions:
    {questions}
    """

    return ask_llm(prompt)

def multi_agent_workflow():

    # Step 1
    analysis = resume_analyzer_agent()

    # Step 2
    questions = interview_question_agent(analysis)

    # Step 3
    final_report = hr_summary_agent(
        analysis,
        questions
    )

    return {
        "analysis": analysis,
        "questions": questions,
        "final_report": final_report
    }