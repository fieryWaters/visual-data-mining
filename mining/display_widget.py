import tkinter as tk

class DisplayWidget:
    def __init__(self, master):
        self.master = master
        self.master.title("Display Widget")
        self.master.overrideredirect(True)

        self.master.attributes('-topmost', True)

        # Dark background color for the root window
        self.master.configure(bg="#2C2C2C")

        # Position the window at bottom-right corner
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        window_width, window_height = 50, 50
        x = screen_width - window_width - 10
        y = screen_height - window_height - 50
        self.master.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Track states
        self.is_running = False
        self.is_loading = False

        # Create a canvas to hold the circle
        self.canvas = tk.Canvas(
            master, 
            width=40, 
            height=40, 
            highlightthickness=0, 
            bd=0, 
            bg="#2C2C2C"
        )
        self.canvas.pack(expand=True, fill="both")

        # Draw the circle (initially red)
        self.circle_id = self.canvas.create_oval(5, 5, 40, 40, fill="red", outline="")

        # Bind a mouse click on the canvas to toggle the state
        self.canvas.bind("<Button-1>", self.toggle_state)

        # Make the window draggable (since it has no border)
        self.master.bind("<ButtonPress-1>", self.start_move)
        self.master.bind("<B1-Motion>", self.do_move)

    def toggle_state(self, event=None):
        """
        Toggle between running (green circle) and not running (red circle).
        If we are in a "loading" state, revert back to normal states 
        if the user clicks again.
        """
        # If we were loading, exit the loading state first.
        if self.is_loading:
            self.is_loading = False

        self.is_running = not self.is_running
        new_color = "green" if self.is_running else "red"
        self.canvas.itemconfig(self.circle_id, fill=new_color)

    def set_loading_state(self):
        """
        Force the circle to appear blue to indicate a 'loading' or 'pending' state.
        This does not toggle self.is_running, but sets a separate flag 'is_loading'.
        """
        self.is_loading = True
        self.canvas.itemconfig(self.circle_id, fill="blue")

    def start_move(self, event):
        """Remember the click position so we can move the window."""
        self._x = event.x
        self._y = event.y

    def do_move(self, event):
        """Reposition the window based on mouse movement."""
        dx = event.x - self._x
        dy = event.y - self._y
        x0 = self.master.winfo_x() + dx
        y0 = self.master.winfo_y() + dy
        self.master.geometry(f"+{x0}+{y0}")


def run_app():
    root = tk.Tk()
    app = DisplayWidget(root)

    # Create a second window with a dark theme
    sync_window = tk.Toplevel(root)
    sync_window.title("Sync Window")
    sync_window.configure(bg="#2C2C2C")
    sync_window.geometry("300x150+100+100")

    for col in range(4):
        sync_window.columnconfigure(col, weight=1)
    for row in range(2):
        sync_window.rowconfigure(row, weight=1)

    # Create the "Sync" button (occupies the entire top row)
    sync_button = tk.Button(
        sync_window, 
        text="Sync", 
        font=("Helvetica", 12, "bold"),
        fg="white",
        bg="#444444",
        relief="flat"
    )
    sync_button.grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")

    # Create four smaller buttons in row=1, columns=0..3
    for col in range(4):
        btn_text = f"Button {col+1}"
        btn = tk.Button(
            sync_window, 
            text=btn_text, 
            font=("Helvetica", 10),
            fg="white",
            bg="#666666",
            relief="flat"
        )
        btn.grid(row=1, column=col, padx=5, pady=5, sticky="nsew")
        

    root.mainloop()

if __name__ == "__main__":
    run_app()
