import json
from pypdf import PdfReader, PdfWriter
from pypdf.constants import AnnotationDictionaryAttributes as AA
from pypdf.generic import NameObject, TextStringObject
import requests
import os
from pathlib import Path


def download_pdfs_from_links(pdf_path, id):
    reader = PdfReader(pdf_path)
    links = []
    for page in reader.pages:
        for annot in page.annotations:
            annot = annot.get_object()
            if annot[AA.Subtype] == "/Link":
                links.append(annot["/A"]["/URI"])

    folder = Path(f"./documents/{id}")
    if not os.path.exists(folder):
        os.mkdir(folder)

    for link in links:
        if link.endswith(".pdf"):
            response = requests.get(link)

            filename = link.split("/")[-1]
            filepath = Path(f"{folder}/{filename}")
            with open(filepath, "wb") as pdf_file:
                pdf_file.write(response.content)

            print(f"Downloaded PDF file: {filename}")


def extract_fields_from_form(pdf_path):
    reader = PdfReader(pdf_path)
    json_name = os.path.basename(pdf_path).split(".")[0] + ".json"

    print(f"Extracting form fields from {pdf_path} to {json_name}")

    alt_form = reader.get_fields()
    form_dict_alt = {}
    for key, value in alt_form.items():
        if key=="chbxStatusPersonBesonderGrundWeitJa":
                continue
        field_id = value.get("/T")
        if field_id:
            form_dict_alt[field_id] = {}
            form_dict_alt[field_id]["hidden_fields"] = {}
            form_dict_alt[field_id]["/TU"] = value.get("/TU")
            form_dict_alt[field_id]["type"] = value.get("/FT")
            form_dict_alt[field_id]["hidden_fields"]["FF"] = value.get("/Ff")

            # Assumption - Checkboxes have /V and it defaults to unchecked value
            if "/V" in value and value.get("/FT") == "/Btn":
                on_state = [x for x in value.get("/_States_") if x != value.get("/V")][
                    0
                ]
                form_dict_alt[field_id]["hidden_fields"]["on_state"] = on_state
                form_dict_alt[field_id]["hidden_fields"]["off_state"] = value.get("/V")
            print(key)
            form_dict_alt[field_id]["page"] = reader.get_pages_showing_field(value)[
                0
            ].page_number

    with open(f"{json_name}", "w", encoding="utf-8") as j_file:
        json.dump(form_dict_alt, j_file, ensure_ascii=False, indent=4)

    return form_dict_alt


def fillPDF(pdf_path, source_json, response):
    try:
        reader = PdfReader(pdf_path)
        writer = PdfWriter()

        writer.append(reader)

        # TODO : Implement retry mechanism
        for k, v in response.items():

            if v:
                print(f"Filling field {k} with value {v}")

                if k not in source_json.keys():
                    raise ValueError(f"Field {k} not found in the original PDF")

                page_num = source_json[k]["page"]
                if source_json[k].get("type") == "/Tx":
                    value = v

                elif source_json[k].get("type") == "/Btn":
                    if v.strip().lower() == "ja" or v.strip().lower() == "yes":
                        # 49152 is radio button in teh form
                        if source_json[k]["hidden_fields"].get("FF") != 49152:
                            value = source_json[k]["hidden_fields"].get("on_state")
                        else:
                            value = "/0"

                    elif v.strip().lower() == "nein" or v.strip().lower() == "no":
                        if source_json[k]["hidden_fields"].get("FF") != 49152:
                            value = source_json[k]["hidden_fields"].get("off_state")
                        else:
                            value = "/1"

                writer.update_page_form_field_values(
                    writer.pages[page_num],
                    {k: value},
                    auto_regenerate=False,
                )

        with open(pdf_path, "wb") as output_stream:
            writer.write(output_stream)

    except Exception as e:
        print(f"Error filling PDF: {e}")
        return False

    return True


def fillPDF_old(pdf_path, source_json, response):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    writer.append(reader)

    # TODO : Implement retry mechanism
    for k, v in response.items():
        if k not in source_json.keys():
            raise ValueError(f"Field {k} not found in the original PDF")

        page_num = source_json[k]["page"]

        page_content = writer.pages[page_num]

        for j in range(0, len(page_content["/Annots"])):
            writer_annot = page_content["/Annots"][j].get_object()
            if writer_annot.get("/T"):
                if writer_annot.get("/T") == k:
                    if writer_annot.get("/FT") == "/Tx":
                        writer_annot.update(
                            {
                                NameObject("/V"): TextStringObject(v),
                            }
                        )

                        if "/AP" in writer_annot:
                            del writer_annot["/AP"]

                    elif writer_annot.get("/FT") == "/Btn":
                        if v.strip().lower() == "ja" or v.strip().lower() == "yes":
                            if "/AP" not in writer_annot:
                                raise ValueError(
                                    f"Button {k} does not have an appearance dictionary"
                                )

                            appearance_dict = writer_annot["/AP"]

                            states_dict = appearance_dict.get(
                                "/N", {}
                            ) or appearance_dict.get("/D", {})

                            if not states_dict:
                                raise ValueError(
                                    f"Button {k} does not have defined states in appearance dictionary"
                                )

                            states = list(states_dict.keys())

                            # Assumption - On state is the first state
                            # (Need to replace this with a rule)
                            on_state = states[0]
                            writer_annot.update(
                                {
                                    NameObject("/V"): NameObject(on_state),
                                    NameObject("/AS"): NameObject(on_state),
                                }
                            )
                        elif v.strip().lower() == "nein" or v.strip().lower() == "no":
                            writer_annot.update(
                                {
                                    NameObject("/V"): NameObject("/0"),
                                    NameObject("/AS"): NameObject("/0"),
                                }
                            )

            elif "/Parent" in writer_annot.keys():
                writer_annot = writer_annot["/Parent"].get_object()
                if writer_annot.get("/T") == k:
                    if writer_annot.get("/FT") == "/Btn":
                        if v.lower() == "ja" or v.lower() == "yes":
                            writer_annot.update(
                                {
                                    NameObject("/V"): NameObject("/0"),
                                    NameObject("/AS"): NameObject("/0"),
                                }
                            )
                        # Check if AS is needed
                        elif v.lower() == "nein" or v.lower() == "no":
                            writer_annot.update(
                                {
                                    NameObject("/V"): NameObject("/1"),
                                    NameObject("/AS"): NameObject("/1"),
                                }
                            )

    # if "/AcroForm" in writer._root_object:
    #     acro_form = writer._root_object["/AcroForm"]
    #     acro_form[NameObject("/NeedAppearances")] = BooleanObject(True)

    # # Flatten the form fields
    # writer._flatten()

    with open(pdf_path, "wb") as output_stream:
        writer.write(output_stream)

    return True
