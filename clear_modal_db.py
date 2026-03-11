import modal
import os
import shutil

# use this command to clear the modal db in case of embedding model change
# modal run clear_modal_db.py

app = modal.App("qa-rag-agent-cleanup")
volume = modal.Volume.from_name("qa-rag-agent-data", create_if_missing=True)

@app.function(volumes={"/root/data": volume})
def clear_db():
    db_path = "/root/data/chroma_db"
    if os.path.exists(db_path):
        print(f"🗑️ Deleting remote Chroma database at {db_path}...")
        shutil.rmtree(db_path)
        print("✅ Database successfully wiped!")
    else:
        print(f"ℹ️ Database at {db_path} does not exist. Nothing to clear.")

@app.local_entrypoint()
def main():
    clear_db.remote()
