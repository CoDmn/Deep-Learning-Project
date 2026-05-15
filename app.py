import gradio as gr
from src.agent import ConvoTutor

agent = ConvoTutor(max_kb_items=5000)

_LEVEL_BADGE = {
    "simple": "🟢  Simple  (Beginner)",
    "normal": "🟡  Normal  (Intermediate)",
    "expert": "🔵  Expert  (Advanced)",
}


def _fmt_confusion(confused: bool, reason: str, similarity: float) -> str:
    if not confused:
        sim_text = f"  (similarity: {similarity:.0%})" if similarity > 0 else ""
        return f"✅  No confusion detected{sim_text}"
    lines = ["⚠️  Confusion detected"]
    if reason == "explicit_phrase":
        lines.append("  Reason: explicit confusion phrase")
    elif reason == "semantic_repetition":
        lines.append(f"  Reason: semantically similar to recent question ({similarity:.0%})")
    return "\n".join(lines)


def _fmt_retrieved(count: int, snippets: list) -> str:
    if count == 0:
        return "No passages retrieved."
    lines = [f"Retrieved {count} passage(s) from QReCC:\n"]
    for i, s in enumerate(snippets, 1):
        lines.append(f"[{i}]  {s}…")
    return "\n".join(lines)


def _fmt_memory(mem: dict) -> str:
    lines = [
        f"Total turns   : {mem['turns']}",
        f"Teaching level: {mem['current_level']}",
        f"Confusion run : {mem['confusion_streak']}",
        f"Clear run     : {mem['clear_streak']}",
    ]
    if mem["recent_questions"]:
        lines.append("\nRecent questions:")
        for q in mem["recent_questions"]:
            lines.append(f"  • {q}")
    return "\n".join(lines)


def chat(message: str, history: list):
    if not message.strip():
        yield history, "", "", "", "", ""
        return

    answer, meta = agent.chat(message)
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": answer},
    ]

    yield (
        history,
        _LEVEL_BADGE.get(meta["level"], meta["level"]),
        _fmt_confusion(meta["confused"], meta["confusion_reason"], meta["confusion_similarity"]),
        meta["rewritten_question"],
        _fmt_retrieved(meta["retrieved_count"], meta["retrieved_snippets"]),
        _fmt_memory(meta["memory"]),
    )


def reset():
    agent.reset()
    return [], "", "", "", "", ""


def clear_input():
    return ""


_EXAMPLES = [
    "What is machine learning?",
    "I don't understand, can you explain again in simpler terms?",
    "What is the difference between supervised and unsupervised learning?",
    "How does gradient descent work in neural networks?",
    "What is backpropagation and how does it relate to the chain rule?",
]

with gr.Blocks(title="ConvoTutor — Adaptive Learning Agent") as demo:

    gr.Markdown("""
    # ConvoTutor
    ### Adaptive Conversational Learning Agent · QReCC-based
    Ask any question. The agent adapts its explanation level based on your understanding.
    """)

    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(height=480, label="Conversation")

            with gr.Row():
                msg_box = gr.Textbox(
                    placeholder="Type your question and press Enter…",
                    label="Your question",
                    lines=1,
                    scale=5,
                )
                send_btn = gr.Button("Send", variant="primary", scale=1)

            reset_btn = gr.Button("Reset conversation", variant="secondary")

            gr.Examples(examples=_EXAMPLES, inputs=msg_box, label="Example questions")

        with gr.Column(scale=2):
            gr.Markdown("### Agent Internals")
            level_box     = gr.Textbox(label="Teaching level",           interactive=False, lines=1)
            confusion_box = gr.Textbox(label="Confusion detector",       interactive=False, lines=3)
            rewrite_box   = gr.Textbox(label="Rewritten question",       interactive=False, lines=2)
            retrieved_box = gr.Textbox(label="Retrieved context (BM25)", interactive=False, lines=5)
            memory_box    = gr.Textbox(label="Conversation memory",      interactive=False, lines=7)

    outputs = [chatbot, level_box, confusion_box, rewrite_box, retrieved_box, memory_box]

    send_btn.click(fn=chat, inputs=[msg_box, chatbot], outputs=outputs).then(
        fn=clear_input, inputs=[], outputs=msg_box
    )
    msg_box.submit(fn=chat, inputs=[msg_box, chatbot], outputs=outputs).then(
        fn=clear_input, inputs=[], outputs=msg_box
    )
    reset_btn.click(fn=reset, inputs=[], outputs=outputs)


if __name__ == "__main__":
    demo.launch(server_port=7861, share=False, inbrowser=True)
