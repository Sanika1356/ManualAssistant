"""
Builds the 3 rehearsal PDFs (2 kitchens). Run from the project root:
    python rehearsal/make_rehearsal_pdfs.py
Same dishes in both kitchens, different values, so wrong-machine mistakes show up.
"""
import pathlib

import pymupdf

OUT = pathlib.Path(__file__).parent / "pdfs"

DOCS = {
    "kitchen_a_recipes.pdf": [
        "Kitchen A Recipe Book, Revision 1.0\n\nLasagna. Preheat the Kitchen A convection oven to 180 degrees Celsius. "
        "Bake the lasagna for 45 minutes. Let it rest for 10 minutes before cutting. Use 500 grams of pasta sheets.",
        "Roast Chicken. Roast the chicken at 200 degrees Celsius for 70 minutes. Baste every 20 minutes. "
        "The internal temperature must reach 75 degrees Celsius before serving.",
        "Garlic Bread and Pizza. Garlic bread bakes at 190 degrees Celsius for 12 minutes, using 4 cloves of garlic per loaf. "
        "Pizza dough must proof for 2 hours in the Kitchen A proofing cabinet before baking.",
    ],
    "kitchen_a_maintenance.pdf": [
        "Kitchen A Oven Maintenance Guide, Revision 2.1\n\nCleaning and safety. Clean the oven door glass every week. "
        "Replace the door gasket every 12 months. The fire extinguisher is mounted next to the north door of the kitchen.",
        "Calibration. Calibrate the oven thermostat every 6 months using the reference thermometer kept in drawer 3. "
        "An error greater than 5 degrees Celsius requires a service call.",
    ],
    "kitchen_b_recipes.pdf": [
        "Kitchen B Recipe Book, Revision 1.0\n\nLasagna. Preheat the Kitchen B deck oven to 200 degrees Celsius. "
        "Bake the lasagna for 35 minutes. Let it rest for 15 minutes before cutting. Use 600 grams of pasta sheets.",
        "Roast Chicken. Roast the chicken at 190 degrees Celsius for 80 minutes. Baste every 30 minutes. "
        "The internal temperature must reach 78 degrees Celsius before serving.",
        "Sourdough. Feed the sourdough starter every 12 hours with equal parts flour and water. "
        "Bake the sourdough loaf at 230 degrees Celsius for 40 minutes with steam.",
    ],
}

OUT.mkdir(exist_ok=True)
for filename, pages in DOCS.items():
    pdf = pymupdf.open()
    for text in pages:
        page = pdf.new_page()
        page.insert_textbox(pymupdf.Rect(72, 72, 523, 770), text, fontsize=12)
    pdf.save(OUT / filename)
    pdf.close()
    print("created", OUT / filename)
