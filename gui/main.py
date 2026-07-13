#!/usr/bin/env python3
"""
Sniffies Command Station — Multi-Agent Orchestration GUI
"""

import sys, os, asyncio, json, threading, time, subprocess
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox, font
except ImportError:
    tk = None

from swarm.controller import SwarmController
from swarm.config import SwarmConfig
from swarm.parser import parse_command

THEME = {
    "bg_dark": "#0F051E",
    "bg_medium": "#1A0A33",
    "bg_light": "#251147",
    "surface": "#2D1557",
    "purple": "#7832FF",
    "blue": "#3264FF",
    "cyan": "#00C8FF",
    "green": "#00FFB4",
    "accent": "#FF3278",
    "text_primary": "#FFFFFF",
    "text_secondary": "#B8A0D8",
    "text_dim": "#7A609A",
    "success": "#00FFB4",
    "error": "#FF3278",
    "warning": "#FFB432",
    "border": "#3D2070",
    "hover": "#3D2070",
    "input_bg": "#1A0A33",
}

FONT_FAMILY = "Segoe UI"


class AsyncExecutor:
    def __init__(self):
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def start(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    def submit(self, coro, callback=None):
        if not self._loop:
            self.start()
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        if callback:
            def done(f):
                try:
                    result = f.result()
                    callback(result)
                except Exception as e:
                    callback(e)
            fut.add_done_callback(done)
        return fut

    def stop(self):
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=5)


class StyleConfig:
    def __init__(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        colors = THEME

        self.style.configure(".", background=colors["bg_dark"], foreground=colors["text_primary"],
                             font=(FONT_FAMILY, 10))
        self.style.configure("TFrame", background=colors["bg_dark"])
        self.style.configure("TLabel", background=colors["bg_dark"], foreground=colors["text_primary"])
        self.style.configure("TButton", background=colors["purple"], foreground="white",
                             borderwidth=0, focusthickness=0, font=(FONT_FAMILY, 10, "bold"),
                             padding=(16, 8))
        self.style.map("TButton", background=[("active", colors["blue"]), ("disabled", colors["text_dim"])])
        self.style.configure("Success.TButton", background=colors["green"], foreground=colors["bg_dark"])
        self.style.map("Success.TButton", background=[("active", "#00DDA0")])
        self.style.configure("Danger.TButton", background=colors["accent"], foreground="white")
        self.style.map("Danger.TButton", background=[("active", "#E02D6A")])

        self.style.configure("TEntry", fieldbackground=colors["input_bg"], foreground=colors["text_primary"],
                             insertcolor=colors["cyan"], borderwidth=1, relief="solid",
                             font=(FONT_FAMILY, 11))
        self.style.configure("Header.TLabel", font=(FONT_FAMILY, 16, "bold"), foreground=colors["cyan"])
        self.style.configure("Title.TLabel", font=(FONT_FAMILY, 12, "bold"), foreground=colors["purple"])
        self.style.configure("Status.TLabel", font=(FONT_FAMILY, 9), foreground=colors["text_secondary"])
        self.style.configure("Success.TLabel", foreground=colors["success"])
        self.style.configure("Error.TLabel", foreground=colors["error"])
        self.style.configure("Accent.TLabel", foreground=colors["cyan"])

        self.style.configure("Console.TText", background=colors["bg_dark"], foreground=colors["text_primary"],
                             insertcolor=colors["cyan"], borderwidth=0, font=("Consolas", 10))
        self.style.configure("Sidebar.TFrame", background=colors["bg_medium"])
        self.style.configure("Card.TFrame", background=colors["surface"], borderwidth=0)
        self.style.layout("Card.TFrame", [("Card.TFrame.border", {"sticky": "nswe", "children":
            [("Card.TFrame.padding", {"sticky": "nswe"})]})])

        self.style.configure("Vertical.TScrollbar", background=colors["bg_light"],
                             troughcolor=colors["bg_dark"], bordercolor=colors["border"],
                             arrowcolor=colors["text_primary"],
                             gripcount=0, relief="flat", borderwidth=0)
        self.style.configure("Horizontal.TScale", background=colors["bg_dark"],
                             troughcolor=colors["bg_light"])


class SidebarButton(tk.Frame):
    def __init__(self, parent, text, icon="", command=None, active=False, **kwargs):
        super().__init__(parent, bg=THEME["surface"] if active else THEME["bg_medium"], cursor="hand2")
        self.command = command
        self.active = active
        self.configure_highlight()

        self.label = tk.Label(self, text=f" {icon} {text}", anchor="w",
                              font=(FONT_FAMILY, 10), bg=self["bg"],
                              fg=THEME["cyan"] if active else THEME["text_secondary"],
                              padx=12, pady=8)
        self.label.pack(fill="x")
        self.label.bind("<Button-1>", self._click)
        self.bind("<Button-1>", self._click)

    def configure_highlight(self):
        self.bind("<Enter>", lambda e: self._set_bg(THEME["hover"]))
        self.bind("<Leave>", lambda e: self._set_bg(THEME["surface"] if self.active else THEME["bg_medium"]))

    def _set_bg(self, color):
        self.config(bg=color)
        self.label.config(bg=color)

    def _click(self, e):
        if self.command:
            self.command()


class CommandStationApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sniffies Command Station")
        self.root.geometry("1280x760")
        self.root.minsize(960, 600)
        self.root.configure(bg=THEME["bg_dark"])

        icon_path = os.path.join(os.path.dirname(__file__), "assets", "sniffies.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        self.async_runner = AsyncExecutor()
        self.async_runner.start()
        self.controller = SwarmController(SwarmConfig())
        self.command_history = []
        self.history_index = -1
        self.running_swarm = False

        StyleConfig()
        self._build_ui()
        self._bind_keys()

        self._log("Sniffies Command Station initialized.")
        self._log("Type a command or click a quick action to begin.")
        self._log("")

    def _build_ui(self):
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()

    def _build_sidebar(self):
        side = tk.Frame(self.root, bg=THEME["bg_medium"], width=220)
        side.grid(row=0, column=0, sticky="nswe")
        side.grid_propagate(False)

        logo_frame = tk.Frame(side, bg=THEME["bg_medium"])
        logo_frame.pack(fill="x", pady=(16, 8))

        logo_img_path = os.path.join(os.path.dirname(__file__), "assets", "sniffies.png")
        self.logo_img = None
        if os.path.exists(logo_img_path):
            try:
                from PIL import Image, ImageTk
                pil_img = Image.open(logo_img_path).resize((40, 40), Image.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(pil_img)
                tk.Label(logo_frame, image=self.logo_img, bg=THEME["bg_medium"]).pack(side="left", padx=(12, 8))
            except Exception:
                pass

        tk.Label(logo_frame, text="COMMAND", font=(FONT_FAMILY, 14, "bold"),
                 fg=THEME["cyan"], bg=THEME["bg_medium"]).pack(side="left")
        tk.Label(logo_frame, text="STATION", font=(FONT_FAMILY, 14, "bold"),
                 fg=THEME["purple"], bg=THEME["bg_medium"]).pack(side="left")

        nav_frame = tk.Frame(side, bg=THEME["bg_medium"])
        nav_frame.pack(fill="x", pady=(16, 0))

        self.nav_buttons = []
        nav_items = [
            ("Console", "\u2328", self._show_console),
            ("Swarm", "\u26A1", self._show_swarm),
            ("Quick Actions", "\u2699", self._show_quick),
            ("Commands", "\uD83D\uDCCB", self._show_commands_view),
            ("History", "\u23F0", self._show_history),
            ("About", "\u2139", self._show_about),
        ]

        self.active_nav = 0
        for i, (text, icon, cmd) in enumerate(nav_items):
            btn = SidebarButton(nav_frame, text, icon, cmd, active=(i == 0))
            btn.pack(fill="x", padx=4, pady=1)
            self.nav_buttons.append(btn)

        tk.Frame(side, bg=THEME["bg_medium"]).pack(expand=True)

        status_frame = tk.Frame(side, bg=THEME["bg_medium"])
        status_frame.pack(fill="x", side="bottom", pady=8)

        self.status_indicator = tk.Canvas(status_frame, width=10, height=10,
                                          bg=THEME["bg_medium"], highlightthickness=0)
        self.status_indicator.pack(side="left", padx=(12, 4))
        self._dot = self.status_indicator.create_oval(1, 1, 9, 9, fill=THEME["green"], outline="")

        tk.Label(status_frame, text="Active", font=(FONT_FAMILY, 9),
                 fg=THEME["text_secondary"], bg=THEME["bg_medium"]).pack(side="left")

    def _build_main(self):
        self.main_container = tk.Frame(self.root, bg=THEME["bg_dark"])
        self.main_container.grid(row=0, column=1, sticky="nswe")
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.rowconfigure(0, weight=1)

        self.views = {}
        self._build_console_view()
        self._build_swarm_view()
        self._build_quick_view()
        self._build_commands_view()
        self._build_history_view()
        self._build_about_view()

        self._show_view("console")

    def _build_console_view(self):
        frame = tk.Frame(self.main_container, bg=THEME["bg_dark"])
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        tk.Label(frame, text="\u2328  Command Console",
                 font=(FONT_FAMILY, 16, "bold"), fg=THEME["cyan"],
                 bg=THEME["bg_dark"]).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 4))
        tk.Label(frame, text="Type  bots <N> <task>  to launch agents",
                 bg=THEME["bg_dark"], fg=THEME["text_secondary"]).grid(row=0, column=0, sticky="w", padx=16, pady=(36, 4))

        self.console = tk.Text(frame, bg=THEME["bg_dark"], fg=THEME["text_primary"],
                               insertbackground=THEME["cyan"], font=("Consolas", 10),
                               borderwidth=0, relief="flat", state="disabled",
                               wrap="word", padx=8, pady=8)
        self.console.grid(row=1, column=0, sticky="nswe", padx=8)
        console_scroll = tk.Scrollbar(frame, orient="vertical", command=self.console.yview,
                                      bg=THEME["bg_light"], troughcolor=THEME["bg_dark"])
        console_scroll.grid(row=1, column=1, sticky="ns")
        self.console.configure(yscrollcommand=console_scroll.set)

        input_frame = tk.Frame(frame, bg=THEME["bg_dark"])
        input_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 8))
        input_frame.columnconfigure(0, weight=1)

        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(input_frame, textvariable=self.input_var,
                                    bg=THEME["input_bg"], fg=THEME["text_primary"],
                                    insertbackground=THEME["cyan"],
                                    font=(FONT_FAMILY, 11), borderwidth=1,
                                    relief="solid", highlightthickness=0)
        self.input_entry.configure(highlightbackground=THEME["border"], highlightcolor=THEME["cyan"])
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8), ipady=6)
        self.input_entry.insert(0, "bots 5 test my signup flow")

        self.run_btn = tk.Button(input_frame, text="\u25B6 RUN", command=self._run_command,
                                 bg=THEME["purple"], fg="white", font=(FONT_FAMILY, 10, "bold"),
                                 borderwidth=0, padx=20, cursor="hand2", activebackground=THEME["blue"])
        self.run_btn.grid(row=0, column=1, sticky="e")

        self.views["console"] = frame

    def _build_swarm_view(self):
        frame = tk.Frame(self.main_container, bg=THEME["bg_dark"])
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        top = tk.Frame(frame, bg=THEME["bg_dark"])
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        tk.Label(top, text="\u26A1  Swarm Dashboard",
                 font=(FONT_FAMILY, 16, "bold"), fg=THEME["cyan"],
                 bg=THEME["bg_dark"]).pack(side="left")

        stats = tk.Frame(top, bg=THEME["bg_dark"])
        stats.pack(side="right")

        self.swarm_stats = {}
        for label in ["Total", "Success", "Failed", "Time"]:
            cell = tk.Frame(stats, bg=THEME["surface"], padx=16, pady=4)
            cell.pack(side="left", padx=4)
            tk.Label(cell, text=label, font=(FONT_FAMILY, 8),
                     fg=THEME["text_dim"], bg=THEME["surface"]).pack()
            val = tk.Label(cell, text="0", font=(FONT_FAMILY, 14, "bold"),
                           fg=THEME["cyan"], bg=THEME["surface"])
            val.pack()
            self.swarm_stats[label.lower()] = val

        canvas = tk.Canvas(frame, bg=THEME["bg_dark"], highlightthickness=0)
        canvas.grid(row=1, column=0, sticky="nswe", padx=8)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview,
                                 bg=THEME["bg_light"], troughcolor=THEME["bg_dark"])
        scrollbar.grid(row=1, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        self.swarm_container = tk.Frame(canvas, bg=THEME["bg_dark"])
        self.swarm_container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.swarm_container, anchor="nw", width=canvas.winfo_width())
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(1, width=e.width))

        self.views["swarm"] = frame

    def _build_quick_view(self):
        frame = tk.Frame(self.main_container, bg=THEME["bg_dark"])
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        tk.Label(frame, text="\u2699  Quick Actions",
                 font=(FONT_FAMILY, 16, "bold"), fg=THEME["cyan"],
                 bg=THEME["bg_dark"]).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 12))

        canvas = tk.Canvas(frame, bg=THEME["bg_dark"], highlightthickness=0)
        canvas.grid(row=1, column=0, sticky="nswe", padx=8)
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview,
                                 bg=THEME["bg_light"], troughcolor=THEME["bg_dark"])
        scrollbar.grid(row=1, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        inner = tk.Frame(canvas, bg=THEME["bg_dark"])
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw", width=canvas.winfo_width())
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(1, width=e.width))

        quick_actions = [
            ("Swarm Commands", [
                ("\u26A1 5 Bots - Test Login", "bots 5 test login flow"),
                ("\u26A1 10 Bots - Signup Test", "bots 10 test signup flow"),
                ("\u26A1 3 Bots - API Check", "bots 3 check if my API is responding"),
                ("\u26A1 20 Bots - Scrape Pages", "bots 20 scrape product pages"),
                ("\u26A1 8 Bots - Form Submit", "bots 8 fill and submit forms"),
            ]),
            ("Agency Commands", [
                ("\u25B6 Onboard Client", "onboard"),
                ("\uD83D\uDCCA Dashboard", "dashboard"),
                ("\uD83D\uDCCB List Teams", "list teams"),
                ("\uD83D\uDCCB List All Commands", "list commands"),
                ("\u2699\uFE0F Run All Teams", "run all teams"),
            ]),
            ("Marketing", [
                ("\uD83D\uDD0D SEO Audit", "run seo technical-audit"),
                ("\uD83D\uDCE7 Email Campaign", "run email campaign"),
                ("\uD83D\uDCAC Social Media Blitz", "workflow social-media-blitz"),
                ("\uD83D\uDCC8 Analytics Report", "run analytics report"),
                ("\uD83D\uDCE2 Google Ads", "run ads google"),
            ]),
            ("Sales & Strategy", [
                ("\uD83C\uDFAF Lead Generation", "workflow lead-generation"),
                ("\uD83D\uDCA1 SWOT Analysis", "run strategy swot"),
                ("\uD83D\uDCC4 Proposal Generator", "run sales proposal"),
                ("\uD83D\uDCC8 Sales Forecast", "run sales forecast"),
                ("\uD83D\uDEC0 Pipeline Report", "sales pipeline report"),
            ]),
            ("Research & Intelligence", [
                ("\uD83D\uDD0D Market Research", "run research market"),
                ("\uD83D\uDCA1 Trend Detection", "run intelligence trends"),
                ("\uD83D\uDCB0 Price Monitor", "run intelligence pricing"),
                ("\uD83D\uDCC4 Competitor Report", "workflow competitor-report"),
                ("\uD83C\uDF10 Industry Scan", "run research industry"),
            ]),
            ("Management", [
                ("\u2705 Quality Check", "qa"),
                ("\uD83D\uDCCA Progress Report", "run managing progress"),
                ("\uD83D\uDCCB Task Coordinator", "run managing tasks"),
                ("\uD83D\uDCC5 Content Calendar", "workflow content-month"),
                ("\uD83D\uDE80 Product Launch", "workflow product-launch"),
            ]),
        ]

        for section_name, actions in quick_actions:
            card = tk.Frame(inner, bg=THEME["surface"], padx=12, pady=6)
            card.pack(fill="x", padx=8, pady=3)
            tk.Label(card, text=section_name, font=(FONT_FAMILY, 11, "bold"),
                     fg=THEME["cyan"], bg=THEME["surface"]).pack(anchor="w", pady=(0, 4))

            for label_text, cmd in actions:
                btn_frame = tk.Frame(card, bg=THEME["surface"])
                btn_frame.pack(fill="x", pady=1)
                btn = tk.Button(btn_frame, text=label_text, anchor="w",
                                bg=THEME["bg_light"], fg=THEME["text_primary"],
                                font=(FONT_FAMILY, 9), borderwidth=0,
                                padx=8, pady=3, cursor="hand2",
                                activebackground=THEME["purple"],
                                command=lambda c=cmd: self._quick_run(c))
                btn.pack(fill="x")

        self.views["quick"] = frame

    def _build_commands_view(self):
        frame = tk.Frame(self.main_container, bg=THEME["bg_dark"])
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        top = tk.Frame(frame, bg=THEME["bg_dark"])
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))

        tk.Label(top, text="\U0001F4CB  Command Browser",
                 font=(FONT_FAMILY, 16, "bold"), fg=THEME["cyan"],
                 bg=THEME["bg_dark"]).pack(side="left")

        self.commands_container = tk.Frame(frame, bg=THEME["bg_dark"])
        self.commands_container.grid(row=1, column=0, sticky="nswe", padx=8, pady=4)
        self.commands_container.columnconfigure(0, weight=1)

        canvas = tk.Canvas(self.commands_container, bg=THEME["bg_dark"],
                           highlightthickness=0, borderwidth=0)
        scrollbar = tk.Scrollbar(self.commands_container, orient="vertical",
                                  command=canvas.yview, bg=THEME["bg_light"],
                                  troughcolor=THEME["bg_dark"])
        scrollable = tk.Frame(canvas, bg=THEME["bg_dark"])
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw", width=canvas.winfo_width())
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(1, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._load_commands_into(scrollable)
        self.views["commands"] = frame

    def _load_commands_into(self, parent):
        cmd_path = Path(__file__).parent.parent / "agents" / "command-station" / "COMMANDS.md"
        if not cmd_path.exists():
            tk.Label(parent, text="COMMANDS.md not found.", fg=THEME["error"],
                     bg=THEME["bg_dark"]).pack(pady=20)
            return

        text = cmd_path.read_text(encoding="utf-8")
        sections = {}
        current_cat = None
        current_lines = []

        for line in text.splitlines():
            if line.startswith("## ") and not line.startswith("### "):
                if current_cat and current_lines:
                    sections[current_cat] = current_lines
                current_cat = line.strip("# ").strip()
                current_lines = []
            elif current_cat:
                current_lines.append(line)
        if current_cat and current_lines:
            sections[current_cat] = current_lines

        total = sum(1 for _ in text.splitlines() if "| `" in _ and "|" in _)

        header_frame = tk.Frame(parent, bg=THEME["bg_dark"])
        header_frame.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(header_frame, text=f"{len(sections)} Categories, {total}+ Commands",
                 font=(FONT_FAMILY, 10), fg=THEME["text_secondary"],
                 bg=THEME["bg_dark"]).pack(side="left")

        self._category_widgets = []
        for cat_name, lines in sections.items():
            cat_frame = tk.Frame(parent, bg=THEME["bg_dark"])
            cat_frame.pack(fill="x", padx=8, pady=2)

            header = tk.Frame(cat_frame, bg=THEME["surface"], cursor="hand2")
            header.pack(fill="x")
            header.bind("<Button-1>", lambda e, f=cat_frame: self._toggle_category(f))

            arrow = tk.Label(header, text="\u25B6", font=(FONT_FAMILY, 10),
                             fg=THEME["cyan"], bg=THEME["surface"])
            arrow.pack(side="left", padx=(8, 4))
            arrow.bind("<Button-1>", lambda e, f=cat_frame: self._toggle_category(f))

            tk.Label(header, text=cat_name, font=(FONT_FAMILY, 10, "bold"),
                     fg=THEME["text_primary"], bg=THEME["surface"],
                     anchor="w").pack(side="left", fill="x", expand=True, padx=(0, 8))

            body = tk.Frame(cat_frame, bg=THEME["bg_medium"])
            cmds = self._parse_commands_from_lines(lines)
            for cmd_name, cmd_action in cmds[:30]:
                row = tk.Frame(body, bg=THEME["bg_medium"])
                row.pack(fill="x", padx=16, pady=1)
                tk.Label(row, text=cmd_name, font=(FONT_FAMILY, 9, "bold"),
                         fg=THEME["green"], bg=THEME["bg_medium"],
                         width=30, anchor="w").pack(side="left")
                tk.Label(row, text=cmd_action, font=(FONT_FAMILY, 9),
                         fg=THEME["text_secondary"], bg=THEME["bg_medium"],
                         anchor="w").pack(side="left", fill="x", expand=True)
            if len(cmds) > 30:
                tk.Label(body, text=f"... and {len(cmds)-30} more",
                         font=(FONT_FAMILY, 8), fg=THEME["text_dim"],
                         bg=THEME["bg_medium"]).pack(anchor="w", padx=16)

            body.pack(fill="x", expand=False)
            self._category_widgets.append(body)

    def _toggle_category(self, cat_frame):
        for w in cat_frame.winfo_children():
            if isinstance(w, tk.Frame) and w != cat_frame.winfo_children()[0]:
                if w.winfo_viewable():
                    w.pack_forget()
                else:
                    w.pack(fill="x", expand=False)
                break

    def _parse_commands_from_lines(self, lines):
        cmds = []
        for line in lines:
            if "| `" in line and "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    cmd = parts[1].strip("` ")
                    action = parts[2] if len(parts) > 2 else ""
                    if cmd and not cmd.startswith("Command"):
                        cmds.append((cmd, action))
        return cmds

    def _show_commands_view(self):
        self._show_view("commands")

    def _build_history_view(self):
        frame = tk.Frame(self.main_container, bg=THEME["bg_dark"])
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        top = tk.Frame(frame, bg=THEME["bg_dark"])
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))

        tk.Label(top, text="\u23F0  Command History",
                 font=(FONT_FAMILY, 16, "bold"), fg=THEME["cyan"],
                 bg=THEME["bg_dark"]).pack(side="left")
        tk.Button(top, text="Clear History", command=self._clear_history,
                  bg=THEME["accent"], fg="white", font=(FONT_FAMILY, 9),
                  borderwidth=0, padx=12, cursor="hand2").pack(side="right")

        self.history_text = tk.Text(frame, bg=THEME["bg_dark"], fg=THEME["text_secondary"],
                                    font=("Consolas", 10), borderwidth=0,
                                    relief="flat", state="disabled", wrap="word", padx=8, pady=8)
        self.history_text.grid(row=1, column=0, sticky="nswe", padx=8)
        hist_scroll = tk.Scrollbar(frame, orient="vertical", command=self.history_text.yview,
                                   bg=THEME["bg_light"], troughcolor=THEME["bg_dark"])
        hist_scroll.grid(row=1, column=1, sticky="ns")
        self.history_text.configure(yscrollcommand=hist_scroll.set)

        self.views["history"] = frame

    def _build_about_view(self):
        frame = tk.Frame(self.main_container, bg=THEME["bg_dark"])
        frame.columnconfigure(0, weight=1)

        tk.Label(frame, text="Sniffies Command Station v1.0",
                 font=(FONT_FAMILY, 20, "bold"), fg=THEME["cyan"],
                 bg=THEME["bg_dark"]).grid(row=0, column=0, pady=(40, 8))

        tk.Label(frame, text="Multi-Agent Task Orchestration System",
                 font=(FONT_FAMILY, 12), fg=THEME["text_secondary"],
                 bg=THEME["bg_dark"]).grid(row=1, column=0, pady=(0, 24))

        info = [
            ("Architecture", "Swarm Controller + Async Worker Agents + Task Decomposition"),
            ("Teams", "8 Teams - Marketing, Sales, Intelligence, Strategy, Research, Content, Direction, Managing"),
            ("Commands", "1,281+ commands across 44 categories + custom agent creation"),
            ("Engine", "asyncio-based parallel execution with retry logic and timeout handling"),
            ("Tools", "HTTP Client (httpx), Filesystem sandbox, LLM reasoning layer"),
            ("Safety", "Built-in permission checks, CAPTCHA/exploit blocklist, auth safeguards"),
        ]

        for label, value in info:
            row = tk.Frame(frame, bg=THEME["bg_dark"])
            row.grid(row=row.grid_size()[1] + 2, column=0, sticky="w", padx=40, pady=4)
            tk.Label(row, text=f"{label}:", font=(FONT_FAMILY, 10, "bold"),
                     fg=THEME["purple"], bg=THEME["bg_dark"], width=14, anchor="e").pack(side="left")
            tk.Label(row, text=value, font=(FONT_FAMILY, 10),
                     fg=THEME["text_secondary"], bg=THEME["bg_dark"]).pack(side="left", padx=(8, 0))

        tk.Label(frame, text="\nBuilt for controlled research environments.",
                 font=(FONT_FAMILY, 9), fg=THEME["text_dim"],
                 bg=THEME["bg_dark"]).grid(row=10, column=0, pady=(24, 0))

        self.views["about"] = frame

    def _bind_keys(self):
        self.input_entry.bind("<Return>", lambda e: self._run_command())
        self.input_entry.bind("<Up>", self._history_up)
        self.input_entry.bind("<Down>", self._history_down)

    def _history_up(self, e):
        if self.command_history:
            self.history_index = max(0, self.history_index - 1)
            self.input_var.set(self.command_history[self.history_index])
            self.input_entry.icursor(tk.END)

    def _history_down(self, e):
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.input_var.set(self.command_history[self.history_index])
        else:
            self.history_index = len(self.command_history)
            self.input_var.set("")

    def _show_view(self, name):
        for n, f in self.views.items():
            f.grid_remove() if n != name else f.grid()
        for i, btn in enumerate(self.nav_buttons):
            keys = ["console", "swarm", "quick", "commands", "history", "about"]
            active = (keys[i] == name) if i < len(keys) else False
            btn.configure(bg=THEME["bg_medium"] if not active else THEME["purple"])

    def _show_console(self):
        self._show_view("console")

    def _show_swarm(self):
        self._show_view("swarm")

    def _show_quick(self):
        self._show_view("quick")

    def _show_history(self):
        self._show_view("history")
        self._refresh_history()

    def _show_about(self):
        self._show_view("about")

    def _log(self, msg: str, color: str | None = None):
        self.console.configure(state="normal")
        self.console.insert("end", msg + "\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    def _log_colored(self, msg: str, tag: str):
        self.console.configure(state="normal")
        self.console.insert("end", msg + "\n", tag)
        self.console.see("end")
        self.console.configure(state="disabled")

    def _run_command(self):
        cmd = self.input_var.get().strip()
        if not cmd:
            return
        self.command_history.append(cmd)
        self.history_index = len(self.command_history)
        self._log(f"> {cmd}")
        self.input_var.set("")

        if cmd.lower() == "exit":
            self.root.quit()
            return

        if cmd.lower() == "clear":
            self.console.configure(state="normal")
            self.console.delete("1.0", "end")
            self.console.configure(state="disabled")
            return

        if cmd.lower().startswith("bots ") or cmd.lower().startswith("bot "):
            self._run_swarm(cmd)
            return

        self._handle_local_command(cmd)

    def _handle_local_command(self, cmd: str):
        c = cmd.lower().strip()

        if c == "list commands":
            self._show_commands()
        elif c == "list teams":
            self._log("[INFO] 8 Teams: Marketing (60), Sales (10), Intelligence (10),"
                      " Strategy (7), Content (10), Research (8), Direction (4), Managing (4)")
            self._log("  Type 'list commands' for full command list.")
        elif c == "history":
            self._show_view("history")
        elif c in ("help", "?"):
            self._log("Commands: bots N <task> | list commands | list teams | history | clear | exit")
            self._log("  Examples: bots 5 health check https://example.com")
            self._log("  Examples: bots 10 ssl check https://example.com")
        elif c == "onboard":
            self._log("[INFO] Onboarding — run 'python onboarding/onboard.md' or use the AI agency in puppet mode.")
        elif c == "dashboard":
            self._log("[INFO] Dashboard — view the agency dashboard at vault/00-Dashboard/")
            self._log("  In puppet mode, type 'dashboard' to the AI agency.")
        elif c.startswith("run ") or c.startswith("workflow "):
            self._log(f"[INFO] '{cmd}' is an AI agency command. Enter puppet mode with 'puppet start', then type it.")
            self._log("  Or run 'bots N <task>' for swarm execution.")
        elif c == "puppet start":
            self._log("[INFO] Puppet mode is for AI agency interaction. Type 'puppet start' to the AI in CLAUDE.md.")
        elif c == "clear":
            self.console.configure(state="normal")
            self.console.delete("1.0", "end")
            self.console.configure(state="disabled")
        else:
            self._log(f"[Local] Unknown command: {cmd}")
            self._log("  Commands: bots N <task> | list commands | list teams | history | help | clear | exit")

    def _show_commands(self):
        cmd_path = Path(__file__).parent.parent / "agents" / "command-station" / "COMMANDS.md"
        if not cmd_path.exists():
            self._log("[ERROR] COMMANDS.md not found.")
            return
        text = cmd_path.read_text(encoding="utf-8")
        categories = []
        for line in text.splitlines():
            if line.startswith("## "):
                cat = line.strip("# ").strip()
                if cat and cat not in ("How To Use",):
                    categories.append(cat)
        self._log(f"[COMMANDS] 1,281+ commands across {len(categories)} categories:")
        for cat in categories:
            self._log(f"  - {cat}")
        self._log("  See agents/command-station/COMMANDS.md for full details.")

    def _run_swarm(self, cmd: str):
        if self.running_swarm:
            self._log("[WARN] A swarm is already running. Wait for it to finish.")
            return

        self.running_swarm = True
        self.run_btn.configure(state="disabled", text="\u23F3 BUSY")

        def callback(result):
            self.root.after(0, self._swarm_done, result, cmd)

        self.async_runner.submit(
            self.controller.run(cmd),
            callback,
        )

    def _swarm_done(self, result, cmd: str):
        self.running_swarm = False
        self.run_btn.configure(state="normal", text="\u25B6 RUN")

        if isinstance(result, Exception):
            self._log(f"[ERROR] {result}")
            return

        self._log(f"[DONE] {result.summary}")
        self._update_swarm_dashboard(result)

    def _update_swarm_dashboard(self, report):
        labels_map = {"total": "total_agents", "success": "success_count",
                      "failed": "failed_count", "time": "total_time_ms"}
        for key, attr in labels_map.items():
            val = getattr(report, attr, 0)
            if key == "time":
                val = f"{val}ms"
            lbl = self.swarm_stats.get(key)
            if lbl:
                lbl.configure(text=str(val))

        for w in self.swarm_container.winfo_children():
            w.destroy()

        if not report.agent_results:
            tk.Label(self.swarm_container, text="No agent data yet.",
                     fg=THEME["text_dim"], bg=THEME["bg_dark"]).pack(pady=20)
            return

        for r in report.agent_results:
            card = tk.Frame(self.swarm_container, bg=THEME["surface"], padx=12, pady=6)
            card.pack(fill="x", padx=8, pady=2)

            status_color = THEME["success"] if r.status.value == "success" else THEME["error"]

            row1 = tk.Frame(card, bg=THEME["surface"])
            row1.pack(fill="x")
            tk.Label(row1, text=f"Agent {r.agent_id}", font=(FONT_FAMILY, 10, "bold"),
                     fg=THEME["cyan"], bg=THEME["surface"]).pack(side="left")
            tk.Label(row1, text=r.status.value.upper(), font=(FONT_FAMILY, 9, "bold"),
                     fg=status_color, bg=THEME["surface"]).pack(side="right")
            tk.Label(row1, text=f"{r.duration_ms}ms", font=(FONT_FAMILY, 9),
                     fg=THEME["text_dim"], bg=THEME["surface"]).pack(side="right", padx=(0, 8))

            if r.result:
                row2 = tk.Frame(card, bg=THEME["surface"])
                row2.pack(fill="x", pady=(2, 0))
                tk.Label(row2, text=r.result[:120], font=(FONT_FAMILY, 9),
                         fg=THEME["text_secondary"], bg=THEME["surface"],
                         wraplength=700, justify="left").pack(anchor="w")

            if r.errors:
                row3 = tk.Frame(card, bg=THEME["surface"])
                row3.pack(fill="x")
                for err in r.errors[:2]:
                    tk.Label(row3, text=f"\u26A0 {err}", font=(FONT_FAMILY, 8),
                             fg=THEME["error"], bg=THEME["surface"]).pack(anchor="w")

    def _quick_run(self, cmd: str):
        self._show_console()
        self.input_var.set(cmd)
        self._run_command()

    def _refresh_history(self):
        self.history_text.configure(state="normal")
        self.history_text.delete("1.0", "end")
        if not self.command_history:
            self.history_text.insert("end", "No commands executed yet.")
        else:
            for i, cmd in enumerate(self.command_history, 1):
                ts = datetime.now().strftime("%H:%M:%S")
                self.history_text.insert("end", f"  {i:3d}. [{ts}] {cmd}\n")
        self.history_text.configure(state="disabled")

    def _clear_history(self):
        self.command_history.clear()
        self.history_index = -1
        self._refresh_history()

    def run(self):
        self.root.mainloop()

    def stop(self):
        self.async_runner.stop()
        self.root.destroy()


def main():
    app = CommandStationApp()
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.stop()


if __name__ == "__main__":
    main()
