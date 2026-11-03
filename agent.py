import os, json, anthropic
from tools import extract_data, simulate_to_excel

client = anthropic.Anthropic()                    # baca ANTHROPIC_API_KEY otomatis
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

SYSTEM = """Kamu adalah agent simulasi data Excel.
Tugas: pahami struktur data dari hasil ekstraksi (jika ada file), lalu rancang
skema kolom yang realistis dan panggil simulate_to_excel.
Aturan: gunakan nama kolom sesuai data asli, rentang nilai yang masuk akal,
dan jawab ke user dalam Bahasa Indonesia secara singkat."""

TOOLS = [
    {
        "name": "extract_data",
        "description": "Ekstrak isi/struktur dari file yang diunggah user menggunakan service extractor.",
        "input_schema": {
            "type": "object",
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"],
        },
    },
    {
        "name": "simulate_to_excel",
        "description": "Buat file Excel berisi data simulasi dari skema kolom.",
        "input_schema": {
            "type": "object",
            "properties": {
                "n_rows": {"type": "integer"},
                "seed": {"type": "integer"},
                "sheet_name": {"type": "string"},
                "columns": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string",
                                     "enum": ["int", "float", "category", "date", "id"]},
                            "min": {"type": "number"}, "max": {"type": "number"},
                            "mean": {"type": "number"}, "std": {"type": "number"},
                            "values": {"type": "array", "items": {"type": "string"}},
                            "weights": {"type": "array", "items": {"type": "number"}},
                            "start": {"type": "string"}, "end": {"type": "string"},
                            "prefix": {"type": "string"},
                        },
                        "required": ["name", "type"],
                    },
                },
            },
            "required": ["columns"],
        },
    },
]

HANDLERS = {"extract_data": extract_data, "simulate_to_excel": simulate_to_excel}


def run_agent(instruction: str, file_path: str | None = None, max_steps: int = 8):
    user_text = instruction
    if file_path:
        user_text += f"\n\n(File yang diunggah ada di: {file_path})"
    messages = [{"role": "user", "content": user_text}]
    result_file = None

    for _ in range(max_steps):
        resp = client.messages.create(
            model=MODEL, max_tokens=4000, system=SYSTEM,
            tools=TOOLS, messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            text = "".join(b.text for b in resp.content if b.type == "text")
            return {"message": text, "file_id": result_file}

        tool_results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            try:
                out = HANDLERS[block.name](**block.input)
                if block.name == "simulate_to_excel":
                    result_file = out["file_id"]
                content, is_err = json.dumps(out, ensure_ascii=False, default=str)[:20000], False
            except Exception as e:
                content, is_err = f"Error: {e}", True
            tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                 "content": content, "is_error": is_err})
        messages.append({"role": "user", "content": tool_results})

    return {"message": "Batas langkah agent tercapai.", "file_id": result_file}