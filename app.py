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
model_options = ["gemini-1.5-flash", "gemini-1.5-pro"]  

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
    if image_path.lower().endswith('.jpg') or image_path.lower().endswith('.jpeg'):
        with exiftool.ExifToolHelper() as et:
            metadata = et.get_metadata(image_path)
            title = metadata.get('XMP-dc:Title', '')
            keywords = metadata.get('XMP-dc:Subject', '')
        return not title or not keywords
    elif image_path.lower().endswith('.png'):
        img = Image.open(image_path)
        metadata = img.info
        title = metadata.get('Title', '')
        keywords = metadata.get('Keywords', '')
        return not title or not keywords
    return True

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
    model_name = selected_model.get()
    model = genai.GenerativeModel(model_name=model_name)

    temperature_value = temperature_slider.get()
    generation_config["temperature"] = temperature_value

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
                print(f"Processing file...")
                failed_files.append(image_path)
                continue

        for image_path in failed_files:
            try:
                process_image(image_path)
                move_file(image_path, output_directory)
            except Exception as e:
                error_message = str(e)
                print(f"Failed to process file, Limit quota")

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
        print(f"Maybe some files are not processed, you can try again")
        messagebox.showinfo("Info", f"Processing complete.\nmaybe some files are not processed, you can try again")

def process_image(image_path):
    img = Image.open(image_path)
    rename_result = model.generate_content(["get a title for the image", img])
    title_result = model.generate_content(["get a short description for the image", img])
    tags_result = model.generate_content(["get relevant tags delimited by comma, not hashtags, for the images", img])

    max_length = 64
    tags_split = split_text(tags_result.text, max_length)

    if image_path.lower().endswith('.jpg') or image_path.lower().endswith('.jpeg') or image_path.lower().endswith('.png'):
        commands = ["-overwrite_original", f'-XMP-dc:Title={title_result.text}', f'-XMP-dc:Description={title_result.text}']
        for i, part in enumerate(tags_split):
            commands.append(f'-XMP-dc:Subject={part}')

        commands.append(image_path)

        try:
            with exiftool.ExifTool() as et:
                et.execute(*commands)
        except exiftool.exceptions.ExifToolExecuteError as e:
            print(f"ExifTool error: {e}")
            raise

    if rename_enabled.get():
        new_filename = f"{rename_result.text}{os.path.splitext(image_path)[1]}"
        new_path = os.path.join(output_directory, new_filename)

        if os.path.exists(new_path):
            base_filename, extension = os.path.splitext(new_filename)
            counter = 1
            while os.path.exists(new_path):
                new_filename = f"{base_filename}_{counter}{extension}"
                new_path = os.path.join(output_directory, new_filename)
                counter += 1

        os.rename(image_path, new_path)

def get_unique_filename(directory, filename):
    base, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    while os.path.exists(os.path.join(directory, new_filename)):
        new_filename = f"{base}_{counter}{ext}"
        counter += 1
    return new_filename

def move_file(file_path, target_directory):
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)
    unique_filename = get_unique_filename(target_directory, os.path.basename(file_path))
    shutil.move(file_path, os.path.join(target_directory, unique_filename))

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
root.geometry("670x950") 

selected_model = tk.StringVar(value=model_options[0]) 

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

rename_enabled = tk.BooleanVar(value=False)

rename_checkbox_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
rename_checkbox_frame.pack(pady=10, anchor="center")

rename_checkbox = ctk.CTkCheckBox(rename_checkbox_frame, text="Enable Rename", variable=rename_enabled,checkbox_width=14,checkbox_height=14,border_width=1,corner_radius=3,font=("Segoe UI Bold", 14),                              
                                  fg_color="#6ccc4f")
rename_checkbox.pack(anchor="center")

label_2 = ctk.CTkLabel(header_frame, pady=(20))
customize_main_label(label_2, "© 2024 Kadang_Kesel", font_size=9)

frame = ctk.CTkFrame(root, fg_color="transparent")
frame.pack(padx=10, pady=30, anchor="center")

model_temperature_frame = ctk.CTkFrame(frame, fg_color="transparent")
model_temperature_frame.pack(pady=10, padx=10, anchor="center")

model_frame = ctk.CTkFrame(model_temperature_frame, fg_color="transparent")
model_frame.pack(side="left", padx=50)

temperature_frame = ctk.CTkFrame(model_temperature_frame, fg_color="transparent")
temperature_frame.pack(side="left", padx=10, pady=0)

model_selection_label = ctk.CTkLabel(model_frame, text="Select Model:", font=("Segoe UI Bold", 14))
model_selection_label.pack(pady=0,padx=(0,100), anchor="center")

model_dropdown = ctk.CTkComboBox(model_frame, values=model_options, variable=selected_model,border_color="#6ccc4f",fg_color="#1d3815",button_color="#6ccc4f",button_hover_color="#1d560c")
model_dropdown.pack(pady=20, padx=(0,100), anchor="center")

temperature_label = ctk.CTkLabel(temperature_frame, text="Select Temperature:", font=("Segoe UI Bold", 14))
temperature_label.pack(pady=10, anchor="center")

temperature_slider = ctk.CTkSlider(temperature_frame, from_=0.0, to=1.0, number_of_steps=100,button_hover_color="#1d560c", fg_color="#1d3815",progress_color="#538f40",button_color="#6ccc4f")
temperature_slider.set(0.7) 
temperature_slider.pack(pady=10, anchor="center")

temperature_value_label = ctk.CTkLabel(temperature_frame, text=f"Temperature: {temperature_slider.get():.2f}", font=("Segoe UI Bold", 12))
temperature_value_label.pack(pady=1, anchor="center")

def update_temperature_label(value):
    temperature_value_label.configure(text=f"Temperature: {float(value):.2f}")

temperature_slider.configure(command=update_temperature_label)

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

instagram_button = ctk.CTkButton(social_frame,border_color="white", fg_color="transparent", hover_color="#eeeeee", border_width=1, corner_radius=8, image=ctk.CTkImage(Image.open(instagram_logo_path)), text="", width=32, height=32, command=lambda: open_url("https://www.instagram.com/hadiyuli_"))
instagram_button.pack(side="left", padx=10)

paypal_button = ctk.CTkButton(social_frame,border_color="white", fg_color="transparent", hover_color="#eeeeee", border_width=1, corner_radius=8, image=ctk.CTkImage(Image.open(paypal_logo_path)), text="", width=32, height=32, command=lambda: open_url("paypal.me/KadangKesel"))
paypal_button.pack(side="left", padx=10)

github_button = ctk.CTkButton(social_frame,border_color="white", fg_color="transparent",hover_color="#eeeeee", border_width=1, corner_radius=8, image=ctk.CTkImage(Image.open(github_logo_path)), text="", width=32, height=32, command=lambda: open_url("https://github.com/kadangkesel"))
github_button.pack(side="left", padx=10)

root.mainloop()
