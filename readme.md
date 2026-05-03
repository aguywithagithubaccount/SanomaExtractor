# SanomaExtractor

SanomaExtractor is a series of Python scripts to extract PDFs and resources from the Sanoma (My Digital Book) app.

## Usage

```python

# run in "C:\Users\[user]\Sanoma\DATA\.books\[bookid]\BK\pages"
# change MAX_FOLDERS with the number of the pages of the book
python svgToPDF.py

# copies and organizes resources
python .\copy_assets_by_label.py --source-root "C:\Users\[user]\Sanoma\DATA\.books\[bookid]\BK\resources" --collection resources

# check for missing files
python .\check_missing_copied_assets.py --source-root "C:\Users\[user]\Sanoma\DATA\.books\[bookid]\BK\resources" --output-root "C:\Users\[user]\Desktop\sanoma\a-collection resoussets_by_label" --collection resources
```

