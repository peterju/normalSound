import configparser
import os
import re
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, font, messagebox

import ttkbootstrap as ttk
from tkinterdnd2 import DND_FILES, TkinterDnD

CONFIG_FILE = 'config.ini'


def load_config() -> configparser.ConfigParser:
    """
    讀取設定檔，如果不存在則建立預設設定。

    傳回:
        configparser.ConfigParser: 包含設定訊息的物件。
    """
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    else:
        config['DEFAULT'] = {'output_dir': os.path.join(os.path.expanduser("~"), "Music")}
    return config


def save_config(config: configparser.ConfigParser) -> None:
    """
    保存設定到設定檔。

    參數:
        config (configparser.ConfigParser): 要保存的設定物件。
    """
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)


def normalize_audio(
    input_files: list, output_dir: str, ffmpeg_path: str, target_lufs: float, progress_var: tk.DoubleVar
) -> None:
    """
    正規化音檔的響度並轉換為 MP3 格式，同時更新進度條。

    參數:
        input_files (list): 要處理的音檔列表。
        output_dir (str): 輸出目錄路徑。
        ffmpeg_path (str): FFmpeg 執行檔的路徑。
        target_lufs (float): 目標 LUFS 值。
        progress_var (tk.DoubleVar): 用於更新進度條的變數。
    """
    total_files = len(input_files)
    for i, input_file in enumerate(input_files):
        try:
            output_file = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(input_file))[0]}.mp3")
            command = [
                ffmpeg_path,
                '-y',
                '-i',
                input_file,
                '-af',
                f'loudnorm=I={target_lufs}:TP=-1:LRA=11',
                '-acodec',
                'libmp3lame',
                output_file,
            ]

            process = subprocess.Popen(command, stderr=subprocess.PIPE, universal_newlines=True)

            duration = None
            for line in process.stderr:
                duration_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})", line)
                if duration_match and not duration:
                    duration = (
                        float(duration_match.group(1)) * 3600
                        + float(duration_match.group(2)) * 60
                        + float(duration_match.group(3))
                    )

                time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})", line)
                if time_match and duration:
                    current_time = (
                        float(time_match.group(1)) * 3600 + float(time_match.group(2)) * 60 + float(time_match.group(3))
                    )
                    progress = (current_time / duration) * (1 / total_files) + (i / total_files)
                    progress_var.set(progress)

            process.wait()

            if os.path.exists(output_file):
                print(f'成功建立: {output_file}')
            else:
                print(f'錯誤: 無法建立 {output_file}')
        except subprocess.CalledProcessError as e:
            print(f'處理 {input_file} 時出錯: {e}')

    progress_var.set(1.0)  # 設置進度為 100%


def select_files() -> None:
    """打開檔案選擇對話框，讓使用者選擇要處理的音檔。"""
    filetypes = [("音檔", "*.m4a *.aac *.wav *.mp3 *.ogg"), ("所有檔案", "*.*")]
    input_dir = os.path.join(os.getcwd(), "input")
    if not os.path.exists(input_dir):
        os.makedirs(input_dir)
    files = filedialog.askopenfilenames(title="選擇音檔", filetypes=filetypes, initialdir=input_dir)
    if files:
        files_text.delete('1.0', tk.END)
        for file in files:
            files_text.insert(tk.END, f"{file}\n")


def select_output_dir() -> None:
    """打開目錄選擇對話框，讓使用者選擇輸出目錄。"""
    dir_path = filedialog.askdirectory(title="選擇輸出目錄", initialdir=output_dir_entry.get())
    if dir_path:
        output_dir_entry.delete(0, tk.END)
        output_dir_entry.insert(0, dir_path)
        config['DEFAULT']['output_dir'] = dir_path
        save_config(config)


def start_processing() -> None:
    """開始處理選定的音檔，並將輸出保存到指定的輸出目錄。"""
    files = files_text.get('1.0', tk.END).strip().split('\n')
    if not files or files == [""]:
        messagebox.showwarning("未選擇檔案", "請選擇要處理的音檔。")
        return

    output_dir = output_dir_entry.get()
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    ffmpeg_path = os.path.join('ffmpeg', 'ffmpeg.exe')
    target_lufs = float(target_lufs_spinbox.get())

    progress_var.set(0)  # 重置進度條

    def process_thread() -> None:
        normalize_audio(files, output_dir, ffmpeg_path, target_lufs, progress_var)
        form.after(0, process_complete)

    def process_complete() -> None:
        messagebox.showinfo("處理完成", f"音檔已處理並保存到 {output_dir}。")
        os.startfile(output_dir)  # 開啟輸出資料夾
        progress_var.set(0)  # 重置進度條

    threading.Thread(target=process_thread, daemon=True).start()


def drop(event: tk.Event) -> None:
    """
    處理拖放事件，將拖放的音檔添加到文字框中。

    參數:
        event (tk.Event): 拖放事件物件。
    """
    files = event.data.split()
    for file in files:
        if file.lower().endswith(('.m4a', '.aac', '.wav', '.mp3', '.ogg')):
            files_text.insert(tk.END, f"{file}\n")


# 載入設定
config = load_config()

# 建立主窗口
form = TkinterDnD.Tk()
form.title("音量一致化工具")
form.geometry("500x340")

# 使用 ttkbootstrap 設定樣式
style = ttk.Style("litera")  # 使用 litera 主題，其他主題可以更換

# 設置全局字體
default_font = font.nametofont("TkDefaultFont")
default_font.configure(size=default_font.cget("size") + 2)
form.option_add("*Font", default_font)

# 建立主框架
frame = ttk.Frame(form, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
form.columnconfigure(0, weight=1)
form.rowconfigure(0, weight=1)

# 檔案選擇區域
label_files = ttk.Label(frame, text="選擇的音檔:")
label_files.grid(row=0, column=0, sticky=tk.W, pady=5)

files_frame = ttk.Frame(frame)
files_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
files_frame.columnconfigure(0, weight=1)
files_frame.rowconfigure(0, weight=1)

files_text = tk.Text(files_frame, height=10, width=50)
files_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=files_text.yview)
scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
files_text['yscrollcommand'] = scrollbar.set

# 瀏覽按鈕與 LUFS 設置區域
label_lufs = ttk.Label(frame, text="目標 LUFS：")
label_lufs.grid(row=2, column=0, sticky=tk.E, pady=8)

target_lufs_spinbox = ttk.Spinbox(frame, from_=-23, to=-14, increment=1, width=3)
target_lufs_spinbox.set(-19)
target_lufs_spinbox.grid(row=2, column=1, sticky=tk.W, pady=8)

button_browse = ttk.Button(frame, text="瀏覽...", bootstyle="danger", cursor='hand2', command=select_files)
button_browse.grid(row=2, column=2, sticky=tk.E, pady=8)

# 輸出目錄設置區域
label_output = ttk.Label(frame, text="輸出目錄:")
label_output.grid(row=3, column=0, sticky=tk.W, pady=5)

output_dir_entry = ttk.Entry(frame, width=50)
output_dir_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
output_dir_entry.insert(0, config['DEFAULT']['output_dir'])

button_output = ttk.Button(frame, text="更換...", bootstyle="info-outline", command=select_output_dir)
button_output.grid(row=3, column=2, sticky=tk.W, pady=5)

# 進度條區域（預留位置）
progress_var = tk.DoubleVar()
progress_var.set(0)
progress_bar = ttk.Progressbar(frame, variable=progress_var, maximum=1.0)
progress_bar.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=0)

# 轉檔按鈕
button_process = ttk.Button(frame, text="轉檔", bootstyle="danger", cursor='hand2', command=start_processing)
button_process.grid(row=6, column=2, sticky=tk.E, pady=3)

# 設置拖放功能
files_text.drop_target_register(DND_FILES)
files_text.dnd_bind('<<Drop>>', drop)

# 設定 grid 權重
frame.columnconfigure(1, weight=1)
frame.rowconfigure(1, weight=1)

# 啟動主循環
form.mainloop()
