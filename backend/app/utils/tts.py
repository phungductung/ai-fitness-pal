from openai import OpenAI
import os

class MorningBriefing:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def generate_briefing_audio(self, text: str, output_path: str = "morning_briefing.mp3", voice: str = "onyx"):
        """Generate a daily morning briefing using OpenAI TTS."""
        response = self.client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        response.stream_to_file(output_path)
        return output_path

    def compose_briefing_text(self, pr_data: list, nutrition_summary: dict):
        """Construct the briefing script based on user data."""
        # Simple template for the briefing
        briefing = f"Good morning! Here is your AI Fitness Architect briefing.\n"
        if pr_data:
            briefing += f"Your last recorded PR was {pr_data[-1]['Exercise']} at {pr_data[-1]['Weight']}kg. Great work!\n"
        briefing += f"Based on your goal, today's target is {nutrition_summary.get('calories', 2500)} calories and {nutrition_summary.get('protein_g', 180)}g of protein.\n"
        briefing += "Keep pushing hard and stay hydrated."
        return briefing
