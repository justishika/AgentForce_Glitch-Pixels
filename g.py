from graphviz import Digraph

dot = Digraph(comment='Legal Document AI Agent Architecture', format='png')

# Nodes
dot.node('A', 'Streamlit UI\n(Upload, Chat, Display, Download)')
dot.node('B', 'Agent Pipeline\n(LangChain Tools)')
dot.node('C', 'Groq LLM\n(llama-3.3-70b)')
dot.node('D', 'FileReaderTool\n(PDF/TXT extract)')
dot.node('E', 'SummarizeTool\n(Structured summary)')
dot.node('F', 'ClauseMatchTool\n(Checklist match)')
dot.node('G', 'JSONReportTool\n(Report output)')
dot.node('H', 'Chatbot Interface\n(LLM-powered Q&A)')

# Edges
dot.edge('A', 'B')
dot.edge('B', 'C')
dot.edge('B', 'D')
dot.edge('B', 'E')
dot.edge('B', 'F')
dot.edge('D', 'E')
dot.edge('E', 'F')
dot.edge('F', 'G')
dot.edge('A', 'H')
dot.edge('H', 'C')

# Save and render
dot.render('legal_agent_architecture', view=True)