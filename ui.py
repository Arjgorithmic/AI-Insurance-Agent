import gradio as gr
import os
from main import run_agent
from tools import view_policies, check_renewals, add_policy
from langchain_core.messages import HumanMessage, AIMessage
from PyPDF2 import PdfReader
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

api_key = os.getenv("OpenRouterAPI")
model = os.getenv("AIModel")
base_url = os.getenv("OpenRouterBaseUrl")

llm = ChatOpenAI(
    model=model,
    base_url=base_url,
    api_key=api_key,
    temperature=0.3
)

history = []


def extract_text_from_file(file):
    if file is None:
        return ""
    try:
        if file.name.endswith(".pdf"):
            reader = PdfReader(file.name)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        elif file.name.endswith(".txt"):
            with open(file.name, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return ""
    except Exception as e:
        return f"Error reading file: {str(e)}"


def extract_policy_details(text: str) -> dict:
    """
    Use the LLM to extract structured insurance policy data from text.
    Expected keys: policy_name, provider, start_date, end_date, premium, summary
    """
    if not text.strip():
        return {}

    prompt = (
        "You are an expert insurance document reader. "
        "Extract and return a JSON object with these fields from the text below:\n"
        "policy_name, provider, start_date, end_date, premium, and summary.\n"
        "Dates must be in YYYY-MM-DD format if possible. "
        "Premium must be a number. Summary should be a short explanation of the coverage.\n\n"
        f"Policy Text:\n{text[:4000]}\n\n"
        "Return ONLY the JSON output, nothing else."
    )

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()

        # Try parsing JSON safely
        import json
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Sometimes LLM returns text with JSON inside
            import re
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
            else:
                data = {}

        # Fill defaults if missing
        data.setdefault("policy_name", "Unnamed Policy")
        data.setdefault("provider", "Unknown Provider")
        data.setdefault("start_date", "")
        data.setdefault("end_date", "")
        data.setdefault("premium", 0.0)
        data.setdefault("summary", "No summary extracted.")

        return data
    except Exception as e:
        return {"error": str(e)}


def handle_upload(file):
    text = extract_text_from_file(file)
    if not text:
        return "Failed to extract text from file. Please upload a valid PDF or TXT insurance document."

    data = extract_policy_details(text)
    if "error" in data:
        return f"Error extracting details: {data['error']}"

    try:
        premium_val = float(data.get("premium", 0.0))
    except Exception:
        premium_val = 0.0

    add_policy.invoke({
        "policy_name": data["policy_name"],
        "provider": data["provider"],
        "start_date": data["start_date"],
        "end_date": data["end_date"],
        "premium": premium_val,
        "details": data["summary"]
    })

    summary_display = (
        f"### Policy Extracted and Saved\n"
        f"**Policy Name:** {data['policy_name']}\n"
        f"**Provider:** {data['provider']}\n"
        f"**Start Date:** {data['start_date'] or '—'}\n"
        f"**End Date:** {data['end_date'] or '—'}\n"
        f"**Premium:** ₹{premium_val:,.2f}\n\n"
        f"**Summary:**\n{data['summary']}"
    )

    return summary_display


def chat_with_agent(user_input):
    global history
    response = run_agent(user_input, history)
    history += [HumanMessage(content=user_input), response]
    return response.content


def view_all_policies():
    return view_policies.invoke({})


def check_renewals_ui(days):
    try:
        d = int(days)
    except Exception:
        return "Enter a valid number for days."
    return check_renewals.invoke({"days_ahead": d})


with gr.Blocks(title="Insurance Assistant") as demo:
    gr.Markdown("## Insurance Assistant")

    with gr.Tab("Chat"):
        chatbot = gr.Chatbot(type="messages")
        msg = gr.Textbox(label="Ask about your insurance policies:")
        clear = gr.Button("Clear Chat")

        def user_chat(user_msg, chat_history):
            response = chat_with_agent(user_msg)
            chat_history.append({"role": "user", "content": user_msg})
            chat_history.append({"role": "assistant", "content": response})
            return "", chat_history

        msg.submit(user_chat, [msg, chatbot], [msg, chatbot])
        clear.click(lambda: ([], ""), None, [chatbot, msg])

    with gr.Tab("Upload Policy Document"):
        file_input = gr.File(label="Upload insurance document (PDF or TXT)")
        upload_btn = gr.Button("Extract & Save Policy")
        output_summary = gr.Markdown()
        upload_btn.click(handle_upload, inputs=[file_input], outputs=output_summary)

    with gr.Tab("View Policies"):
        view_btn = gr.Button("Refresh Policies")
        policies_output = gr.Textbox(label="Stored Policies", lines=10)
        view_btn.click(view_all_policies, None, policies_output)

    with gr.Tab("Renewal Reminders"):
        days_input = gr.Number(label="Days Ahead", value=30)
        check_btn = gr.Button("Check Renewals")
        renewal_output = gr.Textbox(label="Upcoming Renewals", lines=8)
        check_btn.click(check_renewals_ui, inputs=[days_input], outputs=renewal_output)

demo.launch(server_name="0.0.0.0", server_port=7865)
