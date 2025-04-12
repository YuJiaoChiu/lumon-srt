import re
import json
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext, messagebox
from pathlib import Path
import threading
from collections import Counter
from tkinter import font as tkfont
import pickle
from tkinter import TclError

# 词典文件路径
CORRECTION_DICT_FILE = "terms.json"
PROTECTION_DICT_FILE = "保护terms.json"
CONFIG_FILE = "config.pkl"

class SubtitleCorrectorGUI:
    def __init__(self, master):
        self.master = master
        master.title("字幕术语修正程序")
        master.geometry("900x700")
        
        # 设置字体和样式
        self.default_font = tkfont.nametofont("TkDefaultFont")
        self.default_font.configure(size=12)
        self.title_font = tkfont.Font(family="Helvetica", size=16, weight="bold")
        
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置样式
        style.configure("TButton", padding=6, relief="flat", background="#4CAF50", foreground="white")
        style.map("TButton", background=[('active', '#45a049')])
        style.configure("TEntry", padding=6)
        style.configure("Treeview", rowheight=25, font=self.default_font)
        style.configure("Treeview.Heading", font=self.title_font)
        
        self.file_paths = []
        
        # 初始化词典文件路径
        self.correction_dict_file = CORRECTION_DICT_FILE
        self.protection_dict_file = PROTECTION_DICT_FILE
        self.default_output_folder = ''
        self.use_source_folder = True  # 默认使用源文件地址

        # 创建主框架
        main_frame = ttk.Frame(master, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建状态栏
        self.create_status_bar()
        
        # 文件选择部分
        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(file_frame, text="字幕文件:", font=self.title_font).pack(side=tk.LEFT, padx=(0, 10))
        self.file_listbox = tk.Listbox(file_frame, width=50, height=5)
        self.file_listbox.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))
        
        button_frame = ttk.Frame(file_frame)
        button_frame.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Button(button_frame, text="选择文件", command=self.browse_files).pack(fill=tk.X, pady=2)
        ttk.Button(button_frame, text="选择文件夹", command=self.browse_folder).pack(fill=tk.X, pady=2)
        ttk.Button(button_frame, text="清除列表", command=self.clear_file_list).pack(fill=tk.X, pady=2)
        
        # 操作按钮
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Button(action_frame, text="开始处理", command=self.start_processing).pack(side=tk.LEFT, padx=(0, 10))
        self.show_stats_button = ttk.Button(action_frame, text="显示统计信息", command=self.show_statistics, state=tk.DISABLED)
        self.show_stats_button.pack(side=tk.LEFT)
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, length=300, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(0, 10))
        
        # 状态标签
        self.status_label = ttk.Label(main_frame, text="", font=self.default_font)
        self.status_label.pack(pady=(0, 10))
        
        # 日志文本框
        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(log_frame, text="处理日志", font=self.title_font).pack(anchor=tk.W, pady=(0, 5))
        self.log_text = scrolledtext.ScrolledText(log_frame, width=80, height=20, font=self.default_font)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        self.total_replacements = Counter()

        # 加载词典和配置
        self.load_config()  # 先加载配置
        self.load_dictionaries()  # 然后加载词典

        # 更新状态栏
        self.update_status_bar()

    def create_menu(self):
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)
        
        dict_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="词典管理", menu=dict_menu)
        dict_menu.add_command(label="修改矫正词典", command=self.edit_correction_dict)
        dict_menu.add_command(label="修改保护词典", command=self.edit_protection_dict)
        dict_menu.add_command(label="选择矫正词典", command=self.select_correction_dict)
        dict_menu.add_command(label="选择保护词典", command=self.select_protection_dict)
        
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="配置", menu=config_menu)
        config_menu.add_command(label="保存配置", command=self.save_config)
        config_menu.add_command(label="加载配置", command=self.load_config)
        
        # 添加设置菜单
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="设置", menu=settings_menu)
        settings_menu.add_command(label="程序设置", command=self.open_settings)

    def create_status_bar(self):
        self.status_bar = ttk.Label(self.master, text="", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def update_status_bar(self):
        correction_file = Path(self.correction_dict_file).name
        protection_file = Path(self.protection_dict_file).name
        self.status_bar.config(text=f"矫正词典: {correction_file} | 保护词典: {protection_file}")

    def select_correction_dict(self):
        file = filedialog.askopenfilename(title="选择纠正词典文件", filetypes=[("JSON files", "*.json")])
        if file:
            self.correction_dict_file = file
            self.correction_dict = self.load_dictionary(self.correction_dict_file)
            self.log(f"已加载新的矫正词典，共{len(self.correction_dict)}个条目")
            self.update_status_bar()

    def select_protection_dict(self):
        file = filedialog.askopenfilename(title="选择保护词典文件", filetypes=[("JSON files", "*.json")])
        if file:
            self.protection_dict_file = file
            self.protection_dict = self.load_dictionary(self.protection_dict_file)
            self.log(f"已加载新的保护词典，共{len(self.protection_dict)}个条目")
            self.update_status_bar()

    def load_dictionaries(self):
        # 移除文件选择对话框，改为从配置加载
        self.correction_dict = self.load_dictionary(self.correction_dict_file)
        self.protection_dict = self.load_dictionary(self.protection_dict_file)
        self.log(f"纠正词典加载完成，共{len(self.correction_dict)}个条目")
        self.log(f"保护词典加载完成，共{len(self.protection_dict)}个条目")
        self.update_status_bar()

    def open_settings(self):
        SettingsDialog(self.master, self)

    def load_dictionary(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_dictionary(self, dictionary, filename):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(dictionary, f, ensure_ascii=False, indent=2)

    def edit_correction_dict(self):
        DictionaryEditor(self.master, "矫正词典", self.correction_dict, self.save_correction_dict)

    def edit_protection_dict(self):
        DictionaryEditor(self.master, "保护词典", self.protection_dict, self.save_protection_dict, protection=True)

    def save_correction_dict(self, new_dict):
        self.correction_dict = new_dict
        self.save_dictionary(self.correction_dict, self.correction_dict_file)
        self.log("矫正词典已更新并保存")

    def save_protection_dict(self, new_dict):
        self.protection_dict = new_dict
        self.save_dictionary(self.protection_dict, self.protection_dict_file)
        self.log("保护词典已更新并保存")

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.master.update_idletasks()

    def browse_files(self):
        files = filedialog.askopenfilenames(filetypes=[("SRT files", "*.srt")])
        self.add_files(files)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            files = list(Path(folder).glob('*.srt'))
            self.add_files(files)

    def add_files(self, files):
        for file in files:
            if str(file) not in self.file_paths:
                self.file_paths.append(str(file))
                self.file_listbox.insert(tk.END, Path(file).name)
        self.log(f"添加了 {len(files)} 个文件到列表")

    def clear_file_list(self):
        self.file_listbox.delete(0, tk.END)
        self.file_paths.clear()
        self.log("已清除文件列表")

    def drop(self, event):
        files = self.master.tk.splitlist(event.data)
        valid_files = [f for f in files if f.lower().endswith('.srt')]
        self.add_files(valid_files)

    def start_processing(self):
        if not self.file_paths:
            self.status_label.config(text="请选择文件")
            self.log("错误: 未选择文件")
            return
        
        self.show_stats_button.config(state=tk.DISABLED)
        self.total_replacements.clear()
        self.log("开始处理...")
        threading.Thread(target=self.process_files).start()

    def process_files(self):
        try:
            total_files = len(self.file_paths)
            self.log(f"开始处理 {total_files} 个字幕文件")
            
            self.progress['maximum'] = total_files
            self.progress['value'] = 0
            
            for i, file_path in enumerate(self.file_paths):
                self.log(f"处理文件 ({i+1}/{total_files}): {Path(file_path).name}")
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                corrected_content, replacements = self.correct_subtitles(content)
                self.total_replacements.update(replacements)
                
                if self.use_source_folder:
                    output_file = Path(file_path).with_name(Path(file_path).stem + '_corrected.srt')
                else:
                    output_file = Path(self.default_output_folder) / Path(file_path).with_name(Path(file_path).stem + '_corrected.srt').name
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(corrected_content)
                
                self.log(f"文件处理完成: {output_file.name}")
                self.log("本文件替换详情:")
                for (wrong, correct), count in replacements.items():
                    self.log(f"  '{wrong}' -> '{correct}': {count} 次")
                self.log(f"本文件总替换次数: {sum(replacements.values())}")
                self.log("------------------------")
                
                self.progress['value'] = i + 1
                self.master.update_idletasks()
            
            self.log("所有文件处理完成!")
            self.log(f"总替换次数: {sum(self.total_replacements.values())}")
            self.status_label.config(text=f"处理完成！共处理 {total_files} 个文件。")
            self.show_stats_button.config(state=tk.NORMAL)
        except Exception as e:
            self.log(f"发生错误: {str(e)}")
            self.status_label.config(text=f"发生错误: {str(e)}")

    def correct_subtitles(self, text):
        lines = text.split('\n')
        corrected_lines = []
        replacements = Counter()
        
        def should_correct(wrong, protected_words):
            wrong_lower = wrong.lower()
            for protected in protected_words:
                protected_lower = protected.lower()
                if protected_lower in wrong_lower:
                    if protected_lower != wrong_lower:
                        return True
                    return False
                if wrong_lower in protected_lower:
                    return False
            return True
        
        sorted_correction_items = sorted(self.correction_dict.items(), key=lambda x: len(x[0]), reverse=True)
        
        for line in lines:
            if '-->' in line:
                corrected_lines.append(line)
            else:
                if re.match(r'^\s*\([^)]*\)\s*$', line):
                    self.log(f"删除被括号括起来的行: {line}")
                    continue
                
                original_line = line
                replaced_positions = []  # 使用列表来存储已替换的位置范围
                
                for wrong, correct in sorted_correction_items:
                    if should_correct(wrong, self.protection_dict):
                        pattern = re.compile(re.escape(wrong), re.IGNORECASE)
                        
                        def replace_func(match):
                            start, end = match.span()
                            # 检查这个位置是否已经被替换过
                            if any(start < pos[1] and end > pos[0] for pos in replaced_positions):
                                return match.group(0)  # 如果已替换过，返回原始文本
                            
                            replaced = correct if correct else ''
                            if match.group(0).isupper():
                                replaced = replaced.upper()
                            elif match.group(0).istitle():
                                replaced = replaced.capitalize()
                            
                            # 记录这个位置已被替换
                            replaced_positions.append((start, end))
                            return replaced

                        new_line, count = pattern.subn(replace_func, line)
                        if count > 0:
                            line = new_line
                            replacements[(wrong, correct)] += count
                
                if line != original_line:
                    self.log(f"行: '{original_line}' 已更正为: '{line}'")
                corrected_lines.append(line)
        
        return '\n'.join(corrected_lines), replacements

    def show_statistics(self):
        stats_window = tk.Toplevel(self.master)
        stats_window.title("替换统计信息")
        stats_window.geometry("500x400")
        
        stats_frame = ttk.Frame(stats_window, padding="20")
        stats_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(stats_frame, text="替换统计信息", font=self.title_font).pack(pady=(0, 10))
        
        stats_text = scrolledtext.ScrolledText(stats_frame, width=60, height=20, font=self.default_font)
        stats_text.pack(fill=tk.BOTH, expand=True)
        
        total_count = sum(self.total_replacements.values())
        stats_text.insert(tk.END, f"总共替换次数: {total_count}\n\n")
        stats_text.insert(tk.END, "详细替换信息:\n")
        
        for (wrong, correct), count in self.total_replacements.most_common():
            stats_text.insert(tk.END, f"'{wrong}' -> '{correct}': {count} 次\n")
        
        stats_text.config(state=tk.DISABLED)

    def save_config(self):
        config = {
            'file_paths': self.file_paths,
            'correction_dict': self.correction_dict,
            'protection_dict': self.protection_dict,
            'correction_dict_file': self.correction_dict_file,
            'protection_dict_file': self.protection_dict_file,
            'default_output_folder': self.default_output_folder,
            'use_source_folder': self.use_source_folder
        }
        with open(CONFIG_FILE, 'wb') as f:
            pickle.dump(config, f)
        self.log("配置已保存")
        self.update_status_bar()

    def load_config(self):
        try:
            with open(CONFIG_FILE, 'rb') as f:
                config = pickle.load(f)
            self.file_paths = config.get('file_paths', [])
            self.correction_dict = config.get('correction_dict', {})
            self.protection_dict = config.get('protection_dict', {})
            self.correction_dict_file = config.get('correction_dict_file', CORRECTION_DICT_FILE)
            self.protection_dict_file = config.get('protection_dict_file', PROTECTION_DICT_FILE)
            self.default_output_folder = config.get('default_output_folder', '')
            self.use_source_folder = config.get('use_source_folder', True)
            self.save_dictionary(self.correction_dict, self.correction_dict_file)
            self.save_dictionary(self.protection_dict, self.protection_dict_file)
            self.file_listbox.delete(0, tk.END)
            for file_path in self.file_paths:
                self.file_listbox.insert(tk.END, Path(file_path).name)
            self.log("配置已加载")
            self.update_status_bar()
        except FileNotFoundError:
            self.log("未找到配置文件，使用默认设置")
            self.correction_dict_file = CORRECTION_DICT_FILE
            self.protection_dict_file = PROTECTION_DICT_FILE
            self.default_output_folder = ''
            self.use_source_folder = True
            self.load_dictionaries()

# 新增设置对话框类
class SettingsDialog:
    def __init__(self, parent, app):
        self.window = tk.Toplevel(parent)
        self.window.title("程序设置")
        self.app = app
        
        frame = ttk.Frame(self.window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="默认输出文件夹:").grid(row=0, column=0, sticky="w", pady=5)
        self.output_folder = ttk.Entry(frame, width=50)
        self.output_folder.grid(row=0, column=1, sticky="ew", pady=5)
        ttk.Button(frame, text="浏览", command=self.browse_output_folder).grid(row=0, column=2, padx=5)
        
        # 添加使用源文件地址的选项
        self.use_source_folder = tk.BooleanVar(value=self.app.use_source_folder)
        ttk.Checkbutton(frame, text="使用源文件地址作为输出地址", variable=self.use_source_folder).grid(row=1, column=0, columnspan=3, sticky="w", pady=5)
        
        ttk.Button(frame, text="保存设置", command=self.save_settings).grid(row=2, column=1, sticky="e", pady=10)
        
        # 初始化设置
        self.output_folder.insert(0, self.app.default_output_folder)

    def browse_output_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder.delete(0, tk.END)
            self.output_folder.insert(0, folder)

    def save_settings(self):
        self.app.default_output_folder = self.output_folder.get()
        self.app.use_source_folder = self.use_source_folder.get()
        self.app.save_config()
        self.window.destroy()

class DictionaryEditor:
    def __init__(self, parent, title, dictionary, save_callback, protection=False):
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("600x500")
        
        self.dictionary = dictionary
        self.save_callback = save_callback
        self.protection = protection
        
        self.create_widgets()
        self.load_dictionary()

    def create_widgets(self):
        frame = ttk.Frame(self.window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text=self.window.title(), font=("Helvetica", 16, "bold")).pack(pady=(0, 10))
        
        # 添加搜索框
        search_frame = ttk.Frame(frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(search_frame, text="搜索", command=self.search_entries).pack(side=tk.RIGHT, padx=(5, 0))
        
        columns = ('保护词',) if self.protection else ('错误词', '正确词')
        self.tree = ttk.Treeview(frame, columns=columns, show='headings')
        for col in columns:
            self.tree.heading(col, text=col)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(button_frame, text="添加", command=self.add_entry).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="编辑", command=self.edit_entry).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="删除", command=self.delete_entry).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="保存", command=self.save_dictionary).pack(side=tk.RIGHT, padx=5)

    def load_dictionary(self):
        self.tree.delete(*self.tree.get_children())
        for key, value in self.dictionary.items():
            if self.protection:
                self.tree.insert('', 'end', values=(key,))
            else:
                self.tree.insert('', 'end', values=(key, value))

    def search_entries(self):
        search_term = self.search_entry.get().lower()
        self.tree.delete(*self.tree.get_children())
        for key, value in self.dictionary.items():
            if search_term in key.lower() or (not self.protection and search_term in value.lower()):
                if self.protection:
                    self.tree.insert('', 'end', values=(key,))
                else:
                    self.tree.insert('', 'end', values=(key, value))

    def add_entry(self):
        if self.protection:
            AddProtectionEntryDialog(self.window, self.add_protection_entry_callback)
        else:
            AddEntryDialog(self.window, self.add_entry_callback)

    def add_entry_callback(self, wrong, correct):
        self.dictionary[wrong] = correct
        self.load_dictionary()

    def add_protection_entry_callback(self, word):
        self.dictionary[word] = ""
        self.load_dictionary()

    def edit_entry(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个条目")
            return
        item = self.tree.item(selected[0])
        if self.protection:
            old_word = item['values'][0]
            EditProtectionEntryDialog(self.window, old_word, self.edit_protection_entry_callback)
        else:
            old_wrong, old_correct = item['values']
            EditEntryDialog(self.window, old_wrong, old_correct, self.edit_entry_callback)

    def edit_entry_callback(self, old_wrong, new_wrong, new_correct):
        del self.dictionary[old_wrong]
        self.dictionary[new_wrong] = new_correct
        self.load_dictionary()

    def edit_protection_entry_callback(self, old_word, new_word):
        del self.dictionary[old_word]
        self.dictionary[new_word] = ""
        self.load_dictionary()

    def delete_entry(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个条目")
            return
        item = self.tree.item(selected[0])
        word = item['values'][0]
        del self.dictionary[word]
        self.load_dictionary()

    def save_dictionary(self):
        self.save_callback(self.dictionary)
        self.window.destroy()

class AddEntryDialog:
    def __init__(self, parent, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("添加条目")
        self.window.geometry("300x150")
        self.callback = callback
        
        frame = ttk.Frame(self.window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="错误词:").grid(row=0, column=0, sticky="w", pady=5)
        self.wrong_entry = ttk.Entry(frame)
        self.wrong_entry.grid(row=0, column=1, sticky="ew", pady=5)
        
        ttk.Label(frame, text="正确词:").grid(row=1, column=0, sticky="w", pady=5)
        self.correct_entry = ttk.Entry(frame)
        self.correct_entry.grid(row=1, column=1, sticky="ew", pady=5)
        
        ttk.Button(frame, text="确定", command=self.submit).grid(row=2, column=1, sticky="e", pady=10)
        
        self.wrong_entry.bind("<Return>", lambda e: self.correct_entry.focus())
        self.correct_entry.bind("<Return>", lambda e: self.submit())

    def submit(self):
        wrong = self.wrong_entry.get().strip()
        correct = self.correct_entry.get().strip()
        if wrong and correct:
            self.callback(wrong, correct)
            self.window.destroy()
        else:
            messagebox.showwarning("警告", "请填写所有字段")

class AddProtectionEntryDialog:
    def __init__(self, parent, callback):
        self.window = tk.Toplevel(parent)
        self.window.title("添加保护词")
        self.window.geometry("300x100")
        self.callback = callback
        
        frame = ttk.Frame(self.window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="保护词:").grid(row=0, column=0, sticky="w", pady=5)
        self.word_entry = ttk.Entry(frame)
        self.word_entry.grid(row=0, column=1, sticky="ew", pady=5)
        
        ttk.Button(frame, text="确定", command=self.submit).grid(row=1, column=1, sticky="e", pady=10)
        
        self.word_entry.bind("<Return>", lambda e: self.submit())

    def submit(self):
        word = self.word_entry.get().strip()
        if word:
            self.callback(word)
            self.window.destroy()
        else:
            messagebox.showwarning("警告", "请填写保护词")

class EditEntryDialog(AddEntryDialog):
    def __init__(self, parent, old_wrong, old_correct, callback):
        super().__init__(parent, callback)
        self.window.title("编辑条目")
        self.old_wrong = old_wrong
        self.wrong_entry.insert(0, old_wrong)
        self.correct_entry.insert(0, old_correct)

    def submit(self):
        new_wrong = self.wrong_entry.get().strip()
        new_correct = self.correct_entry.get().strip()
        if new_wrong and new_correct:
            self.callback(self.old_wrong, new_wrong, new_correct)
            self.window.destroy()
        else:
            messagebox.showwarning("警告", "请填写所有字段")

class EditProtectionEntryDialog(AddProtectionEntryDialog):
    def __init__(self, parent, old_word, callback):
        super().__init__(parent, callback)
        self.window.title("编辑保护词")
        self.old_word = old_word
        self.word_entry.insert(0, old_word)

    def submit(self):
        new_word = self.word_entry.get().strip()
        if new_word:
            self.callback(self.old_word, new_word)
            self.window.destroy()
        else:
            messagebox.showwarning("警告", "请填写保护词")

if __name__ == "__main__":
    root = tk.Tk()
    app = SubtitleCorrectorGUI(root)
    root.mainloop()