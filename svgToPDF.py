import os
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas

def combine_svgs_to_pdf(output_filename, total_folders):
    c = canvas.Canvas(output_filename)

    for i in range(1, total_folders + 1):
        folder_name = str(i)
        file_path = os.path.join(folder_name, f"{folder_name}.svg")

        if os.path.exists(file_path):
            print(f"Processing: {file_path}")
            try:
                # Draw the SVG into a drawing object
                drawing = svg2rlg(file_path)
                
                # Set page size to match the SVG dimensions
                c.setPageSize((drawing.width, drawing.height))
                
                # Render the SVG onto the current PDF page
                renderPDF.draw(drawing, c, 0, 0)
                
                # Finish the current page and move to the next
                c.showPage()
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
        else:
            print(f"Warning: {file_path} not found. Skipping.")

    c.save()
    print(f"Done! Created {output_filename}")

if __name__ == "__main__":
    # Settings
    OUTPUT_FILE = "combined_output.pdf"
    MAX_FOLDERS = 742
    
    combine_svgs_to_pdf(OUTPUT_FILE, MAX_FOLDERS)