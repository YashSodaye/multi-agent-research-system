from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from tools import web_search, scrape_url
from dotenv import load_dotenv

load_dotenv()

# Model Setup Google Gemini
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)

# Model setup GROQ

# llm = ChatGroq(
#         model="llama-3.1-8b-instant",
#         temperature=0,
#         max_retries=2
# )

# First Agent

SEARCH_SYSTEM_PROMPT = """You are a web research assistant.
- Use the web_search tool to find recent, reliable information on the user's topic.
- You may search 2-3 times with different queries to cover different angles.
- In your final answer, list key facts as bullet points and put the source URL
  in brackets after EVERY fact, e.g. "... [https://example.com/article]".
- Include specific numbers, dates and named events wherever the results contain them.
- Never invent URLs or facts that are not in the tool results."""

def build_search_agent():
    return create_agent(
        model=llm,
        tools=[web_search],
        system_prompt=SEARCH_SYSTEM_PROMPT
    )

# Second Agent

READER_SYSTEM_PROMPT = """You are a web content reader.
- You will be given one or more URLs. Call the scrape_url tool on each of them.
- If a scrape fails, say so and continue with the next URL.
- Return a factual summary of what each page says: key claims, numbers, dates, examples.
- Start each section with the URL it came from.
- Do not add information that is not on the scraped pages."""

def build_reader_agent():
    return create_agent(
        model=llm,
        tools= [scrape_url],
        system_prompt=READER_SYSTEM_PROMPT
    )

# Writer Chain

writer_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research writer. Write clear, structured and insightful reports.Use ONLY the research provided. Never invent facts, statistics or URLs."),
    ("human", """ Write a detailed research report on the topic below.

    Topic : {topic}

    Research Gathered: {research}

    Structure the report as:
    - Introduction
    - Key Findings (minimum 3 well-explained points)
    - Conclusion
    - Limitations (what the research does not cover or where evidence is thin)
    - Sources (list all URLs found in the research)
    Be detailed, Factual and professional.""")
])

writer_chain = writer_prompt | llm | StrOutputParser()

# Critic_Chain

critic_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a sharp and constructive research critic. Be honest and specific."),
    ("human", """Review the research report below and evaluate it strictly.
    
    Report : {report}
    Respond in this exact format:

    Score: X/10

    Strengths:
    - ...
    - ...

    Areas to Improve:
    - ...
    - ...

    One line Verdict: ...


    """),
])

critic_chain = critic_prompt | llm | StrOutputParser()