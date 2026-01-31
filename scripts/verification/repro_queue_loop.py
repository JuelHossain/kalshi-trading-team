
import asyncio
import os
import sqlite3
import uuid
from datetime import datetime
from pydantic import BaseModel, Field

# Mocking the minimal classes needed
class MarketData(BaseModel):
    ticker: str
    title: str = ""
    subtitle: str = ""
    yes_price: int = 50
    no_price: int = 50
    volume: int = 0
    expiration: str = ""

class Opportunity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ticker: str
    market_data: MarketData
    priority: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)

class PersistentQueue:
    def __init__(self, db_path, table_name, model_cls):
        self.db_path = db_path
        self.table_name = table_name
        self.model_cls = model_cls
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {self.table_name} (id TEXT PRIMARY KEY, priority INTEGER, timestamp REAL, payload TEXT, status TEXT)")
        conn.commit()
        conn.close()

    async def push(self, item, priority=0):
        # simplified push
        conn = sqlite3.connect(self.db_path)
        payload = item.model_dump_json()
        item_id = item.id
        ts = datetime.now().timestamp()
        conn.execute(f"INSERT OR REPLACE INTO {self.table_name} VALUES (?, ?, ?, ?, 'QUEUED')", (item_id, priority, ts, payload))
        conn.commit()
        conn.close()

    async def pop(self):
        return await asyncio.to_thread(self._pop_sync)

    def _pop_sync(self):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT id, payload FROM {self.table_name} WHERE status='QUEUED' LIMIT 1")
            row = cursor.fetchone()
            if row:
                item_id, payload = row
                print(f"[DEBUG] Popped item {item_id}. Deleting...")
                cursor.execute(f"DELETE FROM {self.table_name} WHERE id = ?", (item_id,))
                conn.commit()
                print(f"[DEBUG] Deleted item {item_id}.")
                return self.model_cls.model_validate_json(payload)
            return None
        finally:
            conn.close()

async def run_test():
    db_file = "test_queue.db"
    if os.path.exists(db_file):
        os.remove(db_file)
    
    queue = PersistentQueue(db_file, "queue_opportunities", Opportunity)
    
    # Push 1 item
    opp = Opportunity(ticker="KXQUICK", market_data=MarketData(ticker="KXQUICK"))
    print(f"Pushing item {opp.id}")
    await queue.push(opp)
    
    # Pop loop
    for i in range(5):
        print(f"Iteration {i}")
        item = await queue.pop()
        if item:
            print(f"Got item: {item.id}")
        else:
            print("Queue empty.")
            break
        
        # Simulate processing failure (no-op, just next loop)
        
    if os.path.exists(db_file):
        os.remove(db_file)

if __name__ == "__main__":
    asyncio.run(run_test())
