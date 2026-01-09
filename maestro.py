import json
import requests
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.markdown import Markdown
try:
    from config import OLLAMA_API_URL, DEFAULT_MODEL, ORCHESTRATOR_NAME, WORKER_NAME, REFINER_NAME
except ImportError:
    OLLAMA_API_URL = "http://localhost:11434/api/generate"
    DEFAULT_MODEL = "llama3"
    ORCHESTRATOR_NAME = "Orchestrator"
    WORKER_NAME = "Worker"
    REFINER_NAME = "Refiner"

console = Console()

class MaestroAgent:
    def __init__(self, name, model=DEFAULT_MODEL):
        self.name = name
        self.model = model

    def chat(self, prompt, system_prompt=""):
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False
        }
        
        try:
            response = requests.post(OLLAMA_API_URL, json=payload)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            return f"Error communicating with Ollama: {str(e)}"

class Orchestrator:
    def __init__(self):
        self.agent = MaestroAgent(ORCHESTRATOR_NAME)

    def break_down_objective(self, objective):
        system_prompt = (
            "You are the Orchestrator. Break down the user's objective into a list of specific, actionable sub-tasks. "
            "Think about UI/UX requirements, development tasks, and QA/testing needs. "
            "Output your response ONLY as a JSON list of strings."
        )
        response = self.agent.chat(f"Objective: {objective}", system_prompt)
        
        try:
            clean_response = response.strip()
            if "```json" in clean_response:
                clean_response = clean_response.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_response:
                clean_response = clean_response.split("```")[1].split("```")[0].strip()
            
            return json.loads(clean_response)
        except:
            return [line.strip() for line in response.split('\n') if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith('-'))]

class SpecializedAgent(MaestroAgent):
    def __init__(self, name, role_description):
        super().__init__(name)
        self.role_description = role_description

    def execute_task(self, task, context=""):
        system_prompt = f"You are a {self.name}. {self.role_description}\nContext: {context}"
        return self.chat(task, system_prompt)

class UIUXAgent(SpecializedAgent):
    def __init__(self):
        super().__init__("UI/UX Designer", "Design beautiful, intuitive interfaces. Focus on layout, colors, and user flow.")

class DevAgent(SpecializedAgent):
    def __init__(self):
        super().__init__("Developer", "Implement robust and efficient code. Focus on clean architecture and performance.")

class QAAgent(SpecializedAgent):
    def __init__(self):
        super().__init__("QA Tester", "Verify functionality and find bugs. Focus on edge cases and reliability.")

class Worker:
    def __init__(self):
        self.ui_ux = UIUXAgent()
        self.dev = DevAgent()
        self.qa = QAAgent()

    def execute_task(self, task, context=""):
        # Simple heuristic to route task to the right agent
        task_lower = task.lower()
        if any(keyword in task_lower for keyword in ["design", "ui", "ux", "layout", "css", "style"]):
            return self.ui_ux.execute_task(task, context), "UI/UX Designer"
        elif any(keyword in task_lower for keyword in ["test", "bug", "qa", "verify", "fix"]):
            return self.qa.execute_task(task, context), "QA Tester"
        else:
            return self.dev.execute_task(task, context), "Developer"

class Refiner:
    def __init__(self):
        self.agent = MaestroAgent(REFINER_NAME)

    def refine_results(self, objective, task_results):
        context = "\n\n".join([f"Task Result: {r}" for r in task_results])
        system_prompt = (
            f"You are the Refiner. Based on the original objective: '{objective}', "
            f"and the following results from specialized agents, produce a final, comprehensive, and polished output."
        )
        return self.agent.chat("Refine the results.", system_prompt + "\n\n" + context)

def run_maestro(objective):
    console.print(Panel(f"[bold blue]Objective:[/bold blue] {objective}"))
    
    orchestrator = Orchestrator()
    worker = Worker()
    refiner = Refiner()

    with console.status("[bold green]Orchestrating tasks...") as status:
        tasks = orchestrator.break_down_objective(objective)
    
    console.print(f"[bold yellow]Tasks identified:[/bold yellow] {len(tasks)}")
    for i, t in enumerate(tasks):
        console.print(f"  {i+1}. {t}")

    results = []
    for i, task in enumerate(tasks):
        with console.status(f"[bold cyan]Executing Task {i+1}/{len(tasks)}: {task}...") as status:
            result, agent_name = worker.execute_task(task)
            results.append(result)
            console.print(f"[bold green]Done Task {i+1} by {agent_name}[/bold green]")

    with console.status("[bold magenta]Refining final output...") as status:
        final_output = refiner.refine_results(objective, results)

    console.print("\n" + "="*50 + "\n")
    console.print(Panel(Markdown(final_output), title="Final Polished Output"))

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        obj = " ".join(sys.argv[1:])
    else:
        obj = input("Enter your objective: ")
    run_maestro(obj)
