import tkinter as tk

class DisplayWidget:
    def __init__(self, master):
        self.master = master

        self.master.overrideredirect(True)

        # Keep the window always on top
        self.master.attributes('-topmost', True)

        # Use a dark background color for the root window
        self.master.configure(bg="#2C2C2C")

        # Position the window at bottom-right corner
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        window_width, window_height = 100, 80
        x = screen_width - window_width - 10
        y = screen_height - window_height - 50
        self.master.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Create the canvas for the status light
        self.canvas = tk.Canvas(
            master, 
            width=30, 
            height=30, 
            highlightthickness=0,
            bg="#2C2C2C"  # dark gray background
        )
        self.canvas.pack(side=tk.LEFT, padx=2, pady=5)

        # Create the circle (initially red)
        self.circle_id = self.canvas.create_oval(5, 5, 24, 24, fill="red", outline="")

        # Track running state
        self.is_running = False

        # Create the toggle button with a slightly larger font and custom styling
        self.toggle_btn = tk.Button(
            master,
            text="Run",
            command=self.toggle_state,
            font=("Helvetica", 10, "bold"),
            bg="#444444",       # dark gray background
            fg="white",         # white text
            relief="flat",
            borderwidth=0,
            highlightthickness=0
        )
        self.toggle_btn.pack(side=tk.LEFT, padx=2, pady=2, ipadx=10, ipady=5)

        # Allow the user to move this borderless window
        self.master.bind("<ButtonPress-1>", self.start_move)
        self.master.bind("<B1-Motion>", self.do_move)

    def toggle_state(self):
        """Toggle between running (green circle, 'Stop' button) and not running (red circle, 'Run' button)."""
        self.is_running = not self.is_running
        if self.is_running:
            self.canvas.itemconfig(self.circle_id, fill="green")
            self.toggle_btn.config(text="Stop")
        else:
            self.canvas.itemconfig(self.circle_id, fill="red")
            self.toggle_btn.config(text="Run")

    # --- Methods for dragging a borderless window ---
    def start_move(self, event):
        self._x = event.x
        self._y = event.y

    def do_move(self, event):
        dx = event.x - self._x
        dy = event.y - self._y
        x0 = self.master.winfo_x() + dx
        y0 = self.master.winfo_y() + dy
        self.master.geometry(f"+{x0}+{y0}")

def run_app():
    root = tk.Tk()
    app = DisplayWidget(root)
    root.mainloop()

if __name__ == "__main__":
    run_app()
