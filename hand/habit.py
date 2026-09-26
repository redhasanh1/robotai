"""Habits: learning when NOT to think (Kimi round 6, the "smallest real post-training").

After the robot has succeeded with the same grasp family on the same object often enough, it stops asking the big
model and just does it - like a person who no longer thinks about picking up a cup. The model is still asked when
the habit is weak, the object is new, or the habit starts failing (a failure lowers confidence immediately).

The "training" is a Beta-Bernoulli count per (object, family) from episodic memory - microseconds, no GPU, and it
only ever uses what the robot BELIEVED happened (same rule as hand.memory).

    h = habit.lookup(memory, "ball")      # None, or {"family", "s", "t", "p", "n"}
"""
MIN_TRIES = 3          # never a habit before this many attempts with the family
MIN_P = 0.8            # posterior mean success needed to skip the model


def lookup(memory, obj, min_tries=MIN_TRIES, min_p=MIN_P):
    rows = memory.db.execute(
        "SELECT family, SUM(success), COUNT(*), AVG(CASE WHEN success=1 THEN s END), "
        "AVG(CASE WHEN success=1 THEN t_thumb END) FROM episodes WHERE object=? GROUP BY family", (obj,)).fetchall()
    best = None
    for fam, wins, n, s, t in rows:
        p = (wins + 1) / (n + 2)                 # Beta(1,1) prior: 3/3 -> 0.8, 5/5 -> 0.86, 4/5 -> 0.71
        if n >= min_tries and p >= min_p and (best is None or p > best["p"]):
            best = {"family": fam, "s": s, "t": t, "p": round(p, 3), "n": n}
    if best is None:
        return None
    # a habit is only as good as its last try: one fresh failure and the model is consulted again
    last = memory.db.execute("SELECT success FROM episodes WHERE object=? AND family=? ORDER BY id DESC LIMIT 1",
                             (obj, best["family"])).fetchone()
    return best if last and last[0] == 1 else None
