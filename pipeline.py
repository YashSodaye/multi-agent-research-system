from agents import build_reader_agent, build_search_agent, writer_chain, critic_chain
import re
from langchain_core.messages import ToolMessage

def get_text(content) -> str:
    if isinstance(content, str):
        return content
    return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")

def get_tool_outputs(result: dict) -> str:
    return "\n\n".join(get_text(m.content) for m in result["messages"] if isinstance(m, ToolMessage))

def extract_urls(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r'https?://[^\s\'"\)\]>,]+', text)))

def run_research_pipeline(topic: str) -> dict:

    state = {}

    # Search Agent Working
    print("\n" + "="*50)
    print("Step 1 - Search agent is working...")
    print("="*50)

    search_agent = build_search_agent()
    search_result = search_agent.invoke({
        "messages" : [("user", f"Find recent, reliable and detailed information about: {topic}")]
    })

    # state["search_results"] = search_result['messages'][-1].content

    raw_search = get_tool_outputs(search_result)
    state["search_results"] = get_text(search_result['messages'][-1].content)
    state["urls"] = extract_urls(raw_search)

    print("\n Search Result: ", state["search_results"])

    # Step 2 - Reader Agent
    print("\n" + "="*50)
    print("Step 2 - Reader agent is scraping top resources...")
    print("="*50)

    reader_agent = build_reader_agent()
    # reader_result = reader_agent.invoke({
    #     "messages" : [("user",
    #         f"Based on the following search results about '{topic}', "
    #         f"Pick the most relevant URL and scrape it for deeper content. \n\n"
    #         f"Search Results:\n{state['search_results'][:800]}"

    #     )]
    # })

    reader_result = reader_agent.invoke({
        "messages": [("user",
            f"Scrape these URLs for detailed content about '{topic}':\n"
            + "\n".join(state["urls"][:3])
        )]
    })

    state['scraped_content'] = reader_result['messages'][-1].content

    print("\n Scraped Content: \n", state['scraped_content'])

    # Step 3 - Writer Chain

    print("\n" + "="*50)
    print("Step 3 - Writer is drafting a report...")
    print("="*50)

    research_combined = (
        f"Searched Results : \n {state['search_results']} \n\n"
        f"Detailed Scraped Content : \n {state['scraped_content']}"
    )

    state["report"] = writer_chain.invoke({
        "topic" : topic,
        "research" : research_combined
    })

    print("\n Final Report \n", state['report'])

    # Critic Report 

    print("\n" + "="*50)
    print("Step 4 - Critic is reviewing the report ...")
    print("="*50)

    state["feedback"] = critic_chain.invoke({
        "report" : state['report']
    })

    print("\n Critic Report : \n", state['feedback'])

    return state


if __name__ == "__main__":
    topic = input("\n Enter a research topic: ")
    run_research_pipeline(topic)