import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image
import exiftool
import google.generativeai as genai
import customtkinter as ctk
import csv
import sys
from termcolor import colored, cprint

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
csv_file_path = ""

def split_text(text, max_length):
    parts = text.split(';')
    result = []
    for part in parts:
        part = part.strip() 
        if len(part) <= max_length:
            result.append(part)
        else:
            while len(part) > max_length:
                result.append(part[:max_length])
                part = part[max_length:]
            result.append(part)
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

def export_metadata_to_csv(filename, title, description, keywords):
    global csv_file_path
    file_exists = os.path.isfile(csv_file_path)
    with open(csv_file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Filename", "Title", "Description", "Keywords", "Category", "Release"])  # Write header
        writer.writerow([filename, title, description, keywords])  # Use the filename directly

def resize_image(image_path, max_size=(2048, 2048)):
    img = Image.open(image_path)
    img.thumbnail(max_size, Image.LANCZOS)
    resized_path = os.path.join(output_directory, f"temp_img_{os.path.basename(image_path)}")
    img.save(resized_path)
    return resized_path

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
            except Exception as e:
                error_message = str(e)
                print(f"Processing file...{error_message}")
                failed_files.append(image_path)
                continue

        for image_path in failed_files:
            try:
                process_image(image_path)
            except Exception as e:
                error_message = str(e) 
                print(f"Success{error_message}")

        for image_path in files:
            if check_metadata(image_path):
                try:
                    process_image(image_path)
                except Exception as e:
                    error_message = str(e)
                    print(f"Checking metadata...{error_message}")

        print("Processing complete.")
        messagebox.showinfo("Info", "Processing complete.")
    
    except Exception as e:
        error_message = str(e)
        print(f"Success")
        messagebox.showinfo("Info", f"Processing complete.\nMaybe some files are not processed, you can try again")

def process_image(image_path):
    try:
        cprint(f"---------------------------LOG INFORMATION-------------------------------\n","green",attrs=["blink"])
        
        filename = os.path.basename(image_path)
        print(f"Processing image: {filename}")

        resized_image_path = resize_image(image_path)
        print(f"Preparing image")

        with Image.open(resized_image_path) as img:
            print(f"Opened image for processing")
            
            if os.path.getsize(resized_image_path) > 20 * 1024 * 1024:
                print(f"Image size is greater than 20MB, uploading file using File API.")
                file_ref = genai.upload_file(resized_image_path)
                print(f"File uploaded, file reference: {file_ref}")
            else:
                print(f"Image size is less than or equal to 20MB, processing locally.")
                file_ref = img

            prompt_title = "Get a short and concise description for the image"
            response_title = model.generate_content([prompt_title, file_ref])
            title_result = response_title.text.strip()

            prompt_tags = "Get relevant tags delimited by semicolon for the image"
            response_tags = model.generate_content([prompt_tags, file_ref])
            tags_result = response_tags.text.strip()

            full_title = title_result
            if '.' in full_title:
                title = full_title.split('.')[0]
            else:
                title = full_title[:300]

            if len(title) > 300:
                title = title[:300]

            print(f"Processed title")

            tags = tags_result.split(';')
            if len(tags) > 49:
                tags = tags[:49]
            limited_tags = ';'.join(tags)
            print(f"Processed tags")

            final_filename = os.path.basename(image_path)
            final_image_path = image_path

        if rename_enabled.get():
            print(f"Renaming enabled.")
            prompt_rename = "Get title for the image"
            response_rename = model.generate_content([prompt_rename, file_ref])
            new_filename = sanitize_filename(response_rename.text) + os.path.splitext(image_path)[1]
            unique_new_path = get_unique_filename(output_directory, new_filename)
            print(f"Renaming image to: {new_filename}")

            shutil.move(image_path, unique_new_path)
            final_image_path = unique_new_path  
            final_filename = new_filename

            print(f"Moved image to {unique_new_path}")
        else:
            unique_filename = get_unique_filename(output_directory, os.path.basename(image_path))
            new_path = os.path.join(output_directory, unique_filename)
            shutil.move(image_path, new_path)
            final_image_path = new_path  
            final_filename = unique_filename

            print(f"Moved image to {new_path}")

        if export_csv_enabled.get():
            print(f"Exporting metadata to CSV.")
            export_metadata_to_csv(final_filename, title, title_result, limited_tags)

        commands = ["-overwrite_original"]

        if final_image_path.lower().endswith(('.jpg', '.jpeg')):
            print(f"Preparing to write metadata for JPG/JPEG image.")
            commands += [
                f'-Title={title}',
                f'-Description={title_result}',
                f'-XPTitle={title}',
                f'-XPComment={title_result}',
                f'-XPKeywords={limited_tags}',
                f'-XMP-dc:Title={title}',
                f'-XMP-dc:Description={title_result}',
                f'-XMP-dc:Subject={limited_tags}',
                f'-IPTC:ObjectName={title}',
                f'-IPTC:Caption-Abstract={title_result}',
            ]

            iptc_keywords_parts = split_text(limited_tags, 64)
            for part in iptc_keywords_parts:
                commands.append(f'-IPTC:Keywords={part}')

        elif final_image_path.lower().endswith('.png'):
            print(f"Preparing to write metadata for PNG image.")
            commands += [
                f'-XMP-dc:Title={title}',
                f'-XMP-dc:Description={title_result}',
                f'-XMP-dc:Subject={limited_tags}',
                f'-EXIF:XPTitle={title_result}',
                f'-EXIF:XPKeywords={limited_tags}',
                f'-EXIF:XPSubject={title_result}',
                f'-IPTC:ObjectName={title_result}',
                f'-IPTC:Caption-Abstract={title_result}',
            ]

            iptc_keywords_parts = split_text(limited_tags, 64)
            for part in iptc_keywords_parts:
                commands.append(f'-IPTC:Keywords={part}')

        commands.append(final_image_path)

        try:
            with exiftool.ExifTool() as et:
                et.execute(*commands)
            print(f"Metadata written to image")
        except exiftool.exceptions.ExifToolExecuteError as e:
            print(f"ExifTool error: {e}")
            raise

    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
        raise

    finally:
        if os.path.exists(resized_image_path):
            try:
                os.remove(resized_image_path)
                print(f"Removed temp image")
            except Exception as e:
                print(f"Error removing temp image: {e}")
        cprint(f"-------------------------------LOG END-----------------------------------\n","green",attrs=["blink"])


def get_unique_filename(directory, filename):
    base, extension = os.path.splitext(filename)
    counter = 1
    unique_filename = filename
    while os.path.exists(os.path.join(directory, unique_filename)):
        unique_filename = f"{base}_{counter}{extension}"
        counter += 1
    return os.path.join(directory, unique_filename)

def sanitize_filename(filename):
    return "".join(c if c.isalnum() or c in (" ", ".", "_") else "_" for c in filename)

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
    global output_directory, csv_file_path
    output_directory = filedialog.askdirectory()
    if output_directory:
        output_label.configure(text=f"{output_directory}")
        csv_file_path = os.path.join(output_directory, "metadata.csv")

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

rename_checkbox = ctk.CTkCheckBox(rename_checkbox_frame, text="Enable Rename", variable=rename_enabled, checkbox_width=14, checkbox_height=14, border_width=1,hover_color="#1d560c", corner_radius=3, font=("Segoe UI Bold", 14), fg_color="#6ccc4f")
rename_checkbox.pack(side="left", anchor="center")

export_csv_enabled = tk.BooleanVar(value=False)

export_csv_checkbox = ctk.CTkCheckBox(rename_checkbox_frame, text="Export to CSV", variable=export_csv_enabled, checkbox_width=14, checkbox_height=14, border_width=1,hover_color="#1d560c", corner_radius=3, font=("Segoe UI Bold", 14), fg_color="#6ccc4f")
export_csv_checkbox.pack(side="left", padx=20, anchor="center")

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

model_dropdown = ctk.CTkComboBox(model_frame, values=model_options, variable=selected_model, border_color="#6ccc4f", fg_color="#1d3815", button_color="#6ccc4f", button_hover_color="#1d560c")
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

instagram_button = ctk.CTkButton(social_frame, border_color="white", fg_color="transparent", hover_color="#eeeeee", border_width=1, corner_radius=8, image=ctk.CTkImage(Image.open(r'.\assets\instagram.png')), text="", width=32, height=32, command=lambda: open_url("https://www.instagram.com/hadiyuli_"))
instagram_button.pack(side="left", padx=10)

paypal_button = ctk.CTkButton(social_frame, border_color="white", fg_color="transparent", hover_color="#eeeeee", border_width=1, corner_radius=8, image=ctk.CTkImage(Image.open(r'.\assets\paypal.png')), text="", width=32, height=32, command=lambda: open_url("paypal.me/KadangKesel"))
paypal_button.pack(side="left", padx=10)

github_button = ctk.CTkButton(social_frame, border_color="white", fg_color="transparent", hover_color="#eeeeee", border_width=1, corner_radius=8, image=ctk.CTkImage(Image.open(r'.\assets\github.png')), text="", width=32, height=32, command=lambda: open_url("https://github.com/kadangkesel"))
github_button.pack(side="left", padx=10)

root.mainloop()
