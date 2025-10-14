import html
import os
import re


def natural_sort_key(s):
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split("([0-9]+)", s)
    ]
def generate_html_gallery(html_file_path, root_folder="output"):
    supported_extensions = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
    images_by_category = {}
    print(f"Scanning folder: {root_folder}")

    for root, _, files in os.walk(root_folder):
        category_name = os.path.basename(root)
        category_name = html.escape(category_name).replace("®", "&reg;")
        images_by_category[category_name] = []
        for file in files:
            if file.lower().endswith(supported_extensions):
                file = html.escape(file).replace("®", "&reg;")
                images_by_category[category_name].append(os.path.join(root, file))

    for category, images in images_by_category.items():
        alphabetical = sorted(
            [img for img in images if not re.match(r"^\d", os.path.basename(img))],
            key=natural_sort_key,
        )
        numerical = sorted(
            [img for img in images if re.match(r"^\d", os.path.basename(img))],
            key=natural_sort_key,
        )
        images_by_category[category] = alphabetical + numerical

    sorted_categories = sorted(
        images_by_category.keys(),
        key=lambda k: (not k[0].isalpha(), natural_sort_key(k)),
    )
    images_by_category = {
        k: images_by_category[k] for k in sorted_categories if images_by_category[k]
    }

    if not images_by_category:
        print("No images found in the specified folder.")
        return

    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Steam Screenshots Gallery</title>
        <style>
            body {
                background-color: #121212;
                color: #ffffff;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
            }
            h1 {
                text-align: center;
                margin-bottom: 20px;
                font-size: 2.5rem;
                color: #ffffff;
            }
            .search-bar {
                display: flex;
                justify-content: center;
                margin-bottom: 20px;
            }
            .search-bar input {
                padding: 10px;
                width: 50%;
                border: 1px solid #444;
                border-radius: 10px;
                background: rgba(255, 255, 255, 0.1);
                color: #ffffff;
                font-size: 16px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
                backdrop-filter: blur(10px);
            }
            .search-bar input::placeholder {
                color: #cccccc;
            }
            .category {
                margin-top: 10px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 10px;
                padding: 10px 20px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
            }
            .category-title {
                font-size: 1.8rem;
                margin: 0;
                padding: 10px 0;
                cursor: pointer;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .category-title:hover {
                color: #00aaff;
            }
            .category-toggle-icon {
                font-size: 1.2rem;
                transition: transform 0.3s ease;
            }
            .category-toggle-icon.collapsed {
                transform: rotate(-90deg);
            }
            .gallery {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 10px;
                overflow: hidden;
            }
            .gallery img {
                width: 100%;
                border-radius: 12px;
                cursor: pointer;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            }
            .gallery img:hover {
                transform: scale(1.05);
                box-shadow: 0 6px 18px rgba(0, 0, 0, 0.4);
            }
            .lightbox {
                display: none;
                position: fixed;
                z-index: 9999;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.8);
                justify-content: center;
                align-items: center;
                cursor: pointer;
                backdrop-filter: blur(5px);
            }
            .lightbox img {
                max-width: 90%;
                max-height: 90%;
                border-radius: 12px;
                transition: transform 0.3s ease;
            }
            .lightbox:target {
                display: flex;
            }
        </style>
    </head>
    <body>
        <h1>Steam Screenshots Gallery</h1>
        <div class="search-bar">
            <input type="text" id="search" placeholder="Search categories..." onkeyup="filterCategories()">
        </div>
    """

    preload_links = ""
    for category, images in images_by_category.items():
        if images:
            first_image_relative_path = os.path.relpath(
                images[0], start=os.path.dirname(html_file_path)
            )
            preload_links += (
                f'<link rel="preload" href="{first_image_relative_path}" as="image">\n'
            )

    html_content = html_content.replace("</head>", preload_links + "</head>")

    for category, images in images_by_category.items():
        html_content += f"""
        <div class="category" data-category="{category}">
            <h2 class="category-title">
                {category}
                <span class="category-toggle-icon">&#9654;</span>
            </h2>
            <div class="gallery" style="display: none;">
        """
        for index, screenshot_path in enumerate(images):
            relative_path = os.path.relpath(
                screenshot_path, start=os.path.dirname(html_file_path)
            )
            html_content += f"""
            <a href="#lightbox-{category}-{index}">
                <img src="{relative_path}" alt="Screenshot" loading="lazy">
            </a>
            <div id="lightbox-{category}-{index}" class="lightbox" onclick="closeLightbox()">
                <img src="{relative_path}" alt="Screenshot">
            </div>
            """
        html_content += "</div></div>"

    html_content += """
        <script>
            // Filter categories based on search input
            function filterCategories() {
                const searchInput = document.getElementById('search').value.toLowerCase();
                const categories = document.querySelectorAll('.category');
                categories.forEach(category => {
                    const categoryName = category.getAttribute('data-category').toLowerCase();
                    if (categoryName.includes(searchInput)) {
                        category.style.display = 'block';
                    } else {
                        category.style.display = 'none';
                    }
                });
            }

            // Toggle the visibility of gallery images when clicking on the category title
            function toggleCategory(event) {
                const gallery = event.currentTarget.nextElementSibling;
                const icon = event.currentTarget.querySelector('.category-toggle-icon');
                if (gallery.style.display === 'none' || gallery.style.display === '') {
                    gallery.style.display = 'grid';
                    icon.classList.remove('collapsed');
                } else {
                    gallery.style.display = 'none';
                    icon.classList.add('collapsed');
                }
            }

            // Close the lightbox when clicking on the image or background
            function closeLightbox() {
                window.location.hash = '';
            }

            // Attach toggle event listeners to all category titles
            document.addEventListener('DOMContentLoaded', () => {
                document.querySelectorAll('.category-title').forEach(title => {
                    title.addEventListener('click', toggleCategory);
                });
            });
        </script>
    </body>
    </html>
    """

    with open(html_file_path, "w", encoding="utf-8") as html_file:
        html_file.write(html_content)

    print(f"HTML gallery created at {html_file_path}")


if __name__ == "__main__":
    generate_html_gallery("gallery.html", "output")
