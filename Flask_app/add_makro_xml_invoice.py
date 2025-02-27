from setup_database import import_makro_xml_invoice
import os
def list_files_in_folder(folder_path, verbose=False):
    """
    Returns a table of full file paths in the given folder.

    :param folder_path: Path to the target folder
    :return: Printed table of full file paths
    """
    file_data = []

    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file).replace("\\", "/")
            file_data.append(file_path)

    # Print table
    if verbose:
        print("+-------------------------------------------+")
        print("| Full File Path                            |")
        print("+-------------------------------------------+")
        for path in file_data:
            print(f"| {path.ljust(40)} |")
        print("+-------------------------------------------+")
    return file_data

paths = list_files_in_folder('tmp/faktury',verbose=False)
for item in paths:
    import_makro_xml_invoice(item, overwrite=False)