import os
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import threading

class CodeScannerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Code Scanner for AI")
        self.root.geometry("800x600")
        
        # Create menu frame
        menu_frame = tk.Frame(root)
        menu_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Directory selection
        tk.Label(menu_frame, text="Directory:").pack(side=tk.LEFT, padx=5)
        self.dir_var = tk.StringVar()
        tk.Entry(menu_frame, textvariable=self.dir_var, width=50).pack(side=tk.LEFT, padx=5)
        tk.Button(menu_frame, text="Browse", command=self.browse_directory).pack(side=tk.LEFT, padx=5)
        tk.Button(menu_frame, text="Scan", command=self.start_scan, bg="green", fg="white").pack(side=tk.LEFT, padx=5)
        
        # Output text area
        self.output_text = scrolledtext.ScrolledText(root, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Button frame
        button_frame = tk.Frame(root)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(button_frame, text="Copy to Clipboard", command=self.copy_to_clipboard).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Save to File", command=self.save_to_file).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Clear", command=self.clear_output).pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = tk.Label(root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
    
    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_var.set(directory)
    
    def start_scan(self):
        directory = self.dir_var.get()
        if not directory or not os.path.exists(directory):
            messagebox.showerror("Error", "Please select a valid directory")
            return
        
        # Run scan in separate thread to prevent GUI freezing
        threading.Thread(target=self.scan_directory, args=(directory,), daemon=True).start()
    
    def scan_directory(self, directory):
        self.status_label.config(text="Scanning...")
        self.output_text.delete(1.0, tk.END)
        
        output_lines = []
        file_count = 0
        
        skip_dirs = {
            '__pycache__', '.git', '.vscode', '.idea', 'node_modules',
            'venv', 'env', '.env', 'dist', 'build', '.pytest_cache'
        }
        
        skip_extensions = {
            '.pyc', '.pyo', '.exe', '.dll', '.so', '.dylib',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico',
            '.mp3', '.mp4', '.avi', '.mov', '.pdf', '.zip',
            '.tar', '.gz', '.rar', '.7z', '.db', '.sqlite', '.css'
        }
        
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, directory)
                
                _, ext = os.path.splitext(file.lower())
                if ext in skip_extensions:
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    output_lines.append(f"{relative_path}:")
                    output_lines.append(content)
                    output_lines.append("")
                    
                    file_count += 1
                    self.status_label.config(text=f"Processed {file_count} files... Current: {relative_path}")
                    
                except Exception:
                    continue
        
        # Update output text
        final_output = "\n".join(output_lines)
        self.output_text.insert(1.0, final_output)
        self.status_label.config(text=f"Scan complete! Processed {file_count} files.")
    
    def copy_to_clipboard(self):
        content = self.output_text.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.status_label.config(text="Copied to clipboard!")
    
    def save_to_file(self):
        content = self.output_text.get(1.0, tk.END)
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.status_label.config(text=f"Saved to {file_path}")
    
    def clear_output(self):
        self.output_text.delete(1.0, tk.END)
        self.status_label.config(text="Output cleared")

if __name__ == "__main__":
    root = tk.Tk()
    app = CodeScannerGUI(root)
    root.mainloop()