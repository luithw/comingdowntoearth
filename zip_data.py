import os
import csv
import shutil
from concurrent.futures import ProcessPoolExecutor

DEBUG = False
REDO = True


def create_bin_and_csv(subdir, image_files, max_bin_size=2 * 1024 ** 3):
    # Create bin directory if images exist
    bin_dir = subdir.replace("CVACT", "CVACT_bin")
    if REDO and os.path.exists(bin_dir):
        shutil.rmtree(bin_dir, ignore_errors=True)
    os.makedirs(bin_dir, exist_ok=True)

    bin_counter = 1
    bin_file_path = os.path.join(bin_dir, f'{bin_counter}.bin')
    bin_csv_path = os.path.join(bin_dir, 'file_list.csv')

    # CSV setup
    csv_file = open(bin_csv_path, 'w', newline='', encoding='utf-8')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['name', 'bin_file', 'offset', 'size'])

    # Prepare bin file
    binf = open(bin_file_path, 'wb')
    current_bin_size = 0

    for image_file in image_files:
        image_path = os.path.join(subdir, image_file)
        image_size = os.path.getsize(image_path)

        # Check if adding the current image would exceed the max size and if so, create a new bin file
        if current_bin_size + image_size > max_bin_size:
            binf.close()  # Close current bin
            print("Finished creating bin file %s" % bin_file_path)
            if DEBUG and bin_counter >= 2:
                break
            bin_counter += 1
            bin_file_path = os.path.join(bin_dir, f'{bin_counter}.bin')
            binf = open(bin_file_path, 'wb')
            current_bin_size = 0  # Reset current bin size

        # Read image_path as bytes
        with open(image_path, 'rb') as f:
            image_bytes = f.read()

        # Update metadata
        offset = binf.tell()

        # Write image bytes to binary file
        binf.write(image_bytes)

        csv_writer.writerow([image_file, bin_counter, offset, image_size])
        current_bin_size += image_size

    # Close the final bin and CSV file
    binf.close()
    csv_file.close()


if __name__ == '__main__':
    root_directory = 'CVACT'  # Replace with your directory path
    for subdir, _, files in os.walk(root_directory):
        image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
        if 'orientations' in subdir:
            # copy this directory to the new directory
            shutil.copytree(subdir, subdir.replace("CVACT", "CVACT_bin"))
            continue
        if image_files:
            # Use ProcessPoolExecutor to create bins and CSVs in parallel
            with ProcessPoolExecutor() as executor:
                executor.submit(create_bin_and_csv, subdir, image_files)
