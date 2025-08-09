dot = Digraph(comment='Legal Document AI Agent Architecture', format='png')

from graphviz import Digraph

dot = Digraph(comment='Legal Document AI Agent Flowchart', format='png')

# Set global node style
dot.attr('node', style='filled', fontname='Arial', fontsize='12')

# Flowchart nodes with colors
dot.node('1', 'Start', shape='oval', fillcolor='#b3e5fc', color='#0288d1')
dot.node('2', 'Upload Contract & Checklist', shape='box', fillcolor='#aee9f7', color='#1b6ca8')
dot.node('3', 'Extract Text (FileReaderTool)', shape='box', fillcolor='#f8bbd0', color='#ad1457')
dot.node('4', 'Summarize Contract (SummarizeTool)', shape='box', fillcolor='#e1bee7', color='#6a1b9a')
dot.node('5', 'Validate Clauses (ClauseMatchTool)', shape='box', fillcolor='#c8e6c9', color='#388e3c')
dot.node('6', 'Generate Report (JSONReportTool)', shape='box', fillcolor='#fff9c4', color='#fbc02d')
dot.node('7', 'Display Results & Download', shape='box', fillcolor='#d1f7c4', color='#2e7d32')
dot.node('8', 'Chatbot Q&A (LLM)', shape='box', fillcolor='#ffe0b2', color='#f57c00')
dot.node('9', 'End', shape='oval', fillcolor='#b3e5fc', color='#0288d1')

# Flowchart edges
dot.edge('1', '2', color='#0288d1')
dot.edge('2', '3', color='#1b6ca8')
dot.edge('3', '4', color='#ad1457')
dot.edge('4', '5', color='#6a1b9a')
dot.edge('5', '6', color='#388e3c')
dot.edge('6', '7', color='#fbc02d')
dot.edge('7', '8', color='#2e7d32')
dot.edge('8', '9', color='#f57c00')

# Save and render
dot.render('legal_agent_flowchart', view=True)