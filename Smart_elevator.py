import tkinter as tk
from tkinter import ttk, messagebox
import time
import threading
from datetime import datetime
from collections import deque

# ─────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────

FLOORS     = 10
BG         = "#1a1a2e"
PANEL_BG   = "#16213e"
ACCENT     = "#7b2ff7"
ACCENT2    = "#a855f7"
GOLD       = "#f5a623"
GREEN      = "#22c55e"
RED        = "#ef4444"
WHITE      = "#e2e8f0"
GRAY       = "#475569"
SHAFT_BG   = "#0f172a"
CAB_COLOR  = "#7b2ff7"
CAB_OUTLINE= "#c084fc"
DOOR_COLOR = "#a855f7"

FLOOR_H    = 54
SHAFT_W    = 70
SHAFT_X    = 40
ANIM_STEPS = 30
DOOR_STEPS = 12

# ─────────────────────────────────────────
#  DATA CLASSES
# ─────────────────────────────────────────

class Person:
    def __init__(self, person_id, current_floor, destination):
        self.person_id     = person_id
        self.current_floor = current_floor
        self.destination   = destination
        self.wait_start    = time.time()
        self.wait_time     = 0.0

    def boarded(self):
        self.wait_time = time.time() - self.wait_start


class Floor:
    def __init__(self, number):
        self.number       = number
        self.waiting_up   = []
        self.waiting_down = []
        self.button_up    = False
        self.button_down  = False

    def add_person(self, person):
        if person.destination > self.number:
            self.waiting_up.append(person)
            self.button_up = True
        elif person.destination < self.number:
            self.waiting_down.append(person)
            self.button_down = True

    def board_passengers(self, direction, elevator):
        boarded = []
        queue = self.waiting_up if direction == "up" else self.waiting_down
        while queue and len(elevator.passengers) < elevator.capacity:
            p = queue.pop(0)
            p.boarded()
            elevator.passengers.append(p)
            elevator.destinations.add(p.destination)
            boarded.append(p)
        if not self.waiting_up:
            self.button_up = False
        if not self.waiting_down:
            self.button_down = False
        return boarded


class Elevator:
    DOOR_CLOSED  = "closed"
    DOOR_OPENING = "opening"
    DOOR_OPEN    = "open"
    DOOR_CLOSING = "closing"

    def __init__(self, capacity=8, total_floors=10):
        self.capacity      = capacity
        self.total_floors  = total_floors
        self.current_floor = 1
        self.direction     = "idle"
        self.door_state    = self.DOOR_CLOSED
        self.passengers    = []
        self.destinations  = set()
        self.hold_door     = False
        self.emergency     = False
        self.position      = 1.0   # fractional floor pos for animation

    @property
    def is_overloaded(self):
        return len(self.passengers) > self.capacity

    def remove_arrived(self):
        arrived = [p for p in self.passengers
                   if p.destination == self.current_floor]
        self.passengers = [p for p in self.passengers
                           if p.destination != self.current_floor]
        self.destinations.discard(self.current_floor)
        return arrived


class Controller:
    def __init__(self, elevator, floors):
        self.elevator          = elevator
        self.floors            = floors
        self.external_requests = set()
        self._lock             = threading.Lock()

    def request_floor(self, floor_num):
        with self._lock:
            self.external_requests.add(floor_num)

    def all_destinations(self):
        with self._lock:
            return self.elevator.destinations | set(self.external_requests)

    def next_stop(self):
        targets   = self.all_destinations()
        if not targets:
            return None
        cur       = self.elevator.current_floor
        direction = self.elevator.direction
        above = sorted(f for f in targets if f > cur)
        below = sorted((f for f in targets if f < cur), reverse=True)
        if direction == "up":
            return above[0] if above else (below[0] if below else None)
        elif direction == "down":
            return below[0] if below else (above[0] if above else None)
        else:
            return min(targets, key=lambda f: abs(f - cur))

    def decide_direction(self):
        nxt = self.next_stop()
        if nxt is None:
            self.elevator.direction = "idle"
        elif nxt > self.elevator.current_floor:
            self.elevator.direction = "up"
        elif nxt < self.elevator.current_floor:
            self.elevator.direction = "down"

    def clear_external(self, floor_num):
        with self._lock:
            self.external_requests.discard(floor_num)


class Building:
    def __init__(self, num_floors=10):
        self.num_floors      = num_floors
        self.floors          = [Floor(i + 1) for i in range(num_floors)]
        self.elevator        = Elevator(capacity=8, total_floors=num_floors)
        self.controller      = Controller(self.elevator, self.floors)
        self._person_counter = 0

    def call_elevator(self, floor_num, destination):
        self._person_counter += 1
        p = Person(self._person_counter, floor_num, destination)
        self.floors[floor_num - 1].add_person(p)
        self.controller.request_floor(floor_num)

    def press_inside(self, floor_num):
        self.elevator.destinations.add(floor_num)


# ─────────────────────────────────────────
#  GUI
# ─────────────────────────────────────────

class ElevatorGUI:
    _door_ratio = 0.0

    def __init__(self, root):
        self.root      = root
        self.building  = Building(FLOORS)
        self.elev      = self.building.elevator
        self.ctrl      = self.building.controller
        self.running   = True
        self.log_entries = deque(maxlen=200)

        root.title("Smart Elevator Simulator — 10 Floors")
        root.configure(bg=BG)
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()

        t = threading.Thread(target=self._sim_loop, daemon=True)
        t.start()
        self._anim_loop()

    # ── UI ────────────────────────────────

    def _build_ui(self):
        main = tk.Frame(self.root, bg=BG)
        main.pack(padx=10, pady=10)

        canvas_h = FLOORS * FLOOR_H + 20
        canvas_w = SHAFT_X + SHAFT_W + 80
        self.canvas = tk.Canvas(main, width=canvas_w, height=canvas_h,
                                bg=BG, highlightthickness=0)
        self.canvas.grid(row=0, column=0, rowspan=2, padx=(0, 10), sticky="ns")
        self._draw_building_static()

        ctrl_frame = tk.Frame(main, bg=PANEL_BG, bd=2, relief="groove")
        ctrl_frame.grid(row=0, column=1, sticky="ne", padx=4, pady=4)
        self._build_control_panel(ctrl_frame)

        log_frame = tk.Frame(main, bg=PANEL_BG, bd=2, relief="groove")
        log_frame.grid(row=1, column=1, sticky="nsew", padx=4, pady=4)
        self._build_log_panel(log_frame)

    def _draw_building_static(self):
        c = self.canvas
        sx, sy = SHAFT_X, 10
        sh     = FLOORS * FLOOR_H

        # shaft
        c.create_rectangle(sx, sy, sx + SHAFT_W, sy + sh,
                           fill=SHAFT_BG, outline=GRAY, width=2)

        self.arrow_tags = {}
        for i in range(FLOORS):
            floor_num = FLOORS - i
            y_top     = 10 + i * FLOOR_H

            # separator
            c.create_line(sx, y_top + FLOOR_H, sx + SHAFT_W, y_top + FLOOR_H,
                          fill=GRAY, dash=(3, 3))

            # floor number
            c.create_text(sx - 8, y_top + FLOOR_H // 2,
                          text=str(floor_num), fill=WHITE,
                          font=("Consolas", 10, "bold"), anchor="e")

            bx = sx + SHAFT_W + 14
            mid = y_top + FLOOR_H // 2
            self.arrow_tags[f"up_{floor_num}"] = c.create_text(
                bx, mid - 9, text="▲", fill=GRAY, font=("Consolas", 9))
            self.arrow_tags[f"dn_{floor_num}"] = c.create_text(
                bx, mid + 9, text="▼", fill=GRAY, font=("Consolas", 9))

        # cab group (will be moved every frame)
        self.cab_body = c.create_rectangle(0, 0, 1, 1,
                                           fill=CAB_COLOR, outline=CAB_OUTLINE, width=2)
        self.cab_arrow = c.create_text(0, 0, text="■",
                                       fill=WHITE, font=("Consolas", 13, "bold"))
        # door left / right
        self.door_left  = c.create_rectangle(0, 0, 1, 1, fill=DOOR_COLOR, outline="")
        self.door_right = c.create_rectangle(0, 0, 1, 1, fill=DOOR_COLOR, outline="")

    def _floor_cy(self, floor_pos):
        """Canvas Y center for a fractional floor position."""
        idx = FLOORS - floor_pos
        return 10 + idx * FLOOR_H + FLOOR_H / 2

    def _build_control_panel(self, parent):
        tk.Label(parent, text="🏢  ELEVATOR CONTROL",
                 bg=PANEL_BG, fg=ACCENT2,
                 font=("Consolas", 11, "bold")).pack(pady=(8, 4))

        # status row
        sf = tk.Frame(parent, bg=PANEL_BG)
        sf.pack(fill="x", padx=8)
        self.lbl_floor = self._slabel(sf, "Floor", "1")
        self.lbl_dir   = self._slabel(sf, "Dir",   "IDLE")
        self.lbl_door  = self._slabel(sf, "Door",  "CLOSED")
        self.lbl_pax   = self._slabel(sf, "Pax",   "0/8")

        ttk.Separator(parent).pack(fill="x", padx=8, pady=5)

        # inside buttons
        tk.Label(parent, text="Inside Panel", bg=PANEL_BG, fg=GOLD,
                 font=("Consolas", 9)).pack()
        bg_f = tk.Frame(parent, bg=PANEL_BG)
        bg_f.pack(padx=8, pady=4)
        self.floor_btns = {}
        floors_order = list(range(FLOORS, 0, -1))
        for idx, fl in enumerate(floors_order):
            row, col = divmod(idx, 5)
            b = tk.Button(bg_f, text=str(fl), width=3,
                          bg=PANEL_BG, fg=WHITE,
                          activebackground=ACCENT,
                          font=("Consolas", 9, "bold"), relief="raised", bd=2,
                          command=lambda f=fl: self._inside_press(f))
            b.grid(row=row, column=col, padx=2, pady=2)
            self.floor_btns[fl] = b

        ttk.Separator(parent).pack(fill="x", padx=8, pady=5)

        # call from floor
        tk.Label(parent, text="Call From Floor", bg=PANEL_BG, fg=GOLD,
                 font=("Consolas", 9)).pack()
        cf = tk.Frame(parent, bg=PANEL_BG)
        cf.pack(padx=8, pady=4)

        tk.Label(cf, text="From:", bg=PANEL_BG, fg=WHITE,
                 font=("Consolas", 9)).grid(row=0, column=0, padx=2)
        self.var_from = tk.IntVar(value=1)
        tk.Spinbox(cf, from_=1, to=FLOORS, textvariable=self.var_from,
                   width=3, bg=PANEL_BG, fg=WHITE, buttonbackground=ACCENT,
                   font=("Consolas", 9)).grid(row=0, column=1, padx=2)

        tk.Label(cf, text="To:", bg=PANEL_BG, fg=WHITE,
                 font=("Consolas", 9)).grid(row=0, column=2, padx=2)
        self.var_to = tk.IntVar(value=5)
        tk.Spinbox(cf, from_=1, to=FLOORS, textvariable=self.var_to,
                   width=3, bg=PANEL_BG, fg=WHITE, buttonbackground=ACCENT,
                   font=("Consolas", 9)).grid(row=0, column=3, padx=2)

        tk.Button(cf, text="Call", bg=ACCENT, fg=WHITE,
                  font=("Consolas", 9, "bold"), activebackground=ACCENT2,
                  command=self._call_elevator).grid(row=0, column=4, padx=6)

        ttk.Separator(parent).pack(fill="x", padx=8, pady=5)

        # special buttons
        sp = tk.Frame(parent, bg=PANEL_BG)
        sp.pack(padx=8, pady=4)
        self.btn_hold = tk.Button(sp, text="HOLD\nDOOR", width=7, height=2,
                                  bg=GRAY, fg=WHITE,
                                  font=("Consolas", 8, "bold"),
                                  command=self._toggle_hold)
        self.btn_hold.grid(row=0, column=0, padx=4)
        self.btn_emg = tk.Button(sp, text="🚨 EMRG\nSTOP", width=7, height=2,
                                 bg=RED, fg=WHITE,
                                 font=("Consolas", 8, "bold"),
                                 command=self._emergency)
        self.btn_emg.grid(row=0, column=1, padx=4)

        # passenger manual counter
        pf = tk.Frame(parent, bg=PANEL_BG)
        pf.pack(padx=8, pady=5)
        tk.Label(pf, text="Manual Pax:", bg=PANEL_BG, fg=WHITE,
                 font=("Consolas", 9)).pack(side="left")
        tk.Button(pf, text="+", width=2, bg=GREEN, fg=WHITE,
                  font=("Consolas", 10, "bold"),
                  command=lambda: self._change_pax(+1)).pack(side="left", padx=2)
        tk.Button(pf, text="−", width=2, bg=RED, fg=WHITE,
                  font=("Consolas", 10, "bold"),
                  command=lambda: self._change_pax(-1)).pack(side="left", padx=2)

        # ETA
        ef = tk.Frame(parent, bg=PANEL_BG)
        ef.pack(fill="x", padx=8, pady=4)
        tk.Label(ef, text="ETA to queued floors:", bg=PANEL_BG, fg=GOLD,
                 font=("Consolas", 9)).pack(anchor="w")
        self.eta_text = tk.Text(ef, height=4, width=30,
                                bg=SHAFT_BG, fg=GREEN,
                                font=("Consolas", 8),
                                state="disabled", bd=0)
        self.eta_text.pack()

    def _slabel(self, parent, title, value):
        f = tk.Frame(parent, bg=PANEL_BG)
        f.pack(side="left", padx=6)
        tk.Label(f, text=title, bg=PANEL_BG, fg=GRAY,
                 font=("Consolas", 8)).pack()
        lbl = tk.Label(f, text=value, bg=PANEL_BG, fg=ACCENT2,
                       font=("Consolas", 10, "bold"))
        lbl.pack()
        return lbl

    def _build_log_panel(self, parent):
        tk.Label(parent, text="📋  EVENT LOG", bg=PANEL_BG, fg=ACCENT2,
                 font=("Consolas", 10, "bold")).pack(pady=(6, 2))
        frm = tk.Frame(parent, bg=PANEL_BG)
        frm.pack(padx=6, pady=(0, 6), fill="both")
        sb = tk.Scrollbar(frm)
        sb.pack(side="right", fill="y")
        self.log_box = tk.Text(frm, height=12, width=32,
                               bg=SHAFT_BG, fg=GREEN,
                               font=("Consolas", 8),
                               state="disabled", bd=0,
                               yscrollcommand=sb.set)
        self.log_box.pack(side="left")
        sb.config(command=self.log_box.yview)

    # ── ACTIONS ───────────────────────────

    def _inside_press(self, floor):
        if self.elev.emergency:
            return
        self.building.press_inside(floor)
        self.floor_btns[floor].config(bg=ACCENT)
        self._log(f"Inside button: Floor {floor}")

    def _call_elevator(self):
        if self.elev.emergency:
            return
        frm = self.var_from.get()
        to  = self.var_to.get()
        if frm == to:
            messagebox.showwarning("Invalid", "From and To must differ.")
            return
        self.building.call_elevator(frm, to)
        self._log(f"Call: Floor {frm} → {to}")

    def _toggle_hold(self):
        self.elev.hold_door = not self.elev.hold_door
        self.btn_hold.config(bg=GOLD if self.elev.hold_door else GRAY)
        self._log("Hold Door: " + ("ON" if self.elev.hold_door else "OFF"))

    def _emergency(self):
        self.elev.emergency = not self.elev.emergency
        if self.elev.emergency:
            self.elev.direction = "idle"
            self.elev.destinations.clear()
            self.ctrl.external_requests.clear()
            self.btn_emg.config(bg=GOLD, text="✅ RESUME")
            self._log("🚨 EMERGENCY STOP ACTIVATED")
            self._flash(6)
        else:
            self.btn_emg.config(bg=RED, text="🚨 EMRG\nSTOP")
            self._log("System resumed.")

    def _flash(self, n):
        if n > 0 and self.elev.emergency:
            cur = self.canvas["bg"]
            self.canvas.config(bg=RED if cur == BG else BG)
            self.root.after(120, lambda: self._flash(n - 1))
        else:
            self.canvas.config(bg=BG)

    def _change_pax(self, delta):
        if delta > 0:
            if len(self.elev.passengers) >= self.elev.capacity:
                self._log("⚠️ OVERLOAD! Capacity full.")
                messagebox.showwarning("Overload", "Elevator at full capacity!")
                return
            dummy = Person(9999, self.elev.current_floor, self.elev.current_floor)
            self.elev.passengers.append(dummy)
        else:
            if not self.elev.passengers:
                return
            self.elev.passengers.pop()
        self._log(f"Pax {'boarded' if delta > 0 else 'exited'} manually. "
                  f"Total: {len(self.elev.passengers)}")

    def _log(self, msg):
        ts    = datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] {msg}"
        self.log_entries.append(entry)
        self.log_box.config(state="normal")
        self.log_box.insert("end", entry + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    # ── SIMULATION LOOP ───────────────────

    def _sim_loop(self):
        DOOR_OPEN_SEC = 2.5

        while self.running:
            if self.elev.emergency:
                time.sleep(0.1)
                continue

            self.ctrl.decide_direction()
            nxt = self.ctrl.next_stop()

            if nxt is None:
                self.elev.direction = "idle"
                time.sleep(0.15)
                continue

            # ── travel floor by floor ──
            while self.elev.current_floor != nxt and not self.elev.emergency:
                step = 1 if nxt > self.elev.current_floor else -1
                dist = abs(nxt - self.elev.current_floor)
                delay_per_frame = (0.08 if dist > 1 else 0.16) / ANIM_STEPS

                start = float(self.elev.current_floor)
                for s in range(ANIM_STEPS):
                    if not self.running:
                        return
                    self.elev.position = start + step * (s / ANIM_STEPS)
                    time.sleep(delay_per_frame)

                self.elev.current_floor += step
                self.elev.position = float(self.elev.current_floor)

            if self.elev.emergency:
                continue

            # ── arrived ──
            floor_obj = self.building.floors[self.elev.current_floor - 1]
            self.ctrl.clear_external(self.elev.current_floor)

            arrived = self.elev.remove_arrived()
            if arrived:
                self._log(f"Floor {self.elev.current_floor}: "
                          f"{len(arrived)} exited.")

            boarded = floor_obj.board_passengers(self.elev.direction, self.elev)
            if boarded:
                self._log(f"Floor {self.elev.current_floor}: "
                          f"{len(boarded)} boarded.")

            self._log(f"Arrived → Floor {self.elev.current_floor} "
                      f"({self.elev.direction.upper()})")

            # ── open door ──
            self.elev.door_state = self.elev.DOOR_OPENING
            self._log("Door: opening…")
            for s in range(DOOR_STEPS + 1):
                self._door_ratio = s / DOOR_STEPS
                time.sleep(0.04)
            self.elev.door_state = self.elev.DOOR_OPEN
            self._door_ratio = 1.0
            self._log("Door: open")

            # wait
            elapsed = 0.0
            while elapsed < DOOR_OPEN_SEC or self.elev.hold_door:
                time.sleep(0.1)
                elapsed += 0.1
                if self.elev.emergency:
                    break

            # ── close door ──
            if not self.elev.emergency:
                self.elev.door_state = self.elev.DOOR_CLOSING
                self._log("Door: closing…")
                for s in range(DOOR_STEPS + 1):
                    self._door_ratio = 1.0 - s / DOOR_STEPS
                    time.sleep(0.04)
                self.elev.door_state = self.elev.DOOR_CLOSED
                self._door_ratio = 0.0
                self._log("Door: closed")

            # reset lit button
            f_done = self.elev.current_floor
            self.root.after(0, lambda f=f_done:
                            self.floor_btns[f].config(bg=PANEL_BG))

            self.ctrl.decide_direction()

    # ── ANIMATION LOOP ────────────────────

    def _anim_loop(self):
        if not self.running:
            return
        self._update_canvas()
        self._update_status()
        self._update_eta()
        self.root.after(33, self._anim_loop)

    def _update_canvas(self):
        c   = self.canvas
        pos = self.elev.position
        cy  = self._floor_cy(pos)
        cx  = SHAFT_X + 3
        w   = SHAFT_W - 6
        h   = FLOOR_H - 8

        x1, y1 = cx,     cy - h / 2
        x2, y2 = cx + w, cy + h / 2

        # cab body
        c.coords(self.cab_body, x1, y1, x2, y2)

        # direction arrow
        arrow_map = {"up": "▲", "down": "▼", "idle": "■"}
        c.itemconfig(self.cab_arrow,
                     text=arrow_map.get(self.elev.direction, "■"))
        c.coords(self.cab_arrow, cx + w / 2, cy)

        # doors
        half  = w / 2
        slide = half * self._door_ratio
        # left door
        c.coords(self.door_left,  x1, y1 + 2, x1 + half - slide, y2 - 2)
        # right door
        c.coords(self.door_right, x2 - half + slide, y1 + 2, x2, y2 - 2)

        # floor call arrows
        floors_data = self.building.floors
        for fl in floors_data:
            up_col = GOLD  if fl.button_up   else GRAY
            dn_col = GOLD  if fl.button_down else GRAY
            c.itemconfig(self.arrow_tags[f"up_{fl.number}"], fill=up_col)
            c.itemconfig(self.arrow_tags[f"dn_{fl.number}"], fill=dn_col)

        # raise cab and doors so they render on top
        c.tag_raise(self.cab_body)
        c.tag_raise(self.door_left)
        c.tag_raise(self.door_right)
        c.tag_raise(self.cab_arrow)

    def _update_status(self):
        e = self.elev
        self.lbl_floor.config(text=str(e.current_floor))
        self.lbl_dir.config(
            text=e.direction.upper(),
            fg=GREEN if e.direction == "up" else
               RED   if e.direction == "down" else GRAY)
        door_colors = {
            e.DOOR_CLOSED:  GRAY,
            e.DOOR_OPENING: GOLD,
            e.DOOR_OPEN:    GREEN,
            e.DOOR_CLOSING: GOLD,
        }
        self.lbl_door.config(
            text=e.door_state.upper(),
            fg=door_colors.get(e.door_state, WHITE))
        pax_col = RED if e.is_overloaded else WHITE
        self.lbl_pax.config(
            text=f"{len(e.passengers)}/{e.capacity}",
            fg=pax_col)

    def _update_eta(self):
        targets = self.ctrl.all_destinations()
        lines   = []
        cur     = self.elev.current_floor
        # estimate: ~2.5s per floor + 4s door
        for fl in sorted(targets):
            dist = abs(fl - cur)
            eta  = dist * 2.5 + 4
            lines.append(f"  Floor {fl:>2}  →  ~{eta:.0f}s")
        text = "\n".join(lines) if lines else "  No pending requests"
        self.eta_text.config(state="normal")
        self.eta_text.delete("1.0", "end")
        self.eta_text.insert("end", text)
        self.eta_text.config(state="disabled")

    def _on_close(self):
        self.running = False
        self.root.destroy()


# ─────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app  = ElevatorGUI(root)
    root.mainloop()
