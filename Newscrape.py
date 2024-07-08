import requests
from bs4 import BeautifulSoup
import os
import re
import urllib.parse
import fitz  # PyMuPDF
from io import BytesIO
from PIL import Image
import base64

# Function to search Google for PDFs
def search_google_for_pdfs(query, num_results=10):
    search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}+filetype:pdf&num={num_results}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extracting PDF links from the search results
    links = []
    for link in soup.select('.tF2Cxc'):
        url = link.a['href']
        if url.endswith('.pdf'):
            links.append(url)
    
    return links

# Function to download PDFs and save metadata
def download_pdfs_and_save_metadata(pdf_links, query, download_dir='pdfs'):
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    metadata_file = os.path.join(download_dir, 'metadata.txt')
    with open(metadata_file, 'w') as meta_file:
        for link in pdf_links:
            try:
                pdf_response = requests.get(link)
                pdf_filename = os.path.join(download_dir, os.path.basename(link))
                
                with open(pdf_filename, 'wb') as pdf_file:
                    pdf_file.write(pdf_response.content)
                
                # Write metadata
                meta_file.write(f"Title: {os.path.basename(link)}\n")
                meta_file.write(f"URL: {link}\n")
                meta_file.write(f"Downloaded to: {pdf_filename}\n\n")
                
                print(f"Downloaded: {pdf_filename}")
            except Exception as e:
                print(f"Failed to download {link}: {e}")

# Function to extract text and image from a PDF file
def extract_pdf_data(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = ''
        images = []

        for page in doc:
            text += page.get_text()
            image_list = page.get_images(full=True)
            for img in image_list:
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image = Image.open(BytesIO(image_bytes))
                images.append(image)

        excerpt = text[:1000]  # Extract first 1000 characters as excerpt
        return excerpt, images[0] if images else None
    except Exception as e:
        print(f"Failed to extract data from {pdf_path}: {e}")
        return None, None

# Function to post to WordPress
def post_to_wordpress(title, content, excerpt, image, wordpress_url, username, password):
    media_endpoint = f"{wordpress_url}/wp-json/wp/v2/media"
    post_endpoint = f"{wordpress_url}/wp-json/wp/v2/product"

    # Encode the username and password
    credentials = f"{username}:{password}"
    token = base64.b64encode(credentials.encode()).decode('utf-8')

    headers = {"Authorization": f"Basic {token}"}

    # Upload image
    if image:
        image_data = BytesIO()
        image.save(image_data, format='JPEG')
        image_data.seek(0)

        media_response = requests.post(
            f"{wordpress_url}/media",
            headers={
                'Authorization': f'Basic {token}',
                'Content-Disposition': 'attachment; filename=image.jpg'
            },
            files={'file': image_data}
        )

        if media_response.status_code == 201:
            image_id = media_response.json()['id']
        else:
            print(f"Failed to upload image: {media_response.text}")
            image_id = None
    else:
        image_id = None

    # Create post
    post_data = {
        'title': title,
        'content': content,
        'excerpt': excerpt,
        'status': 'publish',
        'featured_media': image_id
    }

    post_response = requests.post(
        f"{wordpress_url}/product",
        headers={
            'Authorization': f'Basic {token}',
            'Content-Type': 'application/json'
        },
        json=post_data
    )

    if post_response.status_code == 201:
        print(f"Product created: {post_response.json()['link']}")
    else:
        print(f"Failed to create product: {post_response.text}")

# Function to search and download PDFs, extract data, and post to WordPress
def search_download_post_pdfs(queries, wordpress_url, username, password):
    for query in queries:
        print(f"Searching for PDFs on: {query}")
        pdf_links = search_google_for_pdfs(query)
        if pdf_links:
            download_pdfs_and_save_metadata(pdf_links, query)
            for pdf_link in pdf_links:
                pdf_filename = os.path.join('pdfs', os.path.basename(pdf_link))
                excerpt, image = extract_pdf_data(pdf_filename)
                if excerpt:
                    title = os.path.basename(pdf_link).replace('.pdf', '')
                    content = f"Download the PDF [here]({pdf_link})"
                    post_to_wordpress(title, content, excerpt, image, wordpress_url, username, password)
        else:
            print(f"No PDFs found for: {query}")

# Example usage
queries = [
    "Technology PDF",
    "Programming Languages PDF",
    "Business PDF",
    "Cryptocurrency PDF",
    "Marketing PDF",
    "IT and Software PDF"
]

wordpress_url = 'https://gentletechs.com/wp-json/wp/v2'
username = 'Seyi'
password = '3qMR XYNr GBTM 0AsM UfOG QrL8'

search_download_post_pdfs(queries, wordpress_url, username, password)