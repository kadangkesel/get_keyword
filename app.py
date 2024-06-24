import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import exiftool
import google.generativeai as genai
import customtkinter as ctk

model = None
directory_path = ""
output_directory = ""
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

def split_text(text, max_length):
    parts = text.split(',')
    result = []
    current = ''
    for part in parts:
        if len(current) + len(part) + 1 <= max_length:  
            if current:
                current += ',' + part
            else:
                current = part
        else:
            result.append(current)
            current = part
    if current:
        result.append(current)
    return result

def check_metadata(image_path):
    with exiftool.ExifToolHelper() as et:
        metadata = et.get_metadata(image_path)
        title = metadata.get('-Title', '')
        keywords = metadata.get('-Keywords', '')

    return not title or not keywords

def process_images(api_key):
    global model, directory_path, output_directory
    if not directory_path:
        messagebox.showerror("Error", "Please select a directory first.")
        return
    if not output_directory:
        messagebox.showerror("Error", "Please select an output directory.")
        return
    if not api_key:
        messagebox.showerror("Error", "Please enter the API Key.")
        return

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")

    try:
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

        files = [os.path.join(directory_path, f) for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]
        failed_files = []

        for image_path in files:
            try:
                process_image(image_path)
                move_file(image_path, output_directory)
            except Exception as e:
                error_message = str(e)
                print(f"Error processing file, try to load again")
                failed_files.append(image_path)
                continue

        # Retry failed files
        for image_path in failed_files:
            try:
                process_image(image_path)
                move_file(image_path, output_directory)
            except Exception as e:
                error_message = str(e)
                print(f"Failed to process file, Limit Quota")

        # Check and reprocess files with empty metadata
        for image_path in files:
            if check_metadata(image_path):
                try:
                    process_image(image_path)
                    move_file(image_path, output_directory)
                except Exception as e:
                    error_message = str(e)
                    print(f"Checking metadata, and try to load again")

        print("Processing complete.")
        messagebox.showinfo("Info", "Processing complete.")
    
    except Exception as e:
        error_message = str(e)
        print(f"Some files are not processed, please retry")
        messagebox.showinfo("Info", f"Processing complete.\nmaybe some files are not processed, you can try again")

def process_image(image_path):
    img = Image.open(image_path)
    rename_result = model.generate_content(["get a title for the image", img])
    title_result = model.generate_content(["get a short description for the image", img])
    tags_result = model.generate_content(["get relevant tags delimited by comma, not hashtags, for the images", img])

    max_length = 64
    tags_split = split_text(tags_result.text, max_length)

    with exiftool.ExifTool() as et:
        commands = ["-overwrite_original", f'-Title={title_result.text}']
        for i, part in enumerate(tags_split):
            commands.append(f'-Keywords={part}')

        commands.append(image_path)
        try:
            et.execute(*commands)
        except exiftool.ExifToolExecuteError as e:
            print(f"ExifTool error: {e}")
            raise

def move_file(file_path, target_directory):
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)
    shutil.move(file_path, os.path.join(target_directory, os.path.basename(file_path)))

def select_directory(dir_label):
    global directory_path
    directory_path = filedialog.askdirectory()
    if directory_path:
        dir_label.configure(text=f"{directory_path}")

def select_output_directory(output_label):
    global output_directory
    output_directory = filedialog.askdirectory()
    if output_directory:
        output_label.configure(text=f"{output_directory}")

ctk.set_appearance_mode("dark") 
ctk.set_default_color_theme("dark-blue")  
ctk.deactivate_automatic_dpi_awareness()

root = ctk.CTk()
root.title("Get Keyword")
root.geometry("680x768") 

def customize_label(label, text, font_size=45, pady=10, anchor="center"):
    label.configure(text=text, font=("Segoe UI Bold", font_size), fg_color="transparent", text_color='#6ccc4f') 
    label.pack(pady=pady, anchor=anchor)

def customize_main_label(label, text, font_size=12, pady=1, anchor="center"):
    label.configure(text=text, font=("Segoe UI Bold", font_size), fg_color="transparent")  
    label.pack(pady=pady, anchor=anchor)

def customize_regular_label(label, text, font_size=12, pady=1, anchor="center"):
    label.configure(text=text, font=("Segoe UI", font_size), fg_color="transparent")    
    label.pack(pady=pady, anchor=anchor)

def customize_entry(entry, show_char="*", width=250, height=30, border_color="#30232d", border_width=1, corner_radius=2):
    entry.configure(show=show_char, width=width, height=height, border_width=border_width, corner_radius=corner_radius)
    entry.pack(pady=10, anchor="center")

def customize_button(button, text, command, fg_color="transparent", hover_color="#6ccc4f", corner_radius=8, font_size=12):
    button.configure(text=text, command=command, fg_color=fg_color, hover_color=hover_color, corner_radius=corner_radius, font=("Segoe UI Bold", font_size))
    button.pack(pady=10, anchor="center")

header_frame = ctk.CTkFrame(root, fg_color="#101010", height=700, width=100, corner_radius=1)
header_frame.pack(fill="both", pady=(0, 10), anchor="n")

logo_label = ctk.CTkLabel(header_frame, text="")
logo_label.pack(pady=110, anchor="center")
customize_label(logo_label, "GetKey{word}", pady=(90,10))

label_3 = ctk.CTkLabel(header_frame)
customize_main_label(label_3, "Made Keyword & Title generated by Gemini AI", font_size=12,pady=(0,30))

select_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
select_frame.pack(pady=10, padx=10, anchor="center")

select_buttons_frame = ctk.CTkFrame(select_frame, fg_color="transparent")
select_buttons_frame.pack(pady=10, anchor="center")

select_directory_frame = ctk.CTkFrame(select_buttons_frame, fg_color="transparent")
select_directory_frame.pack(side="left", padx=70)

select_button = ctk.CTkButton(select_directory_frame, border_color="#6ccc4f", border_width=1, corner_radius=8)
customize_button(select_button, "Select Directory", command=lambda: select_directory(dir_label))

dir_label = ctk.CTkLabel(select_directory_frame)
customize_main_label(dir_label, "No directory selected")

output_directory_frame = ctk.CTkFrame(select_buttons_frame, fg_color="transparent")
output_directory_frame.pack(side="left", padx=70)

output_button = ctk.CTkButton(output_directory_frame, border_color="#6ccc4f", border_width=1, corner_radius=8)
customize_button(output_button, "Select Output Directory", command=lambda: select_output_directory(output_label))

output_label = ctk.CTkLabel(output_directory_frame)
customize_main_label(output_label, "No output directory selected")

label_2 = ctk.CTkLabel(header_frame, pady=(20))
customize_main_label(label_2, "© 2024 Kadang_Kesel", font_size=9)

frame = ctk.CTkFrame(root, fg_color="transparent")
frame.pack(padx=100, pady=30, anchor="center")

customize_main_label(ctk.CTkLabel(frame), "Enter your Gemini API key:", font_size=14)

api_key_entry = ctk.CTkEntry(frame)
customize_entry(api_key_entry)

def start_processing():
    api_key = api_key_entry.get()
    process_images(api_key)

process_button = ctk.CTkButton(frame, border_color="#6ccc4f", border_width=1, corner_radius=8)
customize_button(process_button, "Start", command=start_processing)

def open_url(url):
    import webbrowser
    webbrowser.open(url, new=1)

social_frame = ctk.CTkFrame(frame, fg_color="transparent")
social_frame.pack(pady=(120,0), anchor="center")

instagram_logo_path = r'.\assets\instagram.png'
paypal_logo_path = r'.\assets\paypal.png'
github_logo_path = r'.\assets\github.png'

instagram_button = ctk.CTkButton(social_frame,border_color="white", fg_color="transparent", hover_color="#eeeeee", border_width=0.6, corner_radius=8, image=ctk.CTkImage(Image.open(instagram_logo_path)), text="", width=32, height=32, command=lambda: open_url("https://www.instagram.com/hadiyuli_"))
instagram_button.pack(side="left", padx=10)

paypal_button = ctk.CTkButton(social_frame,border_color="white", fg_color="transparent", hover_color="#eeeeee", border_width=1, corner_radius=8, image=ctk.CTkImage(Image.open(paypal_logo_path)), text="", width=32, height=32, command=lambda: open_url("paypal.me/KadangKesel"))
paypal_button.pack(side="left", padx=10)

github_button = ctk.CTkButton(social_frame,border_color="white", fg_color="transparent",hover_color="#eeeeee", border_width=1, corner_radius=8, image=ctk.CTkImage(Image.open(github_logo_path)), text="", width=32, height=32, command=lambda: open_url("https://github.com/kadangkesel"))
github_button.pack(side="left", padx=10)

root.mainloop()
