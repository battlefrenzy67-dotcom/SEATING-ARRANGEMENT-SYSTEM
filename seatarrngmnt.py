import math
import tkinter as tk
from tkinter import messagebox, ttk


def parse_students(raw_text: str) -> list[dict]:
    """Parse lines formatted as 'RollNumber, Subject'."""
    students = []
    for line_no, raw_line in enumerate(raw_text.strip().splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2 or not parts[0] or not parts[1]:
            raise ValueError(
                f"Line {line_no}: expected 'RollNumber, Subject', got '{raw_line}'"
            )
        students.append({"roll": parts[0], "subject": parts[1]})
    return students


def arrange_seating(
    students: list[dict],
    num_rooms: int,
    rows: int,
    cols: int,
    avoid_same_subject_adjacent: bool = True,
) -> tuple[list[list[list[dict | None]]], list[dict]]:
    """
    Assign students to rooms (rows x cols), attempting to avoid placing
    students with the same subject directly next to each other horizontally.
    Returns (rooms_grid, unassigned_students).
    """
    capacity_per_room = rows * cols
    total_capacity = num_rooms * capacity_per_room

    rooms: list[list[list[dict | None]]] = [
        [[None for _ in range(cols)] for _ in range(rows)]
        for _ in range(num_rooms)
    ]

    if not students:
        return rooms, []

    # Group students by subject and interleave (round-robin) so same-subject
    # students are spread out naturally.
    by_subject: dict[str, list[dict]] = {}
    for s in students:
        by_subject.setdefault(s["subject"], []).append(s)

    queues = [list(group) for group in by_subject.values()]
    ordered_students: list[dict] = []
    while any(queues):
        for q in queues:
            if q:
                ordered_students.append(q.pop(0))

    remaining = list(ordered_students)
    unassigned: list[dict] = []

    for r_idx in range(num_rooms):
        for row in range(rows):
            for col in range(cols):
                if not remaining:
                    break

                left_student = rooms[r_idx][row][col - 1] if col > 0 else None
                forbidden_subject = (
                    left_student["subject"]
                    if (avoid_same_subject_adjacent and left_student is not None)
                    else None
                )

                chosen_idx = None
                if forbidden_subject is not None:
                    for idx, candidate in enumerate(remaining):
                        if candidate["subject"] != forbidden_subject:
                            chosen_idx = idx
                            break

                # Fallback if all remaining students share the forbidden subject
                if chosen_idx is None:
                    chosen_idx = 0

                rooms[r_idx][row][col] = remaining.pop(chosen_idx)

    if total_capacity < len(ordered_students):
        unassigned = remaining

    return rooms, unassigned


class SeatingOutputWindow(tk.Toplevel):
    """Separate window that displays the generated seating arrangement."""

    def __init__(
        self,
        parent: tk.Tk,
        rooms: list[list[list[dict | None]]],
        unassigned: list[dict],
        rows: int,
        cols: int,
    ):
        super().__init__(parent)
        self.title("Examination Seating Arrangement - Output")
        self.geometry("820x560")
        self.minsize(640, 420)

        total_assigned = sum(
            1
            for room in rooms
            for row in room
            for seat in row
            if seat is not None
        )
        total_seats = len(rooms) * rows * cols

        summary_text = (
            f"Rooms: {len(rooms)}  |  Grid per Room: {rows}x{cols}  |  "
            f"Seated: {total_assigned}/{total_seats}  |  "
            f"Unassigned: {len(unassigned)}"
        )

        header = ttk.Frame(self, padding=(12, 10))
        header.pack(fill=tk.X)
        ttk.Label(
            header,
            text="Seating Chart Output",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(header, text=summary_text, font=("Segoe UI", 10)).pack(
            anchor=tk.W, pady=(2, 0)
        )

        if unassigned:
            warn_rolls = ", ".join(s["roll"] for s in unassigned)
            ttk.Label(
                header,
                text=f"Warning - Insufficient capacity for: {warn_rolls}",
                foreground="#b00020",
                font=("Segoe UI", 9, "bold"),
            ).pack(anchor=tk.W, pady=(4, 0))

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        for r_idx, room in enumerate(rooms, start=1):
            tab = ttk.Frame(notebook, padding=10)
            notebook.add(tab, text=f"Room {r_idx}")

            canvas = tk.Canvas(tab, highlightthickness=0)
            v_scroll = ttk.Scrollbar(
                tab, orient=tk.VERTICAL, command=canvas.yview
            )
            h_scroll = ttk.Scrollbar(
                tab, orient=tk.HORIZONTAL, command=canvas.xview
            )
            grid_frame = ttk.Frame(canvas)

            grid_frame.bind(
                "<Configure>",
                lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")),
            )
            canvas.create_window((0, 0), window=grid_frame, anchor="nw")
            canvas.configure(
                yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set
            )

            v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            ttk.Label(
                grid_frame,
                text="[ FRONT / INVIGILATOR DESK ]",
                font=("Segoe UI", 9, "bold"),
            ).grid(row=0, column=0, columnspan=cols, pady=(0, 10))

            for r in range(rows):
                for c in range(cols):
                    seat = room[r][c]
                    seat_label = f"R{r + 1}-C{c + 1}"
                    if seat is not None:
                        text = (
                            f"{seat_label}\n"
                            f"Roll: {seat['roll']}\n"
                            f"Sub: {seat['subject']}"
                        )
                        bg = "#eef6ff"
                        fg = "#111827"
                    else:
                        text = f"{seat_label}\n[EMPTY]"
                        bg = "#f3f4f6"
                        fg = "#6b7280"

                    cell = tk.Label(
                        grid_frame,
                        text=text,
                        bg=bg,
                        fg=fg,
                        relief=tk.SOLID,
                        borderwidth=1,
                        width=18,
                        height=4,
                        font=("Segoe UI", 9),
                        padx=6,
                        pady=4,
                    )
                    cell.grid(row=r + 1, column=c, padx=5, pady=5, sticky="nsew")


class SeatingSystemApp(tk.Tk):
    """Main input window that launches the seating output in a new window."""

    DEFAULT_STUDENTS = "\n".join(
        [
            "CS101, Math",
            "CS102, Math",
            "CS103, Math",
            "CS104, Math",
            "EC101, Physics",
            "EC102, Physics",
            "EC103, Physics",
            "EC104, Physics",
            "ME101, Chemistry",
            "ME102, Chemistry",
            "ME103, Chemistry",
            "ME104, Chemistry",
            "CS105, Math",
            "EC105, Physics",
            "ME105, Chemistry",
            "CS106, Math",
        ]
    )

    def __init__(self):
        super().__init__()
        self.title("Examination Seating Arrangement System")
        self.geometry("620x520")
        self.minsize(520, 440)

        container = ttk.Frame(self, padding=14)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            container,
            text="Examination Seating Arrangement System",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            container,
            text="Enter one student per line as: RollNumber, Subject",
            font=("Segoe UI", 9),
        ).pack(anchor=tk.W, pady=(2, 10))

        # Room & grid configuration
        config_frame = ttk.LabelFrame(
            container, text="Room Configuration", padding=10
        )
        config_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(config_frame, text="Rooms:").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 4)
        )
        self.rooms_var = tk.StringVar(value="2")
        ttk.Entry(config_frame, textvariable=self.rooms_var, width=6).grid(
            row=0, column=1, padx=(0, 14)
        )

        ttk.Label(config_frame, text="Rows:").grid(
            row=0, column=2, sticky=tk.W, padx=(0, 4)
        )
        self.rows_var = tk.StringVar(value="3")
        ttk.Entry(config_frame, textvariable=self.rows_var, width=6).grid(
            row=0, column=3, padx=(0, 14)
        )

        ttk.Label(config_frame, text="Columns:").grid(
            row=0, column=4, sticky=tk.W, padx=(0, 4)
        )
        self.cols_var = tk.StringVar(value="3")
        ttk.Entry(config_frame, textvariable=self.cols_var, width=6).grid(
            row=0, column=5, padx=(0, 14)
        )

        self.auto_rooms_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            config_frame,
            text="Auto-adjust rooms to fit all students",
            variable=self.auto_rooms_var,
        ).grid(row=1, column=0, columnspan=6, sticky=tk.W, pady=(8, 0))

        self.avoid_adj_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            config_frame,
            text="Avoid placing same subject in adjacent seats",
            variable=self.avoid_adj_var,
        ).grid(row=2, column=0, columnspan=6, sticky=tk.W, pady=(4, 0))

        # Student input box
        ttk.Label(
            container, text="Students (Roll Number, Subject):", font=("Segoe UI", 10, "bold")
        ).pack(anchor=tk.W)

        text_frame = ttk.Frame(container)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 12))

        self.student_text = tk.Text(text_frame, height=12, font=("Consolas", 10))
        scroll = ttk.Scrollbar(
            text_frame, orient=tk.VERTICAL, command=self.student_text.yview
        )
        self.student_text.configure(yscrollcommand=scroll.set)
        self.student_text.insert("1.0", self.DEFAULT_STUDENTS)

        self.student_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Action buttons
        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill=tk.X)

        ttk.Button(
            btn_frame,
            text="Generate Seating Plan (New Window)",
            command=self.open_seating_window,
        ).pack(side=tk.RIGHT)

        ttk.Button(
            btn_frame,
            text="Clear",
            command=lambda: self.student_text.delete("1.0", tk.END),
        ).pack(side=tk.LEFT)

    def open_seating_window(self) -> None:
        try:
            students = parse_students(self.student_text.get("1.0", tk.END))
            rows = int(self.rows_var.get().strip())
            cols = int(self.cols_var.get().strip())
            rooms_input = int(self.rooms_var.get().strip())

            if rows <= 0 or cols <= 0 or rooms_input <= 0:
                raise ValueError("Rooms, rows, and columns must be positive integers.")

            if self.auto_rooms_var.get() and students:
                needed_rooms = math.ceil(len(students) / (rows * cols))
                num_rooms = max(rooms_input, needed_rooms)
            else:
                num_rooms = rooms_input

            rooms, unassigned = arrange_seating(
                students=students,
                num_rooms=num_rooms,
                rows=rows,
                cols=cols,
                avoid_same_subject_adjacent=self.avoid_adj_var.get(),
            )

            output_win = SeatingOutputWindow(
                parent=self,
                rooms=rooms,
                unassigned=unassigned,
                rows=rows,
                cols=cols,
            )
            output_win.focus_set()

        except ValueError as exc:
            messagebox.showerror("Invalid Input", str(exc))


if __name__ == "__main__":
    app = SeatingSystemApp()
    app.mainloop()