import os, uuid, httpx
import numpy as np
import pandas as pd

EXTRACTOR_URL = os.environ["EXTRACTOR_URL"]   # contoh: http://extractor.railway.internal:8000
DATA_DIR = os.getenv("DATA_DIR", "/data")
os.makedirs(DATA_DIR, exist_ok=True)


def extract_data(file_path: str) -> dict:
    """Kirim file ke service extractor, kembalikan hasil ekstraksi (JSON)."""
    with open(file_path, "rb") as f:
        r = httpx.post(
            f"{EXTRACTOR_URL}/extract",           # sesuaikan dengan endpoint Anda
            files={"file": (os.path.basename(file_path), f)},
            timeout=120,
        )
    r.raise_for_status()
    return r.json()


def _make_column(spec: dict, n: int, rng: np.random.Generator):
    t = spec["type"]
    if t == "int":
        return rng.integers(spec.get("min", 0), spec.get("max", 100) + 1, n)
    if t == "float":
        if "mean" in spec:
            return np.round(rng.normal(spec["mean"], spec.get("std", 1), n), 2)
        return np.round(rng.uniform(spec.get("min", 0), spec.get("max", 1), n), 2)
    if t == "category":
        return rng.choice(spec["values"], n, p=spec.get("weights"))
    if t == "date":
        start = pd.Timestamp(spec["start"]); end = pd.Timestamp(spec["end"])
        days = (end - start).days
        return start + pd.to_timedelta(rng.integers(0, days + 1, n), unit="D")
    if t == "id":
        prefix = spec.get("prefix", "ID")
        return [f"{prefix}-{i+1:05d}" for i in range(n)]
    raise ValueError(f"Tipe kolom tidak dikenal: {t}")


def simulate_to_excel(columns: list, n_rows: int = 100, seed: int = 42,
                      sheet_name: str = "Simulasi") -> dict:
    """Buat data simulasi dari skema kolom dan simpan sebagai .xlsx."""
    n_rows = min(int(n_rows), 100_000)           # batas aman
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({c["name"]: _make_column(c, n_rows, rng) for c in columns})

    file_id = uuid.uuid4().hex[:12]
    path = os.path.join(DATA_DIR, f"{file_id}.xlsx")
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name=sheet_name)
        ws = w.sheets[sheet_name]
        for col in ws.columns:                    # auto lebar kolom
            ws.column_dimensions[col[0].column_letter].width = \
                min(40, max(len(str(c.value or "")) for c in col) + 2)

    return {"file_id": file_id, "rows": n_rows, "columns": list(df.columns),
            "preview": df.head(5).astype(str).to_dict(orient="records")}