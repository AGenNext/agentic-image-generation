"""
GenAgent: Agentic Image Generation Controller

This module wires tools into an agent loop that plans, generates,
critiques, and improves images iteratively.
"""

from tools.image_tools import ImageTools


class GenAgent:
    def __init__(self, diffusion_model, vision_model, max_iters: int = 3):
        self.tools = ImageTools(diffusion_model, vision_model)
        self.max_iters = max_iters

    def run(self, user_prompt: str):
        """Main execution loop"""
        print(f"[GenAgent] Input Prompt: {user_prompt}")

        # Step 1: refine prompt
        prompt = self.tools.refine_prompt(user_prompt)
        print(f"[GenAgent] Refined Prompt: {prompt}")

        # Step 2: initial generation
        result = self.tools.generate_image(prompt)

        # Step 3: iterative improvement
        for i in range(self.max_iters):
            print(f"[GenAgent] Iteration {i+1}")

            feedback = self.tools.critique_image(result["image"])
            print(f"[GenAgent] Feedback: {feedback}")

            improved = self.tools.improve_image(result["image"], feedback)
            result["image"] = improved

        print("[GenAgent] Generation complete")
        return result


# Example usage
if __name__ == "__main__":
    class DummyDiffusion:
        def generate(self, prompt, steps=30):
            return f"[IMAGE for: {prompt}]"

    class DummyVision:
        def describe(self, image):
            return "Improve lighting, add more details"

    agent = GenAgent(DummyDiffusion(), DummyVision())
    output = agent.run("A futuristic city at sunset")
    print(output)
