"""Control panel: watch the sim, see what's running, and one big STOP ALL button.

    .venv/Scripts/pythonw tools/panel.py        (pythonw = no console window)

STOP ALL kills every robot program started from this repo (sim demo, local AI model server, benchmarks,
brain runs, estimator eval) by process id - it never touches the website/viewer servers or anything else.
To interrupt Claude in the terminal, press Esc there.
"""
import os
import queue
import subprocess
import sys
import tkinter as tk

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
TOOLS = ("demo.py", "bench.py", "brain_live.py", "local_vlm_server.py", "estimator_eval.py",
         "servo_characterize.py", "run_hand.py", "ablation.py", "link_jitter.py", "arm_view.py")
PS_LIST = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | "
           "Select-Object ProcessId, CommandLine | ConvertTo-Json -Compress")


def robot_processes():
    """[(pid, tool name)] for python processes running one of our tools (or their worker children)."""
    import json
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", PS_LIST], capture_output=True, text=True,
                             timeout=15, creationflags=subprocess.CREATE_NO_WINDOW).stdout.strip()
        rows = json.loads(out) if out else []
    except Exception:
        return []
    rows = rows if isinstance(rows, list) else [rows]
    found = []
    for r in rows:
        cmd = r.get("CommandLine") or ""
        for t in TOOLS:
            if t in cmd:
                found.append((int(r["ProcessId"]), t))
        if "multiprocessing" in cmd and "robotai" in cmd.lower():       # sim worker pool children
            found.append((int(r["ProcessId"]), "sim worker"))
    return found


class Panel:
    def __init__(self):
        self.w = tk.Tk()
        self.w.title("PINN Humanoid - control")
        self.w.geometry("440x640+40+40")
        self.w.attributes("-topmost", True)
        tk.Label(self.w, text="PINN Humanoid", font=("Segoe UI", 14, "bold")).pack(pady=(10, 4))
        tk.Label(self.w, text="Tell the robot (e.g. pick up the orange):", anchor="w").pack(fill="x", padx=16)
        row = tk.Frame(self.w)
        row.pack(fill="x", padx=16, pady=(0, 6))
        self.cmd = tk.Entry(row, font=("Segoe UI", 11))
        self.cmd.pack(side="left", fill="x", expand=True)
        self.cmd.bind("<Return>", lambda _e: self.say())
        tk.Button(row, text="Do it", command=self.say).pack(side="left", padx=(6, 0))
        self.out = tk.Text(self.w, height=8, font=("Consolas", 9), wrap="word")
        self.out.pack(fill="x", padx=16)
        tk.Button(self.w, text="▶  Sim hand: grab 4 objects (plays once)", font=("Segoe UI", 11),
                  command=self.watch).pack(fill="x", padx=16, pady=(8, 3))
        tk.Button(self.w, text="▶  Full robot: arm reaches, hand closes", font=("Segoe UI", 11),
                  command=lambda: self.launch("arm_view.py", "--demo")).pack(fill="x", padx=16, pady=3)
        tk.Button(self.w, text="▶  Full robot with sliders (move every joint)", font=("Segoe UI", 11),
                  command=lambda: self.launch("arm_view.py")).pack(fill="x", padx=16, pady=3)
        tk.Button(self.w, text="■  STOP ALL", font=("Segoe UI", 16, "bold"), bg="#d33", fg="white",
                  activebackground="#a11", command=self.stop_all).pack(fill="x", padx=16, pady=8, ipady=10)
        self.status = tk.Label(self.w, text="", font=("Consolas", 9), justify="left", anchor="w")
        self.status.pack(fill="both", expand=True, padx=16)
        tk.Label(self.w, text="To interrupt Claude: press Esc in the terminal", fg="#666").pack(pady=(0, 8))
        self.lines = queue.Queue()
        self.drain()
        self.refresh()

    def drain(self):
        """Main-thread side: move lines from the reader thread into the text box."""
        while not self.lines.empty():
            self.out.insert("end", self.lines.get())
            self.out.see("end")
        self.w.after(150, self.drain)

    def watch(self):
        subprocess.Popen([PY, os.path.join(ROOT, "tools", "demo.py"), "--watch"], cwd=ROOT,
                         creationflags=subprocess.CREATE_NO_WINDOW)
        self.w.after(1500, self.refresh)

    def launch(self, tool, *args):
        subprocess.Popen([PY, os.path.join(ROOT, "tools", tool), *args], cwd=ROOT,
                         creationflags=subprocess.CREATE_NO_WINDOW)
        self.w.after(1500, self.refresh)

    def say(self):
        text = self.cmd.get().strip()
        if not text:
            return
        self.out.delete("1.0", "end")
        self.out.insert("end", "thinking...\n")
        p = subprocess.Popen([PY, "-u", os.path.join(ROOT, "tools", "demo.py"), "--say", text], cwd=ROOT,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             creationflags=subprocess.CREATE_NO_WINDOW)

        def pump():                                   # reader thread: never touch Tk here, only the queue
            for line in p.stdout:
                self.lines.put(line)
        import threading
        threading.Thread(target=pump, daemon=True).start()
        self.w.after(1500, self.refresh)

    def stop_all(self):
        procs = robot_processes()
        for pid, _ in procs:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        self.status.config(text=f"stopped {len(procs)} process(es)")
        self.w.after(1500, self.refresh)

    def refresh(self):
        procs = robot_processes()
        lines = [f"{t:22s} pid {p}" for p, t in procs] or ["nothing running"]
        self.status.config(text="Running now:\n" + "\n".join(lines))
        self.w.after(4000, self.refresh)


if __name__ == "__main__":
    Panel().w.mainloop()
