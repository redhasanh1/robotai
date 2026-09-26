"""Episodic memory: learning with zero gradient steps. Every attempt (success or failure, with a one-line cause)
goes into SQLite; before each decision the most relevant past episodes go into the brain's prompt.

The robot gets better at "pick up the can" over a week because its context window holds what worked on cans,
not because anything was trained. Retrieval is deliberately simple (same object label first, then word overlap
with the goal, newest first) - swap in image embeddings later without changing callers.
"""
import json
import os
import re
import sqlite3
import time

SCHEMA = """CREATE TABLE IF NOT EXISTS episodes(
    id INTEGER PRIMARY KEY, t REAL, goal TEXT, object TEXT, family TEXT, s REAL, t_thumb REAL,
    q TEXT, success INTEGER, cause TEXT, source TEXT)"""


def _words(s):
    return set(re.findall(r"[a-z]+", (s or "").lower()))


class Memory:
    def __init__(self, path=":memory:"):
        if path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute(SCHEMA)

    def add(self, goal, obj, cand, success, cause="", source="sim"):
        self.db.execute("INSERT INTO episodes(t,goal,object,family,s,t_thumb,q,success,cause,source) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (time.time(), goal, obj, cand["family"], cand["s"], cand["t"], json.dumps(cand["q"]),
                         int(bool(success)), cause, source))
        self.db.commit()

    def recall(self, goal, obj, k=6):
        rows = self.db.execute("SELECT goal,object,family,s,t_thumb,success,cause FROM episodes "
                               "ORDER BY id DESC LIMIT 500").fetchall()
        gw = _words(goal)
        scored = sorted(rows, key=lambda r: (r[1] == obj, len(gw & _words(r[0]))), reverse=True)
        return [{"goal": r[0], "object": r[1], "family": r[2], "s": r[3], "t": r[4], "success": bool(r[5]),
                 "cause": r[6]} for r in scored[:k]]

    def best(self, obj):
        """Most successful (family, s, t) on this object so far, or None."""
        row = self.db.execute("SELECT family, AVG(s), AVG(t_thumb), SUM(success), COUNT(*) FROM episodes "
                              "WHERE object=? AND success=1 GROUP BY family ORDER BY SUM(success) DESC LIMIT 1",
                              (obj,)).fetchone()
        return None if row is None else {"family": row[0], "s": row[1], "t": row[2], "wins": row[3]}

    def as_prompt(self, goal, obj, k=6):
        eps = self.recall(goal, obj, k)
        if not eps:
            return "No past attempts yet."
        lines = [f"- {e['object']}: {e['family']} s={e['s']:.2f} t={e['t']:.2f} -> "
                 f"{'HELD' if e['success'] else 'DROPPED'}" + (f" ({e['cause']})" if e["cause"] else "") for e in eps]
        return "Past attempts (most relevant first):\n" + "\n".join(lines)

    def stats(self):
        n, w = self.db.execute("SELECT COUNT(*), COALESCE(SUM(success),0) FROM episodes").fetchone()
        return {"episodes": n, "successes": w}
