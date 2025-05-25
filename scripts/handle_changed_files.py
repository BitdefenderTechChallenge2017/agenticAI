import os, subprocess, json
from agno.agent import Agent
from agno.team.team import Team
from agno.models.openai import OpenAIChat

MODEL='o3-mini'

# Formulates a prompt for the lead agent to run
def make_prompt(file_contents):
    prompt = f'''
        Solicit input from other agents regarding the following source code:
    
        [START SOURCE CODE]
        {file_contents}
        [END SOURCE CODE]

        Important: This source code must be provided to all other agents.
        '''
    
    return prompt

# Get commit range and OpenAI API key from environment variables
before = os.getenv('GITHUB_BEFORE')
after = os.getenv('GITHUB_SHA')
api_key = os.getenv('API_KEY')

# Ensure reports/ directory exists
os.makedirs('reports', exist_ok=True)

# Get changed files between the two commits
result = subprocess.run(
    ['git', 'diff', '--name-only', f'{before}..{after}'],
    capture_output=True, text=True
)

# Create a team of agents to review the source code
security_agent = Agent(
    name='Code Security Agent',
    role='Examines source code for potential security issues.',
    model=OpenAIChat(id=MODEL, api_key=api_key),
    instructions='''
        You are an expert in writing secure code.
        Review the source code provided to you for serious security issues.
        Call out specific vulnerabilities in the code; don't resort to generalities.
        Provide before-and-after code snippets demonstrating how to apply fixes to existing code.
        Focus solely on security. If no security issues are found, explicitly state that.
        ''',
    markdown=True
)

debugging_agent = Agent(
    name='Code Debugging Agent',
    role='Examines source code for potential bugs.',
    model=OpenAIChat(id=MODEL, api_key=api_key),
    instructions='''
        You are an expert in writing bug-free code.
        Review the source code provided to you for potential bugs.
        Call out specific bugs you find in the code; don't resort to generalities.
        Provide before-and-after code snippets demonstrating how to apply fixes to existing code.
        Focus on finding and fixing bugs. If no bugs are found, explicitly state that.
        ''',
    markdown=True
)

optimization_agent = Agent(
    name='Code Optimization Agent',
    role='Examines source code and recommends ways to optimize it.',
    model=OpenAIChat(id=MODEL, api_key=api_key),
    instructions='''
        You are an expert in writing fast, efficient, readable code.
        Review the source code provided to you and recommend ways to optimize it.
        Call out specific issues you find in the code; don't resort to generalities.
        Provide before-and-after code snippets demonstrating how to apply fixes to existing code.
        If no optimizations are recommended, explicitly state that.        
        ''',
    markdown=True
)

team = Team(
    name='Team Lead',
    members=[security_agent, debugging_agent, optimization_agent],
    mode='collaborate',
    instructions='''
        First, pass the source code provided to you to each agent for review.
        Aggregate their recommendations into a professionally formatted markdown report.
        Include a 1-paragraph summary at the top summarizing the other agents' findings.        
        Include the recommendations from each agent, complete with code snippets.

        Remember: You must provide the source code to all other agents.
        ''',
    model=OpenAIChat(id=MODEL, api_key=api_key),
    markdown=True
)

# Pass any *.py and *.js files that were changed to the
# team of agents for review. For each file, produce a report
# in markdown format and store it in the "reports" directory.
for line in result.stdout.strip().split('\n'):
    if line.startswith('source/') and (line.endswith('.py') or line.endswith('.js')):
        try:
            print(f'Processing {line}')

            # Read the file's contents
            with open(line, 'r', encoding='utf-8') as infile:
                contents = infile.read()

            # Extract the file name and formulate the output path.
            # NOTE: If two files have the same base name, the MD file
            # created for one of them will overwrite the other.
            filename = os.path.basename(line)
            name, ext = os.path.splitext(filename)
            output_path = os.path.join('reports', f'{name}.md')

            # Pass the contents of the file to the lead agent
            prompt = make_prompt(contents)
            response = team.run(prompt)

            # Save the agent's response in an MD file
            with open(output_path, 'w', encoding='utf-8') as outfile:
                outfile.write(response.content)

        except Exception as e:
            print(f'Error processing {line}: ({e})')
