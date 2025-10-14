import os


def scan_directory(directory, extensions):
    image_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(extensions):
                image_files.append(os.path.join(root, file))
    return image_files


def generate_html_gallery(directory):
    # Get the list of image files in the directory and its subdirectories
    image_files = scan_directory(directory, ('.png', '.jpg', '.jpeg'))

    if not image_files:
        print("No image files found in the directory.")
        return

    # Group image files by game
    games = {}
    for image_file in image_files:
        game = os.path.basename(os.path.dirname(image_file))
        if game not in games:
            games[game] = []
        games[game].append(image_file)

    # Generate the HTML code for the gallery
    html = """<!DOCTYPE html>
<html>
<head>
<title>Steam Screenshots Gallery</title>
<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
<style>
.container { padding: 20px; }
.gallery-item { margin-bottom: 20px; }
.gallery-item img { cursor: pointer; max-width: 100%; height: auto; }
</style>
</head>
<body>
<div class="container">
"""

    for game, files in games.items():
        html += f'<h2>{game}</h2>\n'
        html += '<div class="row">\n'
        for i, file in enumerate(files):
            html += '<div class="col-md-4 gallery-item">'
            html += f'<img src="{file}" alt="{os.path.basename(file)}" data-toggle="modal" data-target="#modal-{game}-{i}" />\n'
            html += f'<div class="modal fade" id="modal-{game}-{i}" tabindex="-1" role="dialog" aria-hidden="true">'
            html += '<div class="modal-dialog modal-dialog-centered modal-xl" role="document">'  # Set modal-xl class for full-size modal
            html += '<div class="modal-content">'
            html += '<div class="modal-body">'
            html += f'<img src="{file}" alt="{os.path.basename(file)}" style="width: 100%; height: auto;" />\n'  # Set width: 100%
            html += '</div>'
            html += '</div>'
            html += '</div>'
            html += '</div>'
            html += '</div>\n'
        html += '</div>\n'

    html += """</div>
<script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.5.3/dist/umd/popper.min.js"></script>
<script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
</body>
</html>
"""

    # Save the HTML code to a file
    html_file = os.path.join(directory, "gallery.html")
    with open(html_file, "w") as f:
        f.write(html)

    print(f"HTML gallery generated successfully. You can find it at: {html_file}")


# Provide the path to the directory containing the Steam screenshots
screenshot_directory = "D:/GitHubStuff/steam-screenshot-utils/output"

generate_html_gallery(screenshot_directory)
