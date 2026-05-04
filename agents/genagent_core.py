"""
Advanced GenAgent Core

Adds planning, tool selection, and memory to transform the basic
agent into a true GenAgent-style system.
"""

from tools.image_tools import ImageTools


class GenAgentCore:
    def __init__(self, diffusion_model, vision_model, llm=None, max_iters: int = 5):
        self.tools = ImageTools(diffusion_model, vision_model)
        self.llm = llm  # optional LLM for planning/tool selection
        self.max_iters = max_iters
        self.memory = []

    # -----------------------------
    # Planning
    # -----------------------------
    def plan(self, prompt: str):
        """Create a dynamic execution plan"""
        return [
            "refine_prompt",
            "generate_image",
            "critique_image",
            "improve_image"
        ]

    # -----------------------------
    # Tool selection (LLM optional)
    # -----------------------------
    def decide_next_action(self, feedback: str):
        if self.llm:
            return self.llm.predict(f"Decide next tool based on: {feedback}")

        # fallback heuristic
        if "lighting" in feedback.lower():
            return "improve_image"
        elif "detail" in feedback.lower():
            return "improve_image"
        else:
            return "generate_image"

    # -----------------------------
    # Main loop
    # -----------------------------
    def run(self, user_prompt: str):
        print(f"[GenAgentCore] Prompt: {user_prompt}")

        plan = self.plan(user_prompt)
        prompt = user_prompt
        result = {"image": None}

        for step in plan:
            if step == "refine_prompt":
                prompt = self.tools.refine_prompt(prompt)

            elif step == "generate_image":
                result = self.tools.generate_image(prompt)

            elif step == "critique_image":
                feedback = self.tools.critique_image(result["image"])

                self.memory.append({
                    "prompt": prompt,
                    "feedback": feedback
                })

            elif step == "improve_image":
                for i in range(self.max_iters):
                    action = self.decide_next_action(feedback)

                    if action == "improve_image":
                        result["image"] = self.tools.improve_image(result["image"], feedback)
                    else:
                        result = self.tools.generate_image(prompt)

                    feedback = self.tools.critique_image(result["image"])

                    self.memory.append({
                        "iteration": i,
                        "feedback": feedback
                    })

        print("[GenAgentCore] Done")
        return result


# Example usage
if __name__ == "__main__":
    class DummyDiffusion:
        def generate(self, prompt, steps=30):
            return f"[IMAGE: {prompt}]"

    class DummyVision:
        def describe(self, image):
            return "Improve lighting and add more detail"

    agent = GenAgentCore(DummyDiffusion(), DummyVision())
    output = agent.run("A dragon flying over a neon city")
    print(output)
